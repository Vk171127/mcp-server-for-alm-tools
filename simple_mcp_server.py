#!/usr/bin/env python3
"""
Simplified MCP Server for ALM Traceability
Focus on core ALM functionality without complex dependencies
"""

import asyncio
import logging
import sys
import os
import json
from typing import List, Dict, Any, Optional
from mcp.server.fastmcp import FastMCP
from mcp.types import TextContent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize MCP Server
mcp = FastMCP("alm-traceability-server")

# Simple in-memory storage for demo purposes
storage = {
    "ado_config": None,
    "jira_config": None,
    "user_stories": {},
    "test_cases": {},
    "traceability_links": []
}

def register_alm_tools():
    """Register ALM traceability tools"""
    
    @mcp.tool()
    async def configure_ado_connection(
        organization: str,
        project: str,
        personal_access_token: str
    ) -> List[TextContent]:
        """Configure Azure DevOps connection"""
        try:
            storage["ado_config"] = {
                "organization": organization,
                "project": project,
                "personal_access_token": personal_access_token,
                "base_url": f"https://dev.azure.com/{organization}",
                "configured": True
            }
            
            result = {
                "success": True,
                "message": "Azure DevOps connection configured successfully",
                "organization": organization,
                "project": project,
                "base_url": storage["ado_config"]["base_url"]
            }
            
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "message": "Failed to configure ADO connection"
            }
            return [TextContent(type="text", text=json.dumps(error_result, indent=2))]
    
    @mcp.tool()
    async def fetch_user_story(user_story_id: int) -> List[TextContent]:
        """Fetch user story details from Azure DevOps"""
        try:
            if not storage["ado_config"]:
                raise Exception("Azure DevOps not configured. Please configure connection first.")
            
            # Mock user story data - in real implementation this would call ADO API
            user_story = {
                "id": user_story_id,
                "title": f"User Story {user_story_id}",
                "description": f"This is a sample user story with ID {user_story_id}",
                "state": "Active",
                "story_points": 5,
                "acceptance_criteria": [
                    "Given a user wants to perform an action",
                    "When the user clicks the button",
                    "Then the system should respond appropriately"
                ],
                "area_path": storage["ado_config"]["project"],
                "iteration_path": "Sprint 1",
                "created_date": "2024-01-01T00:00:00Z",
                "assigned_to": "developer@company.com",
                "url": f"{storage['ado_config']['base_url']}/{storage['ado_config']['project']}/_workitems/edit/{user_story_id}"
            }
            
            # Store in memory for later reference
            storage["user_stories"][str(user_story_id)] = user_story
            
            result = {
                "success": True,
                "user_story": user_story,
                "organization": storage["ado_config"]["organization"],
                "project": storage["ado_config"]["project"]
            }
            
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "user_story_id": user_story_id,
                "message": "Failed to fetch user story"
            }
            return [TextContent(type="text", text=json.dumps(error_result, indent=2))]
    
    @mcp.tool()
    async def create_testcase(
        user_story_id: int,
        title: str,
        description: str = "",
        steps: List[Dict[str, str]] = None,
        priority: int = 2
    ) -> List[TextContent]:
        """Create a new test case linked to a user story"""
        try:
            if not storage["ado_config"]:
                raise Exception("Azure DevOps not configured. Please configure connection first.")
            
            if steps is None:
                steps = []
            
            # Generate mock test case ID
            test_case_id = len(storage["test_cases"]) + 10000
            
            test_case = {
                "id": test_case_id,
                "title": title,
                "description": description,
                "steps": steps,
                "priority": priority,
                "state": "Design",
                "area_path": storage["ado_config"]["project"],
                "created_date": "2024-01-01T00:00:00Z",
                "linked_user_story": user_story_id,
                "url": f"{storage['ado_config']['base_url']}/{storage['ado_config']['project']}/_workitems/edit/{test_case_id}"
            }
            
            # Store test case
            storage["test_cases"][str(test_case_id)] = test_case
            
            # Create traceability link
            link = {
                "id": len(storage["traceability_links"]) + 1,
                "source_type": "user_story",
                "source_id": user_story_id,
                "target_type": "test_case",
                "target_id": test_case_id,
                "relationship": "tests",
                "created_date": "2024-01-01T00:00:00Z"
            }
            storage["traceability_links"].append(link)
            
            result = {
                "success": True,
                "test_case": test_case,
                "traceability_link": link,
                "message": f"Test case {test_case_id} created and linked to user story {user_story_id}"
            }
            
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "user_story_id": user_story_id,
                "title": title,
                "message": "Failed to create test case"
            }
            return [TextContent(type="text", text=json.dumps(error_result, indent=2))]
    
    @mcp.tool()
    async def fetch_testcases(user_story_id: int) -> List[TextContent]:
        """Get all test cases linked to a user story"""
        try:
            # Find all test cases linked to this user story
            linked_test_cases = []
            for test_case in storage["test_cases"].values():
                if test_case.get("linked_user_story") == user_story_id:
                    linked_test_cases.append(test_case)
            
            result = {
                "success": True,
                "user_story_id": user_story_id,
                "test_case_count": len(linked_test_cases),
                "test_cases": linked_test_cases
            }
            
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "user_story_id": user_story_id,
                "message": "Failed to fetch test cases"
            }
            return [TextContent(type="text", text=json.dumps(error_result, indent=2))]
    
    @mcp.tool()
    async def batch_create_testcases(
        user_story_id: int,
        test_cases: List[Dict[str, Any]]
    ) -> List[TextContent]:
        """Create multiple test cases for a user story in batch"""
        try:
            if not storage["ado_config"]:
                raise Exception("Azure DevOps not configured. Please configure connection first.")
            
            results = {
                "success": True,
                "user_story_id": user_story_id,
                "total_requested": len(test_cases),
                "created_count": 0,
                "failed_count": 0,
                "created_test_cases": [],
                "errors": []
            }
            
            for i, tc_data in enumerate(test_cases):
                try:
                    # Generate test case ID
                    test_case_id = len(storage["test_cases"]) + 10000
                    
                    test_case = {
                        "id": test_case_id,
                        "title": tc_data.get("title", f"Test Case {i+1}"),
                        "description": tc_data.get("description", ""),
                        "steps": tc_data.get("steps", []),
                        "priority": tc_data.get("priority", 2),
                        "state": "Design",
                        "area_path": storage["ado_config"]["project"],
                        "created_date": "2024-01-01T00:00:00Z",
                        "linked_user_story": user_story_id,
                        "url": f"{storage['ado_config']['base_url']}/{storage['ado_config']['project']}/_workitems/edit/{test_case_id}"
                    }
                    
                    # Store test case
                    storage["test_cases"][str(test_case_id)] = test_case
                    
                    # Create traceability link
                    link = {
                        "id": len(storage["traceability_links"]) + 1,
                        "source_type": "user_story",
                        "source_id": user_story_id,
                        "target_type": "test_case",
                        "target_id": test_case_id,
                        "relationship": "tests",
                        "created_date": "2024-01-01T00:00:00Z"
                    }
                    storage["traceability_links"].append(link)
                    
                    results["created_test_cases"].append({
                        "test_case": test_case,
                        "traceability_link": link
                    })
                    results["created_count"] += 1
                    
                except Exception as tc_error:
                    results["failed_count"] += 1
                    results["errors"].append({
                        "index": i,
                        "title": tc_data.get("title", f"Test Case {i+1}"),
                        "error": str(tc_error)
                    })
            
            results["message"] = f"Batch operation completed: {results['created_count']} created, {results['failed_count']} failed"
            
            return [TextContent(type="text", text=json.dumps(results, indent=2))]
            
        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "user_story_id": user_story_id,
                "message": "Failed to perform batch test case creation"
            }
            return [TextContent(type="text", text=json.dumps(error_result, indent=2))]
    
    @mcp.tool()
    async def get_traceability_matrix(user_story_id: Optional[int] = None) -> List[TextContent]:
        """Get traceability matrix between stories and test cases"""
        try:
            if user_story_id:
                # Filter for specific user story
                relevant_links = [
                    link for link in storage["traceability_links"]
                    if (link["source_id"] == user_story_id and link["source_type"] == "user_story") or
                       (link["target_id"] == user_story_id and link["target_type"] == "user_story")
                ]
                scope = f"user story {user_story_id}"
            else:
                # All traceability links
                relevant_links = storage["traceability_links"]
                scope = "all items"
            
            # Build matrix
            matrix = {
                "scope": scope,
                "total_links": len(relevant_links),
                "user_stories": list(storage["user_stories"].keys()),
                "test_cases": list(storage["test_cases"].keys()),
                "links": relevant_links,
                "summary": {
                    "total_user_stories": len(storage["user_stories"]),
                    "total_test_cases": len(storage["test_cases"]),
                    "total_traceability_links": len(storage["traceability_links"])
                }
            }
            
            result = {
                "success": True,
                "traceability_matrix": matrix
            }
            
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "user_story_id": user_story_id,
                "message": "Failed to get traceability matrix"
            }
            return [TextContent(type="text", text=json.dumps(error_result, indent=2))]
    
    @mcp.tool()
    async def system_status() -> List[TextContent]:
        """Get comprehensive system status"""
        try:
            status = {
                "success": True,
                "service": "ALM Traceability MCP Server",
                "version": "1.0.0",
                "status": "running",
                "components": {
                    "ado_client": {
                        "configured": storage["ado_config"] is not None,
                        "organization": storage["ado_config"]["organization"] if storage["ado_config"] else None,
                        "project": storage["ado_config"]["project"] if storage["ado_config"] else None
                    },
                    "jira_client": {
                        "configured": storage["jira_config"] is not None
                    },
                    "storage": {
                        "user_stories": len(storage["user_stories"]),
                        "test_cases": len(storage["test_cases"]),
                        "traceability_links": len(storage["traceability_links"])
                    }
                },
                "available_tools": [
                    "configure_ado_connection",
                    "fetch_user_story",
                    "create_testcase", 
                    "fetch_testcases",
                    "batch_create_testcases",
                    "get_traceability_matrix",
                    "system_status",
                    "prepare_test_case_context"
                ]
            }
            
            return [TextContent(type="text", text=json.dumps(status, indent=2))]
            
        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "message": "Failed to get system status"
            }
            return [TextContent(type="text", text=json.dumps(error_result, indent=2))]
    
    @mcp.tool()
    async def prepare_test_case_context(
        user_story_id: int,
        include_similar: bool = False
    ) -> List[TextContent]:
        """
        Prepare comprehensive context for test case generation
        This is the main coordination tool that agents should call first
        """
        try:
            context_data = {
                "user_story_id": user_story_id,
                "workflow_status": "preparing_context",
                "context_sources": []
            }
            
            # 1. Fetch user story
            if str(user_story_id) in storage["user_stories"]:
                context_data["user_story"] = storage["user_stories"][str(user_story_id)]
                context_data["context_sources"].append("local_storage")
            else:
                # Try to fetch from "ADO" (mock)
                if storage["ado_config"]:
                    user_story = {
                        "id": user_story_id,
                        "title": f"User Story {user_story_id}",
                        "description": f"Sample user story {user_story_id} for testing",
                        "state": "Active",
                        "acceptance_criteria": [
                            "Given a user wants to test functionality",
                            "When the user performs the action",
                            "Then the system should behave correctly"
                        ]
                    }
                    storage["user_stories"][str(user_story_id)] = user_story
                    context_data["user_story"] = user_story
                    context_data["context_sources"].append("ado_mock_fetch")
                else:
                    context_data["user_story_error"] = "ADO not configured and story not in cache"
            
            # 2. Check for existing test cases
            existing_tests = []
            for test_case in storage["test_cases"].values():
                if test_case.get("linked_user_story") == user_story_id:
                    existing_tests.append(test_case)
            
            context_data["existing_test_cases"] = {
                "count": len(existing_tests),
                "test_cases": existing_tests
            }
            context_data["has_existing_tests"] = len(existing_tests) > 0
            
            # 3. Generate recommendations
            recommendations = []
            if not context_data["has_existing_tests"]:
                recommendations.append("No existing test cases found - full test suite generation recommended")
            else:
                recommendations.append(f"Found {len(existing_tests)} existing test cases - consider gap analysis")
            
            # 4. Test case suggestions based on user story
            test_suggestions = [
                "Generate positive path test cases",
                "Generate negative path test cases",
                "Generate boundary/edge case tests",
                "Generate integration test scenarios"
            ]
            
            if context_data.get("user_story", {}).get("acceptance_criteria"):
                test_suggestions.insert(0, "Generate tests based on acceptance criteria")
            
            context_data.update({
                "success": True,
                "workflow_status": "context_ready",
                "recommendations": recommendations,
                "test_generation_suggestions": test_suggestions,
                "ready_for_generation": "user_story" in context_data,
                "context_completeness": {
                    "user_story_available": "user_story" in context_data,
                    "existing_tests_checked": True,
                    "ado_configured": storage["ado_config"] is not None
                }
            })
            
            return [TextContent(type="text", text=json.dumps(context_data, indent=2))]
            
        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "user_story_id": user_story_id,
                "workflow_status": "context_preparation_failed",
                "message": "Failed to prepare test case context"
            }
            return [TextContent(type="text", text=json.dumps(error_result, indent=2))]

async def initialize_services():
    """Initialize all required services"""
    logger.info("Initializing ALM Traceability MCP Server...")
    
    # Register all ALM tools
    register_alm_tools()
    
    logger.info("✅ MCP Server initialized successfully")
    logger.info(f"📦 Available Tools: {len(mcp.list_tools())}")
    
    # Log available tools
    for tool in mcp.list_tools():
        logger.info(f"   - {tool.name}: {tool.description}")

def main():
    """Main entry point for the MCP server"""
    try:
        logger.info("🚀 Starting ALM Traceability MCP Server...")
        
        # Initialize services
        asyncio.run(initialize_services())
        
        # Run the MCP server
        logger.info("🔌 MCP Server ready to accept connections")
        mcp.run()
        
    except KeyboardInterrupt:
        logger.info("⚠️  Server interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Server error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()