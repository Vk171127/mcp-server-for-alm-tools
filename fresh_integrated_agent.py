from google.adk.agents import Agent
from a2a.client import ClientFactory, ClientConfig
from a2a.types import TransportProtocol
from google.adk.tools import FunctionTool, AgentTool
import httpx
from mcp import StdioServerParameters
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
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


PROJECT_ID = "195472357560"
LOCATION = "us-central1"
ANALYZER_RESOURCE_ID = "5155975060502085632"
GENERATOR_RESOURCE_ID = "7810284090883571712"

ANALYZER_CARD_URL = f"https://{LOCATION}-aiplatform.googleapis.com/v1beta1/projects/{PROJECT_ID}/locations/{LOCATION}/reasoningEngines/{ANALYZER_RESOURCE_ID}/a2a/v1/card"
GENERATOR_CARD_URL = f"https://{LOCATION}-aiplatform.googleapis.com/v1beta1/projects/{PROJECT_ID}/locations/{LOCATION}/reasoningEngines/{GENERATOR_RESOURCE_ID}/a2a/v1/card"

# ❌ REMOVED: agent_state: Dict[str, Any] = {}

URL = "https://toolbox-195472357560.us-central1.run.app"
# URL = "http://localhost:5007"
auth_token_provider = auth_methods.aget_google_id_token(URL)
toolbox = ToolboxSyncClient(URL, client_headers={"Authorization": auth_token_provider})
tools = toolbox.load_toolset()


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
    """
    Load workflow state from PostgreSQL database via toolbox.
    Replaces in-memory agent_state dictionary with persistent database storage.

    Args:
        session_id: Session ID to load state for

    Returns:
        Dictionary containing workflow state or default empty state
    """
    try:
        # Call toolbox to get workflow state from database
        result = toolbox.call_tool("get-workflow-state", {
            "session_id": session_id
        })

        if result and result.get("found"):
            return result.get("state", {})
        else:
            # Return default state for new sessions
            return {
                "iteration_count": 0,
                "feedback_history": [],
                "quality_scores": {},
                "enhancement_requests": [],
                "approval_chain": []
            }
    except Exception as e:
        print(f"Error loading workflow state for session {session_id}: {e}")
        # Return default state on error
        return {
            "iteration_count": 0,
            "feedback_history": [],
            "quality_scores": {},
            "enhancement_requests": [],
            "approval_chain": []
        }


