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

if __name__ == "__main__":
    asyncio.run(main())