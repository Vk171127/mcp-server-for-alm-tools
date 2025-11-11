# """
# Azure DevOps MCP Server - Main Entry Point
# PostgreSQL-based traceability management for ALM platforms
# """

# import asyncio
# import logging
# from mcp.server.fastmcp import FastMCP
# from jira_client import JiraClient
# from ado_client import ADOClient
# from vector_service import VectorService
# from traceability_manager import TraceabilityManager
# from mcp_traceability_tools import register_all_tools

# # Configure logging
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# # Initialize MCP Server
# mcp = FastMCP("alm-traceability-server")

# # Global instances
# ado_client = None
# jira_client = None
# vector_service = None
# traceability_manager = None

# async def initialize_services():
#     """Initialize all required services"""
#     global ado_client, jira_client, vector_service, traceability_manager

#     logger.info("Initializing MCP Server with PostgreSQL-based ALM Traceability...")

#     # Initialize services (will be configured via tools)
#     ado_client = ADOClient()
#     jira_client = JiraClient()
#     vector_service = VectorService()
#     traceability_manager = TraceabilityManager()

#     # Register all MCP tools with PostgreSQL traceability support
#     register_all_tools(mcp, ado_client, jira_client, vector_service, traceability_manager)

#     logger.info("MCP Server initialized successfully with PostgreSQL Traceability")

# if __name__ == "__main__":
#     asyncio.run(initialize_services())
#     logger.info("Starting ALM Traceability MCP Server...")
#     asyncio.run(mcp.run())



"""
Azure DevOps MCP Server - Main Entry Point
PostgreSQL-based traceability management for ALM platforms
"""

import asyncio
import logging
import sys
from mcp.server.fastmcp import FastMCP
from jira_client import JiraClient
from ado_client import ADOClient
from vector_service import VectorService
from traceability_manager import TraceabilityManager
from mcp_tools import register_all_tools

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize MCP Server
mcp = FastMCP("alm-traceability-server")

# Global instances
ado_client = None
jira_client = None
vector_service = None
traceability_manager = None

async def initialize_services():
    """Initialize all required services"""
    global ado_client, jira_client, vector_service, traceability_manager

    logger.info("Initializing MCP Server with PostgreSQL-based ALM Traceability...")

    # Initialize services (will be configured via tools)
    ado_client = ADOClient()
    jira_client = JiraClient()
    vector_service = VectorService()
    traceability_manager = TraceabilityManager()

    # Register all MCP tools with PostgreSQL traceability support
    register_all_tools(mcp, ado_client, jira_client, vector_service, traceability_manager)

    logger.info("✅ MCP Server initialized successfully with PostgreSQL Traceability")
    logger.info(f"📦 Available Tools: {len(mcp._tool_manager._tools)}")

def main():
    """Main entry point for the MCP server"""
    try:
        logger.info("🚀 Starting ALM Traceability MCP Server...")

        # Initialize services
        asyncio.run(initialize_services())

        import os
        port = int(os.environ.get("PORT", 8080))
        # Run the MCP server
        logger.info(f"🔌 MCP Server ready to accept connections on port {port}")
        mcp.run(port=port)

    except KeyboardInterrupt:
        logger.info("⚠️  Server interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Server error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
