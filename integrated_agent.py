from google.adk.agents import Agent
from a2a.client import ClientFactory, ClientConfig
from a2a.types import TransportProtocol
from google.adk.tools import FunctionTool, AgentTool
import httpx
from google.auth import default
from google.auth.transport.requests import Request
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent
from typing import Dict, Any
import uuid
from toolbox_core import ToolboxSyncClient, auth_methods
import asyncio
import threading
import time
import os
import json
import re
import subprocess

# Try to import ALM traceability MCP - handle gracefully if not available
try:
    from alm_traceability_mcp import ALMClient
    ALM_AVAILABLE = True
except ImportError as e:
    print(f"ALM Traceability MCP not available: {e}")
    ALM_AVAILABLE = False
    ALMClient = None# ==================== CONFIG ====================

PROJECT_ID = "195472357560"
LOCATION = "us-central1"
ANALYZER_RESOURCE_ID = "5155975060502085632"
GENERATOR_RESOURCE_ID = "7810284090883571712"

ANALYZER_CARD_URL = f"https://{LOCATION}-aiplatform.googleapis.com/v1beta1/projects/{PROJECT_ID}/locations/{LOCATION}/reasoningEngines/{ANALYZER_RESOURCE_ID}/a2a/v1/card"
GENERATOR_CARD_URL = f"https://{LOCATION}-aiplatform.googleapis.com/v1beta1/projects/{PROJECT_ID}/locations/{LOCATION}/reasoningEngines/{GENERATOR_RESOURCE_ID}/a2a/v1/card"

URL = "https://toolbox-195472357560.us-central1.run.app"
# URL = "http://localhost:5007"
auth_token_provider = auth_methods.aget_google_id_token(URL)
toolbox = ToolboxSyncClient(URL, client_headers={"Authorization": auth_token_provider})
tools = toolbox.load_toolset()

# ==================== USER STORY DETECTION & MCP TOOLS ====================

def detect_user_story_numbers(text: str) -> list:
    """Detect user story numbers in text"""
    patterns = [
        r'[A-Z]{2,}-\d+',     # PROJ-123, ABC-456
        r'US\d+',             # US123, US456
        r'#\d+',              # #123, #456
        r'story\s*\d+',       # story 123, story123
        r'user\s*story\s*\d+' # user story 123
    ]

    user_stories = []
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        user_stories.extend(matches)

    return list(set(user_stories))

def run_mcp_tool(tool_name: str, args: Dict[str, Any] = None) -> Dict[str, Any]:
    """Run MCP server tool directly using subprocess"""
    try:
        # Use the published alm-traceability-mcp package as MCP server
        cmd = ["python", "-m", "alm_traceability_mcp"]

        # Add tool-specific arguments
        if tool_name and args:
            tool_input = {
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": args or {}
                }
            }
            cmd.extend(["--input", json.dumps(tool_input)])

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            return {"success": True, "output": result.stdout, "tool": tool_name}
        else:
            return {"success": False, "error": result.stderr, "tool": tool_name}

    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Tool execution timed out", "tool": tool_name}
    except Exception as e:
        return {"success": False, "error": str(e), "tool": tool_name}

async def process_user_story_mcp_tools(user_input: str, session_id: str) -> Dict[str, Any]:
    """Process user story references using direct MCP tool calls"""

    # Detect user story numbers
    user_stories = detect_user_story_numbers(user_input)

    if not user_stories:
        return {
            "user_stories_found": False,
            "message": "No user story numbers detected",
            "enhanced_input": user_input
        }

    # Try to get ALM data for the first user story
    primary_story = user_stories[0]
    alm_results = []

    # Try ADO first
    story_id = primary_story.split('-')[-1] if '-' in primary_story else primary_story.replace('#', '').replace('US', '').replace('story', '').strip()

    ado_result = run_mcp_tool("get_ado_work_item", {
        "work_item_id": story_id
    })

    if ado_result["success"]:
        alm_results.append({"source": "ADO", "data": ado_result["output"]})
    else:
        # Try Jira
        jira_result = run_mcp_tool("search_jira_issues", {
            "jql": f"key = {primary_story}",
            "max_results": 1
        })

        if jira_result["success"]:
            alm_results.append({"source": "Jira", "data": jira_result["output"]})

    # Enhanced input with ALM context
    enhanced_input = user_input
    if alm_results:
        alm_context = f"\\n\\nALM Context for {primary_story}:\\n{alm_results[0]['data']}"
        enhanced_input += alm_context

    return {
        "user_stories_found": True,
        "user_stories": user_stories,
        "alm_results": alm_results,
        "enhanced_input": enhanced_input,
        "session_id": session_id
    }

