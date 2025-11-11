"""
PostgreSQL-based MCP Tools Registration Module
Registers MCP tools for ALM traceability management with PostgreSQL backend
"""
import json
import logging
from typing import List, Dict, Any
from mcp.types import TextContent

logger = logging.getLogger(__name__)

def register_traceability_tools(mcp, traceability_manager):
    """Register PostgreSQL-based traceability tools with the MCP server"""
    
    @mcp.tool()
    async def initialize_traceability_database() -> List[TextContent]:
        """Initialize the PostgreSQL traceability database connection"""
        try:
            result = await traceability_manager.initialize()
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "message": "Failed to initialize traceability database"
            }
            return [TextContent(type="text", text=json.dumps(error_result, indent=2))]
    
    @mcp.tool()
    async def create_traceability_link(
        source_type: str,
        source_id: str,
        target_type: str,
        target_id: str,
        relationship_type: str,
        source_alm_type: str = None,
        source_external_id: str = None,
        target_alm_type: str = None,
        target_external_id: str = None,
        confidence_score: float = 1.0,
        description: str = None,
        created_by: str = None
    ) -> List[TextContent]:
        """Create a new traceability link between two items
        
        Args:
            source_type: Type of source item ('session', 'requirement', 'test_case')
            source_id: ID of source item
            target_type: Type of target item ('session', 'requirement', 'test_case')  
            target_id: ID of target item
            relationship_type: Relationship type ('tests', 'covers', 'implements', 'relates_to')
            source_alm_type: ALM platform type for source ('azure_devops', 'jira')
            source_external_id: External ID in ALM system for source
            target_alm_type: ALM platform type for target ('azure_devops', 'jira')
            target_external_id: External ID in ALM system for target
            confidence_score: Confidence score (0.0-1.0)
            description: Optional description
            created_by: User who created the link
        """
        try:
            result = await traceability_manager.create_traceability_link(
                source_type=source_type,
                source_id=source_id,
                target_type=target_type,
                target_id=target_id,
                relationship_type=relationship_type,
                source_alm_type=source_alm_type,
                source_external_id=source_external_id,
                target_alm_type=target_alm_type,
                target_external_id=target_external_id,
                confidence_score=confidence_score,
                description=description,
                created_by=created_by
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "message": "Failed to create traceability link"
            }
            return [TextContent(type="text", text=json.dumps(error_result, indent=2))]
    
    @mcp.tool()
    async def get_traceability_links_for_item(
        item_type: str,
        item_id: str,
        direction: str = "both"
    ) -> List[TextContent]:
        """Get all traceability links for a specific item
        
        Args:
            item_type: Type of item ('session', 'requirement', 'test_case')
            item_id: ID of the item
            direction: Direction to search ('source', 'target', 'both')
        """
        try:
            result = await traceability_manager.get_traceability_links_for_item(
                item_type=item_type,
                item_id=item_id,
                direction=direction
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "message": f"Failed to get traceability links for {item_type}:{item_id}"
            }
            return [TextContent(type="text", text=json.dumps(error_result, indent=2))]
    
    @mcp.tool()
    async def get_traceability_link(link_id: str) -> List[TextContent]:
        """Get a specific traceability link by ID
        
        Args:
            link_id: UUID of the traceability link
        """
        try:
            result = await traceability_manager.get_traceability_link(link_id)
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "message": f"Failed to get traceability link {link_id}"
            }
            return [TextContent(type="text", text=json.dumps(error_result, indent=2))]
    
    @mcp.tool()
    async def generate_traceability_report(
        report_type: str = "summary",
        alm_type: str = None
    ) -> List[TextContent]:
        """Generate comprehensive traceability reports
        
        Args:
            report_type: Type of report ('summary', 'detailed')
            alm_type: Filter by ALM platform type ('azure_devops', 'jira')
        """
        try:
            result = await traceability_manager.generate_traceability_report(
                report_type=report_type,
                alm_type=alm_type
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "message": f"Failed to generate {report_type} traceability report"
            }
            return [TextContent(type="text", text=json.dumps(error_result, indent=2))]
    
    @mcp.tool()
    async def link_session_to_requirements(
        session_id: str,
        requirement_ids: List[str],
        alm_type: str,
        confidence_score: float = 1.0,
        created_by: str = None
    ) -> List[TextContent]:
        """Create traceability links from a session to multiple requirements
        
        Args:
            session_id: ID of the session
            requirement_ids: List of requirement IDs to link to
            alm_type: ALM platform type ('azure_devops', 'jira')
            confidence_score: Confidence score (0.0-1.0)
            created_by: User who created the links
        """
        try:
            results = []
            for req_id in requirement_ids:
                result = await traceability_manager.create_traceability_link(
                    source_type="session",
                    source_id=session_id,
                    target_type="requirement",
                    target_id=req_id,
                    relationship_type="covers",
                    source_alm_type=alm_type,
                    target_alm_type=alm_type,
                    confidence_score=confidence_score,
                    description=f"Session {session_id} covers requirement {req_id}",
                    created_by=created_by
                )
                results.append(result)
            
            summary = {
                "success": True,
                "session_id": session_id,
                "linked_requirements": len(requirement_ids),
                "links_created": len([r for r in results if r.get("success")]),
                "links_failed": len([r for r in results if not r.get("success")]),
                "results": results
            }
            
            return [TextContent(type="text", text=json.dumps(summary, indent=2))]
        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "message": f"Failed to link session {session_id} to requirements"
            }
            return [TextContent(type="text", text=json.dumps(error_result, indent=2))]
    
    @mcp.tool()
    async def link_requirements_to_test_cases(
        requirement_ids: List[str],
        test_case_ids: List[str],
        alm_type: str,
        confidence_score: float = 1.0,
        created_by: str = None
    ) -> List[TextContent]:
        """Create traceability links from requirements to test cases
        
        Args:
            requirement_ids: List of requirement IDs
            test_case_ids: List of test case IDs to link to
            alm_type: ALM platform type ('azure_devops', 'jira')
            confidence_score: Confidence score (0.0-1.0)
            created_by: User who created the links
        """
        try:
            results = []
            for req_id in requirement_ids:
                for tc_id in test_case_ids:
                    result = await traceability_manager.create_traceability_link(
                        source_type="requirement",
                        source_id=req_id,
                        target_type="test_case",
                        target_id=tc_id,
                        relationship_type="tests",
                        source_alm_type=alm_type,
                        target_alm_type=alm_type,
                        confidence_score=confidence_score,
                        description=f"Test case {tc_id} tests requirement {req_id}",
                        created_by=created_by
                    )
                    results.append(result)
            
            summary = {
                "success": True,
                "requirements_count": len(requirement_ids),
                "test_cases_count": len(test_case_ids),
                "total_links_attempted": len(results),
                "links_created": len([r for r in results if r.get("success")]),
                "links_failed": len([r for r in results if not r.get("success")]),
                "results": results
            }
            
            return [TextContent(type="text", text=json.dumps(summary, indent=2))]
        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "message": "Failed to link requirements to test cases"
            }
            return [TextContent(type="text", text=json.dumps(error_result, indent=2))]
    
    @mcp.tool()
    async def get_traceability_matrix_for_session(session_id: str) -> List[TextContent]:
        """Get complete traceability matrix for a session showing all linked items
        
        Args:
            session_id: ID of the session
        """
        try:
            # Get all links for the session
            session_links = await traceability_manager.get_traceability_links_for_item(
                item_type="session",
                item_id=session_id,
                direction="both"
            )
            
            if not session_links["success"]:
                return [TextContent(type="text", text=json.dumps(session_links, indent=2))]
            
            # Build matrix structure
            matrix = {
                "session_id": session_id,
                "total_links": session_links["total_links"],
                "requirements": [],
                "test_cases": [],
                "direct_links": session_links["links"]
            }
            
            # Extract linked requirements and test cases
            for link in session_links["links"]:
                if link["source_type"] == "session" and link["target_type"] == "requirement":
                    matrix["requirements"].append({
                        "id": link["target_id"],
                        "external_id": link["target_external_id"],
                        "alm_type": link["target_alm_type"],
                        "relationship": link["relationship_type"],
                        "confidence": link["confidence_score"]
                    })
                elif link["source_type"] == "session" and link["target_type"] == "test_case":
                    matrix["test_cases"].append({
                        "id": link["target_id"],
                        "external_id": link["target_external_id"],
                        "alm_type": link["target_alm_type"],
                        "relationship": link["relationship_type"],
                        "confidence": link["confidence_score"]
                    })
            
            # Get secondary links (requirements to test cases)
            secondary_links = []
            for req in matrix["requirements"]:
                req_links = await traceability_manager.get_traceability_links_for_item(
                    item_type="requirement",
                    item_id=req["id"],
                    direction="source"
                )
                if req_links["success"]:
                    secondary_links.extend(req_links["links"])
            
            matrix["secondary_links"] = secondary_links
            matrix["requirements_count"] = len(matrix["requirements"])
            matrix["test_cases_count"] = len(matrix["test_cases"])
            matrix["secondary_links_count"] = len(secondary_links)
            
            result = {
                "success": True,
                "matrix": matrix
            }
            
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "message": f"Failed to get traceability matrix for session {session_id}"
            }
            return [TextContent(type="text", text=json.dumps(error_result, indent=2))]

def register_all_tools(mcp, ado_client, jira_client, vector_service, traceability_manager):
    """Register all MCP tools with the server including PostgreSQL traceability tools"""
    
    # Register the new PostgreSQL-based traceability tools
    register_traceability_tools(mcp, traceability_manager)
    
    # Keep existing tools (this is a simplified version - you can add back other tools as needed)
    @mcp.tool()
    async def test_database_connection() -> List[TextContent]:
        """Test the PostgreSQL database connection and schema"""
        try:
            from database_manager import db_manager
            result = await db_manager.test_connection()
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "message": "Failed to test database connection"
            }
            return [TextContent(type="text", text=json.dumps(error_result, indent=2))]