#!/usr/bin/env python3
"""
MCP Web Server Wrapper
Exposes existing MCP tools as HTTP endpoints for ADK agents
"""

import asyncio
import logging
import json
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Import your existing MCP setup
from mcp.server.fastmcp import FastMCP
from jira_client import JiraClient
from ado_client import ADOClient
from vector_service import VectorService
from traceability_manager import TraceabilityManager
from mcp_tools import register_all_tools as register_comprehensive_tools
from mcp_traceability_tools import register_all_tools as register_traceability_tools

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MCPWebServer:
    """Web server wrapper for MCP tools"""

    def __init__(self):
        self.app = FastAPI(
            title="ALM Traceability MCP Web Server",
            description="HTTP wrapper for MCP tools - for ADK agent integration",
            version="1.0.0"
        )

        # Add CORS middleware for ADK agents
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Initialize MCP server internally
        self.mcp = FastMCP("alm-traceability-web-server")
        self.ado_client = None
        self.jira_client = None
        self.vector_service = None
        self.traceability_manager = None
        self.initialized = False

        # Setup routes
        self._setup_routes()

    async def initialize_mcp(self):
        """Initialize MCP services and tools"""
        if self.initialized:
            return

        logger.info("Initializing MCP services for web server...")

        # Initialize service clients
        self.ado_client = ADOClient()
        self.jira_client = JiraClient()
        self.vector_service = VectorService()
        self.traceability_manager = TraceabilityManager()

        # Register comprehensive tools from mcp_tools.py
        register_comprehensive_tools(
            self.mcp,
            self.ado_client,
            self.jira_client,
            self.vector_service,
            self.traceability_manager
        )

        # Register additional traceability tools
        register_traceability_tools(
            self.mcp,
            self.ado_client,
            self.jira_client,
            self.vector_service,
            self.traceability_manager
        )

        self.initialized = True
        logger.info(f"MCP Web Server initialized with {len(self.mcp.list_tools())} tools")

    def _setup_routes(self):
        """Setup HTTP routes"""

        @self.app.get("/")
        async def root():
            return {
                "service": "ALM Traceability MCP Web Server",
                "status": "running",
                "version": "1.0.0",
                "description": "HTTP wrapper for MCP tools - for ADK agent integration"
            }

        @self.app.get("/tools")
        async def list_tools():
            """List all available MCP tools"""
            if not self.initialized:
                await self.initialize_mcp()

            tools = self.mcp.list_tools()
            return {
                "total_tools": len(tools),
                "tools": [
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.inputSchema.get("properties", {}) if tool.inputSchema else {}
                    }
                    for tool in tools
                ]
            }

        @self.app.post("/tools/{tool_name}")
        async def call_tool(tool_name: str, parameters: Dict[str, Any] = None):
            """Call a specific MCP tool"""
            if not self.initialized:
                await self.initialize_mcp()

            if parameters is None:
                parameters = {}

            try:
                # Get the tool
                tools = self.mcp.list_tools()
                tool = next((t for t in tools if t.name == tool_name), None)

                if not tool:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Tool '{tool_name}' not found. Available tools: {[t.name for t in tools]}"
                    )

                # Call the tool
                result = await self.mcp.call_tool(tool_name, parameters)

                # Extract text content from MCP response
                if result and hasattr(result, 'content') and result.content:
                    content = result.content[0]
                    if hasattr(content, 'text'):
                        try:
                            # Try to parse as JSON
                            response_data = json.loads(content.text)
                        except json.JSONDecodeError:
                            # Return as plain text if not JSON
                            response_data = {"result": content.text}
                    else:
                        response_data = {"result": str(content)}
                else:
                    response_data = {"result": "No content returned"}

                return {
                    "tool": tool_name,
                    "success": True,
                    "data": response_data
                }

            except Exception as e:
                logger.error(f"Error calling tool {tool_name}: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail={
                        "tool": tool_name,
                        "success": False,
                        "error": str(e)
                    }
                )

        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            if not self.initialized:
                await self.initialize_mcp()

            status = {
                "status": "healthy",
                "initialized": self.initialized,
                "components": {}
            }

            # Check component health
            if self.ado_client:
                status["components"]["ado_client"] = {
                    "configured": self.ado_client.is_configured if hasattr(self.ado_client, 'is_configured') else False
                }

            if self.jira_client:
                status["components"]["jira_client"] = {
                    "configured": self.jira_client.is_configured if hasattr(self.jira_client, 'is_configured') else False
                }

            if self.vector_service:
                status["components"]["vector_service"] = {
                    "configured": self.vector_service.is_configured if hasattr(self.vector_service, 'is_configured') else False
                }

            if self.traceability_manager:
                status["components"]["traceability_manager"] = {
                    "initialized": self.traceability_manager.is_initialized if hasattr(self.traceability_manager, 'is_initialized') else False
                }

            return status

# Global server instance
web_server = MCPWebServer()

# FastAPI app instance for uvicorn
app = web_server.app

async def startup():
    """Startup event"""
    await web_server.initialize_mcp()

# Add startup event
app.add_event_handler("startup", startup)

def main():
    """Main entry point"""
    logger.info("Starting MCP Web Server for ADK integration...")
    uvicorn.run(
        "mcp_web_server:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )

if __name__ == "__main__":
    main()