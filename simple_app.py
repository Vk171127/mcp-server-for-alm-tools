#!/usr/bin/env python3
"""
Simple FastAPI Web Server for MCP Tools
Simplified version for Cloud Run deployment
"""

import asyncio
import logging
import json
import os
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SimpleALMServer:
    """Simple ALM Traceability HTTP Server for agents"""
    
    def __init__(self):
        self.app = FastAPI(
            title="ALM Traceability Server",
            description="Simplified HTTP server for ALM tools integration",
            version="1.0.0"
        )
        
        # Add CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Mock configuration
        self.config = {
            "ado_org": os.getenv("ADO_ORG"),
            "ado_project": os.getenv("ADO_PROJECT"),
            "ado_pat": os.getenv("ADO_PAT"),
            "jira_url": os.getenv("JIRA_URL"),
            "jira_email": os.getenv("JIRA_EMAIL"),
            "jira_token": os.getenv("JIRA_TOKEN")
        }
        
        self.setup_routes()
    
    def setup_routes(self):
        """Setup HTTP routes"""
        
        @self.app.get("/")
        async def root():
            return {
                "service": "ALM Traceability Server",
                "status": "running",
                "version": "1.0.0",
                "description": "Simplified HTTP server for ALM tools integration",
                "endpoints": {
                    "health": "/health",
                    "tools": "/tools",
                    "ado": "/ado/*",
                    "jira": "/jira/*"
                }
            }
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            return {
                "status": "healthy",
                "service": "ALM Traceability Server",
                "timestamp": "2024-01-01T00:00:00Z",
                "components": {
                    "server": "running",
                    "ado_configured": bool(self.config["ado_org"]),
                    "jira_configured": bool(self.config["jira_url"])
                }
            }
        
        @self.app.get("/tools")
        async def list_tools():
            """List all available tools"""
            tools = [
                {
                    "name": "configure_ado",
                    "description": "Configure Azure DevOps connection",
                    "method": "POST",
                    "endpoint": "/ado/configure"
                },
                {
                    "name": "fetch_user_story",
                    "description": "Fetch user story from Azure DevOps",
                    "method": "GET",
                    "endpoint": "/ado/story/{story_id}"
                },
                {
                    "name": "create_test_case",
                    "description": "Create test case in Azure DevOps",
                    "method": "POST",
                    "endpoint": "/ado/testcase"
                },
                {
                    "name": "configure_jira",
                    "description": "Configure Jira connection",
                    "method": "POST",
                    "endpoint": "/jira/configure"
                },
                {
                    "name": "fetch_jira_issue",
                    "description": "Fetch issue from Jira",
                    "method": "GET",
                    "endpoint": "/jira/issue/{issue_key}"
                }
            ]
            
            return {
                "total_tools": len(tools),
                "tools": tools
            }
        
        # ADO Routes
        @self.app.post("/ado/configure")
        async def configure_ado(
            organization: str,
            project: str,
            personal_access_token: str
        ):
            """Configure Azure DevOps connection"""
            try:
                self.config.update({
                    "ado_org": organization,
                    "ado_project": project,
                    "ado_pat": personal_access_token
                })
                
                # Mock test connection
                return {
                    "success": True,
                    "message": "ADO connection configured successfully",
                    "organization": organization,
                    "project": project
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/ado/story/{story_id}")
        async def fetch_user_story(story_id: int):
            """Fetch user story from Azure DevOps"""
            try:
                if not self.config["ado_org"]:
                    raise HTTPException(status_code=400, detail="ADO not configured")
                
                # Mock user story response
                return {
                    "success": True,
                    "user_story_id": story_id,
                    "title": f"Sample User Story {story_id}",
                    "description": "This is a mock user story for demonstration",
                    "state": "Active",
                    "acceptance_criteria": "Given... When... Then...",
                    "organization": self.config["ado_org"],
                    "project": self.config["ado_project"]
                }
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/ado/testcase")
        async def create_test_case(
            user_story_id: int,
            title: str,
            description: str = "",
            steps: Optional[List[Dict[str, str]]] = None
        ):
            """Create test case in Azure DevOps"""
            try:
                if not self.config["ado_org"]:
                    raise HTTPException(status_code=400, detail="ADO not configured")
                
                # Mock test case creation
                test_case_id = 12345  # Mock ID
                
                return {
                    "success": True,
                    "test_case_id": test_case_id,
                    "title": title,
                    "description": description,
                    "user_story_id": user_story_id,
                    "steps": steps or [],
                    "url": f"https://dev.azure.com/{self.config['ado_org']}/{self.config['ado_project']}/_workitems/edit/{test_case_id}"
                }
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        # Jira Routes
        @self.app.post("/jira/configure")
        async def configure_jira(
            base_url: str,
            email: str,
            api_token: str,
            project_key: str
        ):
            """Configure Jira connection"""
            try:
                self.config.update({
                    "jira_url": base_url,
                    "jira_email": email,
                    "jira_token": api_token,
                    "jira_project": project_key
                })
                
                return {
                    "success": True,
                    "message": "Jira connection configured successfully",
                    "base_url": base_url,
                    "project_key": project_key
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/jira/issue/{issue_key}")
        async def fetch_jira_issue(issue_key: str):
            """Fetch issue from Jira"""
            try:
                if not self.config["jira_url"]:
                    raise HTTPException(status_code=400, detail="Jira not configured")
                
                # Mock Jira issue response
                return {
                    "success": True,
                    "key": issue_key,
                    "title": f"Sample Issue {issue_key}",
                    "description": "This is a mock Jira issue for demonstration",
                    "status": "To Do",
                    "issue_type": "Story",
                    "project": self.config.get("jira_project", "DEMO"),
                    "url": f"{self.config['jira_url']}/browse/{issue_key}"
                }
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        # Generic tool call endpoint for MCP-style calls
        @self.app.post("/tools/{tool_name}")
        async def call_tool(tool_name: str, parameters: Dict[str, Any] = None):
            """Generic tool call endpoint"""
            if parameters is None:
                parameters = {}
            
            try:
                # Route to appropriate handler based on tool name
                if tool_name == "configure_ado_connection":
                    return await configure_ado(
                        parameters.get("organization", ""),
                        parameters.get("project", ""),
                        parameters.get("personal_access_token", "")
                    )
                elif tool_name == "fetch_user_story":
                    story_id = parameters.get("user_story_id")
                    if not story_id:
                        raise HTTPException(status_code=400, detail="user_story_id required")
                    return await fetch_user_story(int(story_id))
                elif tool_name == "create_testcase":
                    return await create_test_case(
                        parameters.get("user_story_id"),
                        parameters.get("title", ""),
                        parameters.get("description", ""),
                        parameters.get("steps", [])
                    )
                elif tool_name == "configure_jira_connection":
                    return await configure_jira(
                        parameters.get("base_url", ""),
                        parameters.get("email", ""),
                        parameters.get("api_token", ""),
                        parameters.get("project_key", "")
                    )
                elif tool_name == "fetch_jira_issue":
                    issue_key = parameters.get("issue_key")
                    if not issue_key:
                        raise HTTPException(status_code=400, detail="issue_key required")
                    return await fetch_jira_issue(issue_key)
                else:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Tool '{tool_name}' not found"
                    )
                    
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

# Create global app instance
server = SimpleALMServer()
app = server.app

def main():
    """Main entry point"""
    port = int(os.getenv("PORT", 8080))
    host = "0.0.0.0"
    
    logger.info(f"Starting ALM Traceability Server on {host}:{port}")
    logger.info("Service ready for AI agent integration")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )

if __name__ == "__main__":
    main()