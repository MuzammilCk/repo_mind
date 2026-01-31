"""
Analysis API Router
Endpoints for code analysis (CodeQL and full analysis)
"""

from fastapi import APIRouter, HTTPException, status
from typing import Dict
import logging

from models.requests import CodeQLScanRequest, AnalysisRequest
from models.responses import CodeQLResponse, AnalysisResponse
from services.codeql_service import CodeQLService

# Setup logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


@router.post(
    "/analysis/codeql",
    response_model=CodeQLResponse,
    status_code=status.HTTP_200_OK,
    summary="Run CodeQL analysis",
    description="Perform static analysis using CodeQL. Returns security and code quality findings.",
    responses={
        200: {
            "description": "Analysis completed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "repo_id": "a1b2c3d4",
                        "language": "python",
                        "findings": [
                            {
                                "rule_id": "py/sql-injection",
                                "severity": "critical",
                                "message": "Potential SQL injection vulnerability",
                                "file_path": "src/database/queries.py",
                                "start_line": 125,
                                "end_line": 127,
                                "recommendation": "Use parameterized queries"
                            }
                        ],
                        "total_findings": 15,
                        "critical_count": 2,
                        "high_count": 5,
                        "medium_count": 6,
                        "low_count": 2
                    }
                }
            }
        },
        400: {"description": "Invalid request parameters"},
        404: {"description": "Repository not found"},
        500: {"description": "Internal server error or CodeQL not installed"}
    },
    tags=["Analysis"]
)
async def codeql_analysis(request: CodeQLScanRequest) -> CodeQLResponse:
    """
    Run CodeQL static analysis on a repository
    
    - **repo_id**: Repository identifier
    - **language**: Programming language (python, javascript, java, etc.)
    - **query_suite**: Query suite to run (security-extended, security-and-quality, etc.)
    
    Returns security and code quality findings with severity levels.
    """
    try:
        logger.info(f"Running CodeQL analysis on {request.repo_id} ({request.language})")
        service = CodeQLService()
        response = service.analyze_repository(request)
        logger.info(f"CodeQL analysis completed: {response.total_findings} findings")
        return response
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid request: {str(e)}"
        )
    except FileNotFoundError as e:
        logger.error(f"Repository not found: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository '{request.repo_id}' not found. Please ingest it first."
        )
    except RuntimeError as e:
        error_msg = str(e)
        logger.error(f"CodeQL analysis failed: {error_msg}")
        
        # Check if CodeQL is not installed
        if "not found" in error_msg.lower() or "not installed" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="CodeQL CLI not installed. Please install from: https://github.com/github/codeql-cli-binaries/releases"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="CodeQL analysis failed. Please check the repository and language settings."
            )
    except Exception as e:
        logger.error(f"CodeQL analysis failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Analysis failed. Please try again."
        )


@router.post(
    "/analysis/full",
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
    summary="Run full repository analysis",
    description="Orchestrated analysis combining ingestion, search, CodeQL, and AI insights (Phase 2).",
    responses={
        501: {"description": "Not implemented (Phase 2 feature)"}
    },
    tags=["Analysis"]
)
async def full_analysis():
    """
    Run full orchestrated analysis (Phase 2 feature)
    
    **Note**: This endpoint requires Phase 2 (Gemini Integration) to be implemented.
    """
    logger.warning("Full analysis endpoint called but not yet implemented (Phase 2)")
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Full analysis requires Phase 2 (Gemini Integration). Currently only CodeQL analysis is available."
    )
