#!/usr/bin/env python3
"""
MCP HTTP Bridge for Cloud Run
Exposes MCP tools over HTTP for AI agents while maintaining MCP protocol compatibility
"""

import asyncio
import logging
import json
import os
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Import the existing MCP server
import mcp_main

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MCPHttpBridge:
    """HTTP bridge for MCP server on Cloud Run"""
    
    def __init__(self):
        self.app = FastAPI(
            title="ALM Traceability MCP Server",
            description="HTTP bridge for MCP tools - for AI agent integration",
            version="1.0.0"
        )
        
        # Add CORS middleware for AI agents
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        self.mcp_initialized = False
        self.setup_routes()
    
    async def initialize_mcp(self):
        """Initialize the MCP server"""
        if not self.mcp_initialized:
            logger.info("Initializing MCP server...")
            await mcp_main.initialize_services()
            self.mcp_initialized = True
            logger.info("MCP server initialized successfully")
    
    def setup_routes(self):
        """Setup HTTP routes"""
        
        @self.app.get("/")
        async def root():
            if not self.mcp_initialized:
                await self.initialize_mcp()
            
            return {
                "service": "ALM Traceability MCP Server",
                "status": "running",
                "version": "1.0.0",
                "description": "HTTP bridge for MCP tools - for AI agent integration",
                "mcp_protocol": "exposed over HTTP",
                "endpoints": {
                    "tools": "/tools",
                    "tools_call": "/tools/{tool_name}",
                    "health": "/health",
                    "mcp_info": "/mcp"
                }
            }
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            if not self.mcp_initialized:
                await self.initialize_mcp()
            
            return {
                "status": "healthy",
                "service": "ALM Traceability MCP Server",
                "mcp_initialized": self.mcp_initialized,
                "components": {
                    "mcp_server": "running",
                    "http_bridge": "active"
                }
            }
        
        @self.app.get("/tools")
        async def list_tools():
            """List all available MCP tools"""
            if not self.mcp_initialized:
                await self.initialize_mcp()
            
            try:
                tools = await mcp_main.mcp.list_tools()
                return {
                    "total_tools": len(tools),
                    "tools": [
                        {
                            "name": tool.name,
                            "description": tool.description,
                            "input_schema": tool.inputSchema if hasattr(tool, 'inputSchema') else {}
                        }
                        for tool in tools
                    ]
                }
            except Exception as e:
                logger.error(f"Error listing tools: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/tools/{tool_name}")
        async def call_tool(tool_name: str, request: Request):
            """Call a specific MCP tool"""
            if not self.mcp_initialized:
                await self.initialize_mcp()
            
            try:
                # Get parameters from request body
                try:
                    body = await request.json()
                    parameters = body if isinstance(body, dict) else {}
                except:
                    parameters = {}
                
                logger.info(f"Calling MCP tool: {tool_name} with parameters: {parameters}")
                
                # Get available tools first
                tools = await mcp_main.mcp.list_tools()
                tool = next((t for t in tools if t.name == tool_name), None)
                
                if not tool:
                    available_tools = [t.name for t in tools]
                    raise HTTPException(
                        status_code=404,
                        detail=f"Tool '{tool_name}' not found. Available tools: {available_tools}"
                    )
                
                # Call the MCP tool
                result = await mcp_main.mcp.call_tool(tool_name, parameters)
                
                # Process the result
                response_data = {"tool": tool_name, "success": True}
                
                if result and hasattr(result, 'content') and result.content:
                    # Extract content from MCP response
                    content_items = []
                    for content in result.content:
                        if hasattr(content, 'text'):
                            try:
                                # Try to parse as JSON
                                parsed_content = json.loads(content.text)
                                content_items.append(parsed_content)
                            except json.JSONDecodeError:
                                # Return as plain text if not JSON
                                content_items.append({"text": content.text})
                        else:
                            content_items.append({"content": str(content)})
                    
                    response_data["data"] = content_items[0] if len(content_items) == 1 else content_items
                else:
                    response_data["data"] = {"message": "Tool executed successfully"}
                
                return response_data
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error calling tool {tool_name}: {str(e)}", exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail={
                        "tool": tool_name,
                        "success": False,
                        "error": str(e)
                    }
                )
        
        @self.app.get("/mcp")
        async def mcp_info():
            """Get MCP server information"""
            if not self.mcp_initialized:
                await self.initialize_mcp()
            
            tools = await mcp_main.mcp.list_tools()
            
            return {
                "mcp_server": {
                    "name": "alm-traceability-server",
                    "initialized": self.mcp_initialized,
                    "total_tools": len(tools),
                    "capabilities": [
                        "Azure DevOps integration",
                        "Jira integration", 
                        "Vector search",
                        "Traceability management",
                        "Test case generation",
                        "Batch operations"
                    ]
                },
                "usage": {
                    "list_tools": "GET /tools",
                    "call_tool": "POST /tools/{tool_name}",
                    "health_check": "GET /health"
                }
            }

# Create global app instance
bridge = MCPHttpBridge()
app = bridge.app

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize MCP server on startup"""
    await bridge.initialize_mcp()

def main():
    """Main entry point"""
    port = int(os.getenv("PORT", 8080))
    host = "0.0.0.0"
    
    logger.info(f"Starting ALM Traceability MCP HTTP Bridge on {host}:{port}")
    logger.info("Service ready for AI agent integration via HTTP")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )

if __name__ == "__main__":
    main()