async def save_workflow_state(session_id: str, state_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Save workflow state to PostgreSQL database via toolbox.
    Replaces in-memory agent_state dictionary with persistent database storage.

    Args:
        session_id: Session ID to save state for
        state_data: State data dictionary to save

    Returns:
        Result from database operation
    """
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
    """
    Execute enhanced HITL workflow with database-backed state persistence.

    Args:
        status: Workflow status - 'start', 'approved', 'edited', 'rejected', 'refine', 'review', 'enhance'
        user_input: User input text for the workflow
        session_id: Required session ID for tracking workflow state

    Returns:
        Workflow result with status, stage, delegate_to, and relevant data
    """
    status = status.strip().lower()
    user_input = user_input.strip()
    current_session_id = session_id.strip()

    # Load state from database instead of in-memory dict
    session_data = await load_workflow_state(current_session_id)

    if status == "start":
        # STEP 1: Initial analysis with HITL checkpoint and MCP user story check
        session_data["analyzer_input"] = user_input
        session_data["current_status"] = "analyzing"
        session_data["iteration_count"] = 1

        # Check for user_story in input and enhance with MCP data if found
        enhanced_input = user_input
        if "user_story" in user_input.lower():
            # Extract user story ID from input (basic extraction)
            import re
            story_match = re.search(r'user_story[_\s]*(\d+)', user_input.lower())
            if story_match:
                story_id = int(story_match.group(1))
                # Note: The actual MCP tool call will be made by the agent via MCPToolset
                # This just marks that MCP enhancement should happen
                enhanced_input = f"{user_input}\n\n[MCP_ENHANCE: user_story_id={story_id}]"
                session_data["mcp_user_story_id"] = story_id

        # Save state to database
        await save_workflow_state(current_session_id, session_data)

        return {
            "status": "delegating",
            "stage": "analyzing_requirements",
            "delegate_to": "requirement_analyzer",
            "input": enhanced_input,
            "session_id": current_session_id,
            "next_action": "store_original_requirements_to_db",
            "hitl_checkpoint": "analysis_review",
            "available_actions": ["approved", "edited", "rejected", "refine", "enhance"]
        }

    elif status == "refine":
        # HITL: Human requests refinement with specific feedback
        session_data["iteration_count"] += 1
        session_data["feedback_history"].append({
            "iteration": session_data["iteration_count"],
            "feedback_type": "refinement",
            "human_input": user_input,
            "timestamp": str(uuid.uuid4())[:8]  # Simple timestamp
        })

        # Save state to database
        await save_workflow_state(current_session_id, session_data)

        # Re-analyze with human feedback incorporated
        enhanced_prompt = f"Original analysis needs refinement. Human feedback: {user_input}. Please re-analyze considering this feedback."
        return {
            "status": "delegating",
            "stage": "refining_analysis",
            "delegate_to": "requirement_analyzer",
            "input": enhanced_prompt,
            "session_id": current_session_id,
            "iteration": session_data["iteration_count"],
            "feedback_incorporated": True,
            "next_action": "store_refined_requirements_to_db"
        }

    elif status == "enhance":
        # HITL: Human requests enhancement with additional context
        session_data["enhancement_requests"].append({
            "enhancement_type": "context_addition",
            "details": user_input,
            "iteration": session_data["iteration_count"]
        })

        # Get current analysis and enhance it
        current_analysis = session_data.get("last_analysis", "")
        enhanced_input = f"Current analysis: {current_analysis}\n\nAdditional context from human: {user_input}\n\nPlease enhance the analysis with this new information."

        # Save state to database
        await save_workflow_state(current_session_id, session_data)

        return {
            "status": "delegating",
            "stage": "enhancing_analysis",
            "delegate_to": "requirement_analyzer",
            "input": enhanced_input,
            "session_id": current_session_id,
            "enhancement_applied": True,
            "next_action": "store_enhanced_requirements_to_db"
        }

    elif status == "review":
        # HITL: Human provides quality review and scoring
        try:
            # Parse review format: "review; score:8; feedback:needs more detail"
            parts = user_input.split(';')
            score = None
            feedback = ""

            for part in parts:
                if part.strip().startswith("score:"):
                    score = int(part.split(":")[1].strip())
                elif part.strip().startswith("feedback:"):
                    feedback = part.split(":", 1)[1].strip()

            session_data["quality_scores"][f"iteration_{session_data['iteration_count']}"] = {
                "score": score,
                "feedback": feedback,
                "review_timestamp": str(uuid.uuid4())[:8]
            }

            # Save state to database
            await save_workflow_state(current_session_id, session_data)

            # If score is low (< 7), suggest improvements
            if score and score < 7:
                return {
                    "status": "needs_improvement",
                    "stage": "quality_review_failed",
                    "score": score,
                    "feedback": feedback,
                    "session_id": current_session_id,
                    "suggested_actions": ["refine", "enhance", "rejected"],
                    "improvement_needed": True
                }
            else:
                return {
                    "status": "quality_approved",
                    "stage": "quality_review_passed",
                    "score": score,
                    "feedback": feedback,
                    "session_id": current_session_id,
                    "available_actions": ["approved", "generate_tests"]
                }

        except Exception as e:
            return {
                "status": "review_error",
                "error": f"Invalid review format. Use: 'score:X; feedback:your feedback'",
                "session_id": current_session_id
            }

    elif status == "edited":
        # STEP 2: Human edited content - track changes and delegate
        session_data["edited_input"] = user_input
        session_data["current_status"] = "editing"
        session_data["feedback_history"].append({
            "iteration": session_data["iteration_count"],
            "feedback_type": "direct_edit",
            "edited_content": user_input,
            "timestamp": str(uuid.uuid4())[:8]
        })

        # Save state to database
        await save_workflow_state(current_session_id, session_data)

        return {
            "status": "delegating",
            "stage": "processing_edited_requirements",
            "delegate_to": "test_case_generator",
            "input": user_input,
            "session_id": current_session_id,
            "human_edited": True,
            "next_action": "store_edited_requirements_to_db_then_generate"
        }

    elif status == "approved":
        # STEP 3: Human approval - proceed to test generation
        stored_analysis = session_data.get("last_analysis", "")
        session_data["current_status"] = "approved"
        session_data["approval_chain"].append({
            "approver": "human",
            "timestamp": str(uuid.uuid4())[:8],
            "iteration": session_data["iteration_count"]
        })

        # Save state to database
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

    elif status == "rejected":
        # STEP 4: Human rejection with optional feedback
        session_data["current_status"] = "rejected"
        session_data["feedback_history"].append({
            "iteration": session_data["iteration_count"],
            "feedback_type": "rejection",
            "rejection_reason": user_input if user_input else "No reason provided",
            "timestamp": str(uuid.uuid4())[:8]
        })

        # Save state to database
        await save_workflow_state(current_session_id, session_data)

        return {
            "status": "rejected",
            "stage": "workflow_rejected",
            "session_id": current_session_id,
            "rejection_reason": user_input,
            "restart_options": ["start", "refine"],
            "feedback_available": True
        }

    else:
        return {
            "status": "failed",
            "reason": "invalid_status",
            "valid_statuses": ["start", "approved", "edited", "rejected", "refine", "review", "enhance"],
            "session_id": current_session_id,
            "hitl_help": "Use 'refine' for feedback-based improvements, 'enhance' to add context, 'review' to score quality"
        }


async def get_session_feedback_history(session_id: str) -> Dict[str, Any]:
    """
    Get comprehensive feedback history for a session to enable HITL analysis.

    Args:
        session_id: Session ID to retrieve history for

    Returns:
        Dictionary containing complete feedback history and analytics
    """
    # Load state from database
    session_data = await load_workflow_state(session_id)

    if not session_data.get("iteration_count"):
        return {
            "session_id": session_id,
            "status": "not_found",
            "message": "No session data found"
        }

    return {
        "session_id": session_id,
        "status": "found",
        "iteration_count": session_data.get("iteration_count", 0),
        "feedback_history": session_data.get("feedback_history", []),
        "quality_scores": session_data.get("quality_scores", {}),
        "enhancement_requests": session_data.get("enhancement_requests", []),
        "approval_chain": session_data.get("approval_chain", []),
        "current_status": session_data.get("current_status", "unknown"),
        "analytics": {
            "total_feedback_items": len(session_data.get("feedback_history", [])),
            "average_quality_score": _calculate_average_score(session_data.get("quality_scores", {})),
            "enhancement_count": len(session_data.get("enhancement_requests", [])),
            "approval_count": len(session_data.get("approval_chain", []))
        }
    }


def _calculate_average_score(quality_scores: Dict[str, Any]) -> float:
    """Calculate average quality score from session data."""
    scores = [item.get("score", 0) for item in quality_scores.values() if item.get("score")]
    return sum(scores) / len(scores) if scores else 0.0


async def suggest_improvements(session_id: str, current_output: str) -> Dict[str, Any]:
    """
    AI-powered suggestion system for HITL improvements based on feedback history.

    Args:
        session_id: Session ID to analyze
        current_output: Current agent output to improve

    Returns:
        Improvement suggestions and recommendations
    """
    # Load state from database
    session_data = await load_workflow_state(session_id)

    if not session_data.get("iteration_count"):
        return {"error": "Session not found"}

    feedback_history = session_data.get("feedback_history", [])
    quality_scores = session_data.get("quality_scores", {})

    # Analyze patterns in feedback
    common_issues = []
    improvement_areas = []

    for feedback in feedback_history:
        if feedback.get("feedback_type") == "refinement":
            common_issues.append(feedback.get("human_input", ""))
        elif feedback.get("feedback_type") == "rejection":
            improvement_areas.append(feedback.get("rejection_reason", ""))

    # Analyze quality scores for trends
    low_score_feedback = []
    for score_data in quality_scores.values():
        if score_data.get("score", 10) < 7:
            low_score_feedback.append(score_data.get("feedback", ""))

    return {
        "session_id": session_id,
        "suggestions": {
            "common_issues_identified": common_issues,
            "improvement_areas": improvement_areas,
            "low_score_patterns": low_score_feedback,
            "recommended_actions": _generate_action_recommendations(feedback_history, quality_scores),
            "quality_trend": _analyze_quality_trend(quality_scores)
        },
        "hitl_insights": {
            "feedback_frequency": len(feedback_history),
            "refinement_cycles": len([f for f in feedback_history if f.get("feedback_type") == "refinement"]),
            "human_engagement_level": "high" if len(feedback_history) > 3 else "medium" if len(feedback_history) > 1 else "low"
        }
    }


def _generate_action_recommendations(feedback_history: list, quality_scores: dict) -> list:
    """Generate action recommendations based on HITL patterns."""
    recommendations = []

    if len(feedback_history) > 3:
        recommendations.append("Consider breaking down the analysis into smaller, more focused sections")

    if any(score.get("score", 10) < 6 for score in quality_scores.values()):
        recommendations.append("Quality scores are low - consider requesting more specific human feedback")

    refinement_count = len([f for f in feedback_history if f.get("feedback_type") == "refinement"])
    if refinement_count > 2:
        recommendations.append("Multiple refinements detected - consider asking for clearer initial requirements")

    return recommendations


def _analyze_quality_trend(quality_scores: dict) -> str:
    """Analyze quality score trends."""
    scores = [item.get("score", 0) for item in quality_scores.values() if item.get("score")]
    if len(scores) < 2:
        return "insufficient_data"

    if scores[-1] > scores[0]:
        return "improving"
    elif scores[-1] < scores[0]:
        return "declining"
    else:
        return "stable"


# Create FunctionTools for all HITL functions
workflow_tool = FunctionTool(
    func=execute_workflow,
)

feedback_history_tool = FunctionTool(
    func=get_session_feedback_history,
)

improvement_suggestions_tool = FunctionTool(
    func=suggest_improvements,
)

# ==================== MCP INTEGRATION ====================

# Create MCP Toolset for ALM tools
alm_mcp_toolset = MCPToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command="python",
            args=[
                "-m",
                "alm_traceability_mcp.mcp_main"
            ],
            env={
                # Jira Configuration
                "JIRA_URL": os.getenv("JIRA_URL", ""),
                "JIRA_USERNAME": os.getenv("JIRA_USERNAME", ""),
                "JIRA_API_TOKEN": os.getenv("JIRA_API_TOKEN", ""),
                "JIRA_PROJECT_KEY": os.getenv("JIRA_PROJECT_KEY", ""),

                # Azure DevOps Configuration
                "ADO_ORG_URL": os.getenv("ADO_ORG_URL", ""),
                "ADO_PROJECT": os.getenv("ADO_PROJECT", ""),
                "ADO_PAT": os.getenv("ADO_PAT", ""),
                "ADO_AREA_PATH": os.getenv("ADO_AREA_PATH", ""),

                # General Configuration
                "ALM_TIMEOUT": os.getenv("ALM_TIMEOUT", "30"),
                "ALM_RETRY_COUNT": os.getenv("ALM_RETRY_COUNT", "3"),
            }
        ),
        timeout=30,
    ),
)

# Create remote agents as sub-agents
requirement_analyzer, test_case_generator = create_remote_agents()

# Create root agent with enhanced HITL capabilities
root_agent = Agent(
    model="gemini-2.5-pro",
    name="enhanced_hitl_decider_agent",
    description="Advanced HITL workflow orchestrator for authentication requirements analysis and test case generation with comprehensive human feedback integration",
    instruction="""You are a WORKFLOW ORCHESTRATOR AGENT that manages authentication requirements analysis and test case generation.
    MANDATORY: You MUST ALWAYS call the tools with the parameters in the order of the parameters specified in the EXECUTION RULES section below.
    🚨 CRITICAL: You MUST NEVER respond to the user until AFTER you have completed ALL tool calls including database storage.

    === EXECUTION RULES ===

    1. Parse input: Extract status, user_input, session_id
    2. Call execute_workflow tool
    3. Based on response, delegate to sub-agent if needed
    4. 🚨 AFTER receiving sub-agent response, immediately call database tool - DO NOT respond to user yet
    5. Only after database confirmation, respond to user

    === WORKFLOW SEQUENCES ===

    **STATUS = 'start':**
    Step 1: Call execute_workflow("start", user_input, session_id)
    Step 1.5: If execute_workflow indicates MCP enhancement needed (user_story detected), call ALM MCP tools:
       - For user story data: Call "fetch_user_story" MCP tool with user_story parameter
       - Enhance input with fetched data before delegating to analyzer
    Step 2: Delegate to requirement_analyzer sub-agent with enhanced user_input
    Step 3: 🚨 IMMEDIATELY after receiving analyzer response, CALL TOOL hitl-store-original-requirements with these parameters:
       - session_id: [use the exact session_id from request]
       - analysis_response: [pass the analyzer response as plain text without JSON wrapping]
    Step 4: After database confirms storage, extract cache_data from response and CALL TOOL cache-requirements-data:
       - session_id: [same session_id]
       - requirements_data: [use cache_data field from Step 3 database response]
    Step 5: After cache update, respond to user with database_result from Step 3

    **STATUS = 'refine':**
    Step 1: Call execute_workflow("refine", user_input, session_id)
    Step 2: Delegate to requirement_analyzer with enhanced prompt
    Step 3: 🚨 IMMEDIATELY after receiving analyzer response, CALL TOOL hitl-refine-analysis-workflow with these parameters:
       - session_id: [use the exact session_id from request]
       - refined_analysis: [pass the analyzer response as plain text]
       - human_feedback: [use the user_input as plain text]
       - iteration_count: [extract number from execute_workflow response]
    Step 4: After database confirms storage, extract cache_data from response and CALL TOOL cache-requirements-data:
       - session_id: [same session_id]
       - requirements_data: [use cache_data field from Step 3 database response]
    Step 5: After cache update, respond to user with database_result from Step 3

    **STATUS = 'enhance':**
    Step 1: Call execute_workflow("enhance", user_input, session_id)
    Step 2: Delegate to requirement_analyzer with enhanced prompt
    Step 3: 🚨 IMMEDIATELY after receiving analyzer response, CALL TOOL hitl-enhance-analysis-workflow with these parameters:
       - session_id: [use the exact session_id from request]
       - enhanced_analysis: [pass the analyzer response as plain text]
       - enhancement_context: [use the user_input as plain text]
    Step 4: After database confirms storage, extract cache_data from response and CALL TOOL cache-requirements-data:
       - session_id: [same session_id]
       - requirements_data: [use cache_data field from Step 3 database response]
    Step 5: After cache update, respond to user with database_result from Step 3

    **STATUS = 'edited':**
    Step 1: Call execute_workflow("edited", user_input, session_id)
    Step 2: Call hitl-process-edited-requirements tool with edited content:
       - session_id: session_id from request
       - edited_content: user_input
    Step 3: After database confirms storage, extract cache_data from response and CALL TOOL cache-requirements-data:
       - session_id: session_id
       - requirements_data: [cache_data from Step 2 response]
    Step 4: After cache update, respond to user with database_result from Step 2

    **STATUS = 'approved':**
    Step 1: Call execute_workflow("approved", "", session_id)
    Step 2: Call hitl-approve-and-generate-tests tool with session_id
    Step 3: CHECK if requirements are available from Step 2 response:
       - If requirements_available = true: Delegate to test_case_generator with combined_requirements
       - If requirements_available = false: Respond with error about missing requirements
    Step 4: 🚨 ONLY if requirements were available and generator responded, CALL TOOL parse-and-store-test-cases(session_id, structured_test_cases, test_types_requested) in the following order of parameters:
       - session_id: session_id from request
       - structured_test_cases: [generator response]
       - test_types_requested: ["functional", "security","performance", "edge_case", "regression", "integration", "negative"]
    Step 5: After database confirms storage, extract cache_data from response and CALL TOOL cache-test-cases-data:
       - session_id: session_id
       - test_cases_data: [cache_data from Step 4 response]
    Step 6: After cache update, respond to user with database_result from Step 4

    **STATUS = 'rejected':**
    Step 1: Call execute_workflow("rejected", user_input, session_id)
    Step 2: Call hitl-reject-workflow tool:
       - session_id: session_id from request
       - rejection_reason: user_input
    Step 3: After database confirms, respond with rejection acknowledgment

    🚨 CRITICAL BEHAVIOR RULES 🚨

    1. **DO NOT say anything to the user until database storage AND cache update are complete**
    2. **Sub-agent responses are intermediate data - NOT final responses**
    3. **Every sub-agent call must be followed by: database tool call → cache tool call → user response**
    4. **The database and cache tool calls happen AUTOMATICALLY - you don't wait for user permission**
    5. **Always return the database_result from the database tool response, not your own summary**
    6. **Cache operations ensure data consistency between database and Redis cache**
    7. **Extract cache_data from database tool response JSON and pass as requirements_data/test_cases_data to cache tools**
    8. **Database tool responses contain: database_result (for user), cache_data (for caching), next_action (instruction)**
    9. **CRITICAL: When calling tools, pass text data as plain strings - DO NOT wrap in JSON or add extra quotes**
    10. **Your thinking process:**
       - "Got sub-agent response" → "Now I must call database tool" → "Database confirmed" → "Now I can respond to user"

    🚨 DATA HANDLING RULES 🚨
    - Pass analyzer/generator responses as plain text strings to database tools
    - Do NOT wrap responses in JSON format like {"response": "text"}
    - Do NOT add extra escaping or quotes around the content
    - Extract session_id, user_input as simple string values
    - Use cache_data from database responses exactly as provided

    🔒 CORRECT BEHAVIOR EXAMPLE:
    - User: "start; Analyze OAuth flow; session_123"
    - You: [Call execute_workflow]
    - You: [Call requirement_analyzer sub-agent]
    - You: [Receive analyzer response: "Authentication requires OAuth 2.0..."]
    - You: [IMMEDIATELY call store-original-requirements(session_id="session_123", analysis_response="Authentication requires OAuth 2.0...")]
    - You: [Get database confirmation]
    - You: "I've analyzed and stored your requirements. The analysis shows authentication requires OAuth 2.0..."

    ❌ WRONG BEHAVIOR (what you're doing now):
    - You: [Call requirement_analyzer]
    - You: "Here's the analysis: [analyzer response]" ← WRONG! Database not called yet!

    The key is: Think of the sub-agent response as data you need to process (store in DB) before reporting to the user.
    You are a DATA PROCESSOR, not a messenger. Process first, report after.

    Remember: execute_workflow → sub-agent → database tool → user response
    NEVER skip the database tool step!

    Enhanced HITL statuses: start, refine, enhance, review, edited, approved, rejected
    """,
    sub_agents=[],
    tools=[workflow_tool, feedback_history_tool, improvement_suggestions_tool, alm_mcp_toolset, *tools, requirement_analyzer, test_case_generator],
)