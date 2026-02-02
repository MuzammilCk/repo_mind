"""
Repo Analyzer API - Main FastAPI Application
"""

from fastapi import FastAPI
from fastapi.responses import JSONResponse
import logging

from api import ingest, search, analysis, orchestrator, marathon
from api.middleware import setup_middleware
from utils.metrics import metrics_collector
from config import settings

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Repo Analyzer API",
    description="""
    AI-powered repository analysis platform.
    
    ## Features
    
    * **Ingest**: Clone and process repositories
    * **Search**: Semantic code search with SeaGOAT
    * **Analysis**: Static analysis with CodeQL
    * **Orchestrator**: Multi-step analysis with plan approval
    * **AI Insights**: Gemini-powered analysis (Phase 2)
    
    ## Authentication
    
    API key authentication is planned for production (currently placeholder).
    
    ## Rate Limiting
    
    Default: 100 requests per minute per IP address.
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Setup middleware (CORS, rate limiting, etc.)
setup_middleware(app)

# Include routers
app.include_router(ingest.router, prefix="/api", tags=["Ingest"])
app.include_router(search.router, prefix="/api", tags=["Search"])
app.include_router(analysis.router, prefix="/api", tags=["Analysis"])
app.include_router(orchestrator.router, prefix="/api", tags=["Orchestrator"])
app.include_router(marathon.router, tags=["Marathon"])

logger.info("All routers registered successfully")


@app.get(
    "/",
    summary="Root endpoint",
    description="Returns API information",
    tags=["Info"]
)
async def root():
    """
    Root endpoint - Returns API information
    """
    return {
        "name": "Repo Analyzer API",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs",
        "redoc": "/redoc",
        "openapi": "/openapi.json",
        "health": "/health",
        "metrics": "/metrics"
    }


from services.codeql_service import CodeQLService
from services.gemini_service import GeminiService

# Initialize services at module level for health checks
codeql_service = CodeQLService()
gemini_service = GeminiService()

@app.get(
    "/health",
    summary="Health check",
    description="Returns API health status with service availability",
    tags=["Info"]
)
async def health():
    """
    Health check endpoint with CodeQL and Gemini status
    """
    from datetime import datetime
    
    # Calculate uptime
    uptime_seconds = (datetime.utcnow() - metrics_collector.start_time).total_seconds()
    
    # Get statuses
    codeql_status = codeql_service.get_status()
    gemini_status = gemini_service.get_status()
    
    return {
        "status": "healthy",
        "version": "1.0.0",
        "debug_mode": settings.DEBUG,
        "uptime_seconds": round(uptime_seconds, 2),
        "codeql_available": codeql_status["codeql_available"],
        "codeql_version": codeql_status["codeql_version"],
        "gemini_available": gemini_status["gemini_available"],
        "gemini_model": gemini_status["gemini_model"],
        "api_key_configured": gemini_status["api_key_configured"],
        "services": {
            "ingest": "available",
            "search": "available (requires SeaGOAT)",
            "codeql": "available" if codeql_status["codeql_available"] else "unavailable (CLI missing)",
            "orchestrator": "available",
            "gemini": "available" if gemini_status["gemini_available"] else "unavailable"
        }
    }


@app.get(
    "/metrics",
    summary="API metrics",
    description="Returns request metrics and statistics",
    tags=["Info"]
)
async def metrics():
    """
    Metrics endpoint
    
    Returns metrics about API usage including:
    - Requests per second
    - Average duration
    - Breakdown by endpoint, status code, and method
    """
    from datetime import datetime
    
    return {
        "metrics": metrics_collector.get_metrics(),
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


@app.on_event("startup")
async def startup_event():
    """
    Startup event handler
    """
    logger.info("=" * 80)
    logger.info("Repo Analyzer API Starting...")
    logger.info("=" * 80)
    logger.info("Version: 1.0.0")
    logger.info("Docs: http://localhost:8000/docs")
    logger.info("=" * 80)


@app.on_event("shutdown")
async def shutdown_event():
    """
    Shutdown event handler
    """
    logger.info("Repo Analyzer API Shutting down...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")

# Reload trigger 15