# ==================== MCP SERVER TOOLS ====================

def run_mcp_tool(tool_name: str, args: Dict[str, Any] = None) -> Dict[str, Any]:
    """Run MCP server tool directly"""
    try:
        # Use the published alm-traceability-mcp package as MCP server
        cmd = ["python", "-m", "alm_traceability_mcp"]

        # Add tool-specific arguments
        if tool_name and args:
            tool_input = {
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": args or {}
                }
            }
            cmd.extend(["--input", json.dumps(tool_input)])

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            return {"success": True, "output": result.stdout, "tool": tool_name}
        else:
            return {"success": False, "error": result.stderr, "tool": tool_name}

    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Tool execution timed out", "tool": tool_name}
    except Exception as e:
        return {"success": False, "error": str(e), "tool": tool_name}

# ==================== SIMPLIFIED WORKFLOW ====================

async def process_user_query(query: str, session_context: Dict[str, Any] = None) -> Dict[str, Any]:
    """Process user query with direct MCP tool routing"""

    # Detect user story references
    user_stories = detect_user_story_numbers(query)
    has_user_story = len(user_stories) > 0

    response = {
        "query": query,
        "user_stories_detected": user_stories,
        "has_user_story": has_user_story,
        "actions_taken": [],
        "results": []
    }

    if has_user_story:
        # Route to MCP tools for ALM operations
        response["actions_taken"].append("user_story_detected")

        # Example: Get work item details for first detected user story
        if user_stories:
            primary_story = user_stories[0]

            # Try ADO first, then Jira
            ado_result = run_mcp_tool("get_ado_work_item", {
                "work_item_id": primary_story.split('-')[-1] if '-' in primary_story else primary_story.replace('#', '').replace('US', '').replace('story', '').strip()
            })

            if ado_result["success"]:
                response["actions_taken"].append("ado_lookup")
                response["results"].append(ado_result)
            else:
                # Try Jira
                jira_result = run_mcp_tool("search_jira_issues", {
                    "jql": f"key = {primary_story}",
                    "max_results": 1
                })

                if jira_result["success"]:
                    response["actions_taken"].append("jira_lookup")
                    response["results"].append(jira_result)
                else:
                    response["actions_taken"].append("no_alm_match")
                    response["results"].append({
                        "message": f"No ALM item found for {primary_story}"
                    })

    else:
        # Handle general queries without user story context
        response["actions_taken"].append("general_query")
        response["results"].append({
            "message": "No user story detected - processing as general query",
            "suggestion": "Include user story numbers (e.g., PROJ-123) for ALM integration"
        })

    return response

# ==================== ADK AGENT SETUP ====================

