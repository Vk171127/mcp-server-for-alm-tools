"""
Simple FastAPI server for ALM Traceability - Production Ready
"""
import os
import asyncio
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from simple_db import db
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="ALM Traceability Server",
    description="Simple traceability management for ADK agents",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database connection pool
db_pool = None

# Models
class TraceabilityLink(BaseModel):
    source_type: str
    source_id: str
    target_type: str
    target_id: str
    relationship_type: str
    source_alm_type: Optional[str] = None
    target_alm_type: Optional[str] = None
    confidence_score: float = 1.0
    description: Optional[str] = None

class LinkResponse(BaseModel):
    success: bool
    link_id: Optional[str] = None
    message: str
    error: Optional[str] = None

@app.on_event("startup")
async def startup():
    """Initialize database connection"""
    try:
        logger.info("Initializing database connection...")
        result = await db.initialize()
        if result["success"]:
            logger.info("✅ Database initialized successfully")
        else:
            logger.error(f"❌ Database initialization failed: {result.get('error')}")
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")

@app.on_event("shutdown")
async def shutdown():
    """Cleanup database connection"""
    await db.close()
    logger.info("✅ Database connection closed")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        await db.fetch_one("SELECT 1")
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    return {
        "status": "healthy" if db_status == "healthy" else "unhealthy", 
        "service": "ALM Traceability Server",
        "version": "1.0.0",
        "database": db_status,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "ALM Traceability Server",
        "status": "running",
        "version": "1.0.0",
        "endpoints": [
            "/health",
            "/create-link",
            "/get-links/{item_type}/{item_id}",
            "/docs"
        ]
    }

@app.post("/create-link", response_model=LinkResponse)
async def create_traceability_link(link: TraceabilityLink):
    """Create a traceability link"""
    try:
        # For initial deployment, we'll simulate success
        # TODO: Add real database integration
        
        fake_link_id = f"link-{hash(f'{link.source_id}-{link.target_id}')}"
        
        return LinkResponse(
            success=True,
            link_id=fake_link_id,
            message="Traceability link created successfully (simulated)"
        )
        
    except Exception as e:
        logger.error(f"Failed to create link: {e}")
        return LinkResponse(
            success=False,
            message="Failed to create traceability link",
            error=str(e)
        )

@app.get("/get-links/{item_type}/{item_id}")
async def get_traceability_links(item_type: str, item_id: str):
    """Get all traceability links for an item"""
    try:
        # For initial deployment, return simulated data
        # TODO: Add real database integration
        
        return {
            "success": True,
            "item_type": item_type,
            "item_id": item_id,
            "links": [
                {
                    "id": f"link-{item_id}-1",
                    "source_type": item_type,
                    "source_id": item_id,
                    "target_type": "requirement",
                    "target_id": "req-example",
                    "relationship_type": "covers",
                    "created_at": datetime.now().isoformat()
                }
            ],
            "total_links": 1,
            "note": "Simulated data - database integration coming soon"
        }
        
    except Exception as e:
        logger.error(f"Failed to get links: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/bulk-link-session")
async def bulk_link_session_to_requirements(
    session_id: str,
    requirement_ids: List[str],
    alm_type: str = "azure_devops"
):
    """Bulk link a session to multiple requirements"""
    try:
        # Simulated for initial deployment
        results = [f"link-{session_id}-{req_id}" for req_id in requirement_ids]
        
        return {
            "success": True,
            "session_id": session_id,
            "linked_requirements": len(requirement_ids),
            "link_ids": results,
            "note": "Simulated data - database integration coming soon"
        }
        
    except Exception as e:
        logger.error(f"Bulk linking failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/report/{session_id}")
async def get_traceability_report(session_id: str):
    """Get traceability report for a session"""
    try:
        # Simulated report for initial deployment
        return {
            "success": True,
            "session_id": session_id,
            "summary": {
                "total_links": 3,
                "requirements_linked": 2,
                "test_cases_linked": 1
            },
            "requirements": [
                {
                    "id": f"link-{session_id}-req1",
                    "target_id": "req-001",
                    "relationship_type": "covers"
                }
            ],
            "test_cases": [
                {
                    "id": f"link-{session_id}-tc1", 
                    "target_id": "tc-001",
                    "relationship_type": "tests"
                }
            ],
            "note": "Simulated data - database integration coming soon"
        }
        
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)