async def enhanced_hitl_workflow(
    query: str,
    session_id: str,
    context: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Enhanced HITL workflow with direct MCP tool integration"""

    # Process the query
    query_result = await process_user_query(query, context)

    # If user stories detected, offer additional ALM operations
    if query_result["has_user_story"]:
        user_stories = query_result["user_stories_detected"]

        # Create traceability links if requested
        if "link" in query.lower() or "trace" in query.lower():
            for story in user_stories:
                trace_result = run_mcp_tool("create_traceability_link", {
                    "source_id": session_id,
                    "target_id": story,
                    "relationship_type": "discusses",
                    "source_type": "session",
                    "target_type": "requirement"
                })

                if trace_result["success"]:
                    query_result["actions_taken"].append("traceability_created")
                    query_result["results"].append(trace_result)

        # Generate test cases if requested
        if "test" in query.lower() and any(word in query.lower() for word in ["generate", "create", "write"]):
            for story in user_stories:
                test_result = run_mcp_tool("generate_ai_test_cases", {
                    "requirements_text": query,
                    "test_types": ["unit", "integration", "acceptance"],
                    "context": f"User story: {story}"
                })

                if test_result["success"]:
                    query_result["actions_taken"].append("tests_generated")
                    query_result["results"].append(test_result)

    return {
        "session_id": session_id,
        "query_processing": query_result,
        "timestamp": asyncio.get_event_loop().time()
    }

# ==================== MAIN AGENT ====================

async def main():
    """Main agent execution"""
    print("🚀 Starting Simplified ALM-ADK Agent")
    print("📋 Direct MCP tool integration enabled")

    # Test query with user story
    test_query = "Please analyze requirements for user story ABC-123 and generate test cases"
    print(f"\n🔍 Testing query: {test_query}")

    result = await enhanced_hitl_workflow(
        query=test_query,
        session_id="test-session-001"
    )

    print(f"\n✅ Result: {json.dumps(result, indent=2)}")

# ==================== ADK AGENT WORKFLOW FUNCTIONS ====================

def create_client_factory():
    """Create client factory with automatic token refresh for A2A calls"""
    credentials, _ = default(scopes=["https://www.googleapis.com/auth/cloud-platform"])

    # Ensure initial token is valid
    if not credentials.valid or credentials.expired:
        credentials.refresh(Request())

    # Thread-safe token refresh mechanism
    token_lock = threading.Lock()

    class AsyncRefreshingAuth:
        def __init__(self, credentials):
            self.credentials = credentials
            self.last_refresh = time.time()

        async def __call__(self, request):
            # Check if token needs refresh (refresh every 50 minutes to be safe)
            current_time = time.time()
            needs_refresh = (
                not self.credentials.valid or
                self.credentials.expired or
                (current_time - self.last_refresh) > 3000  # 50 minutes
            )

            if needs_refresh:
                with token_lock:
                    # Double-check after acquiring lock
                    if (not self.credentials.valid or
                        self.credentials.expired or
                        (current_time - self.last_refresh) > 3000):

                        # Run token refresh in thread pool to avoid blocking async
                        loop = asyncio.get_event_loop()
                        await loop.run_in_executor(
                            None,
                            lambda: self.credentials.refresh(Request())
                        )
                        self.last_refresh = time.time()

            request.headers["Authorization"] = f"Bearer {self.credentials.token}"
            return request

    httpx_client = httpx.AsyncClient(
        auth=AsyncRefreshingAuth(credentials),
        headers={"Content-Type": "application/json"},
        timeout=60.0,
    )

    return ClientFactory(
        ClientConfig(
            supported_transports=[TransportProtocol.http_json],
            use_client_preference=True,
            httpx_client=httpx_client,
        ),
    )

def create_remote_agents():
    """Create and return remote A2A agents with fresh client factories"""
    # Create separate client factories for each agent to avoid sharing auth state
    analyzer_client_factory = create_client_factory()
    generator_client_factory = create_client_factory()

    requirement_analyzer = RemoteA2aAgent(
        name="requirement_analyzer",
        description="Auth requirements analyzer that analyzes authentication and authorization requirements",
        agent_card=ANALYZER_CARD_URL,
        a2a_client_factory=analyzer_client_factory,
    )

    test_case_generator = RemoteA2aAgent(
        name="test_case_generator",
        description="Test case generator that generates test cases based on analysis",
        agent_card=GENERATOR_CARD_URL,
        a2a_client_factory=generator_client_factory,
    )

    requirement_analyzer_tool = AgentTool(
        agent=requirement_analyzer,
        )

    test_case_generator_tool = AgentTool(
        agent=test_case_generator,
        )

    return requirement_analyzer_tool, test_case_generator_tool

# ==================== DATABASE STATE MANAGEMENT ====================

async def load_workflow_state(session_id: str) -> Dict[str, Any]:
    """Load workflow state from PostgreSQL database via toolbox."""
    try:
        result = toolbox.call_tool("get-workflow-state", {
            "session_id": session_id
        })

        if result and result.get("found"):
            return result.get("state", {})
        else:
            return {
                "iteration_count": 0,
                "feedback_history": [],
                "quality_scores": {},
                "enhancement_requests": [],
                "approval_chain": []
            }
    except Exception as e:
        print(f"Error loading workflow state for session {session_id}: {e}")
        return {
            "iteration_count": 0,
            "feedback_history": [],
            "quality_scores": {},
            "enhancement_requests": [],
            "approval_chain": []
        }

async def save_workflow_state(session_id: str, state_data: Dict[str, Any]) -> Dict[str, Any]:
    """Save workflow state to PostgreSQL database via toolbox."""
    try:
        result = toolbox.call_tool("update-workflow-state", {
            "session_id": session_id,
            "state_data": state_data
        })
        return {"success": True, "result": result}
    except Exception as e:
        print(f"Error saving workflow state for session {session_id}: {e}")
        return {"success": False, "error": str(e)}

# ==================== WORKFLOW EXECUTION ====================

async def execute_workflow(status: str, user_input: str, session_id: str) -> Dict[str, Any]:
    """Execute enhanced HITL workflow with MCP ALM integration"""
    status = status.strip().lower()
    user_input = user_input.strip()
    current_session_id = session_id.strip()

    # Load state from database
    session_data = await load_workflow_state(current_session_id)

    if status == "start":
        # STEP 1: Initial analysis with MCP ALM integration
        session_data["analyzer_input"] = user_input
        session_data["current_status"] = "analyzing"
        session_data["iteration_count"] = 1

        # Process user story with MCP tools
        mcp_result = await process_user_story_mcp_tools(user_input, current_session_id)
        session_data["mcp_alm_data"] = mcp_result

        # Use enhanced input for analysis
        analysis_input = mcp_result.get("enhanced_input", user_input)

        # Save state to database
        await save_workflow_state(current_session_id, session_data)

        return {
            "status": "delegating",
            "stage": "analyzing_requirements",
            "delegate_to": "requirement_analyzer",
            "input": analysis_input,
            "session_id": current_session_id,
            "next_action": "store_original_requirements_to_db",
            "hitl_checkpoint": "analysis_review",
            "available_actions": ["approved", "edited", "rejected", "refine", "enhance"],
            "mcp_alm_integration": mcp_result
        }

    elif status == "approved":
        # Human approval - proceed to test generation
        stored_analysis = session_data.get("last_analysis", "")
        session_data["current_status"] = "approved"
        session_data["approval_chain"].append({
            "approver": "human",
            "timestamp": str(uuid.uuid4())[:8],
            "iteration": session_data["iteration_count"]
        })

        await save_workflow_state(current_session_id, session_data)

        return {
            "status": "delegating",
            "stage": "generating_test_cases",
            "delegate_to": "test_case_generator",
            "input": stored_analysis,
            "session_id": current_session_id,
            "human_approved": True,
            "next_action": "store_test_cases_to_db"
        }

    else:
        return {
            "status": "failed",
            "reason": "invalid_status",
            "valid_statuses": ["start", "approved", "edited", "rejected", "refine", "review", "enhance"],
            "session_id": current_session_id
        }

# Function to check if text contains user story numbers
async def check_user_story_keyword(text: str) -> bool:
    """Check if the text contains user story numbers"""
    return len(detect_user_story_numbers(text)) > 0

# Create FunctionTools
workflow_tool = FunctionTool(func=execute_workflow)
check_user_story_tool = FunctionTool(func=check_user_story_keyword)
process_user_story_mcp_tool = FunctionTool(func=process_user_story_mcp_tools)

# Create remote agents
requirement_analyzer, test_case_generator = create_remote_agents()

# MCP Server Configuration
mcp_alm_server_config = {
    "command": "mcp_server_alm_tools",
    "args": [],
    "env": {
        "JIRA_URL": os.getenv("JIRA_URL", ""),
        "JIRA_USERNAME": os.getenv("JIRA_USERNAME", ""),
        "JIRA_API_TOKEN": os.getenv("JIRA_API_TOKEN", ""),
        "JIRA_PROJECT_KEY": os.getenv("JIRA_PROJECT_KEY", ""),
        "ADO_ORG_URL": os.getenv("ADO_ORG_URL", ""),
        "ADO_PROJECT": os.getenv("ADO_PROJECT", ""),
        "ADO_PAT": os.getenv("ADO_PAT", ""),
        "ADO_AREA_PATH": os.getenv("ADO_AREA_PATH", ""),
        "ALM_TIMEOUT": os.getenv("ALM_TIMEOUT", "30"),
        "ALM_RETRY_COUNT": os.getenv("ALM_RETRY_COUNT", "3"),
    },
}

# Create root agent
root_agent = Agent(
    model="gemini-2.5-pro",
    name="enhanced_hitl_decider_agent",
    description="Advanced HITL workflow orchestrator with direct MCP ALM tools integration",
    instruction="""You are a WORKFLOW ORCHESTRATOR AGENT that manages authentication requirements analysis and test case generation.

    === MCP ALM TOOLS INTEGRATION ===

    For 'start' status:
    1. Call execute_workflow("start", user_input, session_id)
    2. The execute_workflow function automatically:
       - Detects user story numbers using regex patterns (PROJ-123, US456, #123, etc.)
       - If user stories detected, calls MCP tools directly:
         * run_mcp_tool("get_ado_work_item", {"work_item_id": story_id})
         * If ADO fails, run_mcp_tool("search_jira_issues", {"jql": f"key = {story}", "max_results": 1})
       - Enhances user_input with ALM context if found
       - Returns enhanced input for requirement analysis
    3. Delegate to requirement_analyzer with enhanced_input from execute_workflow response
    4. Store results in database and respond to user

    Available MCP Tools (called automatically):
    - get_ado_work_item: Get Azure DevOps work item details
    - search_jira_issues: Search Jira issues by JQL
    - create_traceability_link: Create traceability links
    - generate_ai_test_cases: Generate AI test cases

    The MCP integration is automatic - no manual tool calls needed for user story detection.
    """,
    sub_agents=[],
    tools=[workflow_tool, check_user_story_tool, process_user_story_mcp_tool, *tools, requirement_analyzer, test_case_generator],
    mcp=mcp_alm_server_config,
)