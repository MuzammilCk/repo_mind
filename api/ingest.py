"""
Ingest API Router
Endpoints for repository ingestion
"""

from fastapi import APIRouter, HTTPException, status
from typing import Dict
import logging

from models.requests import IngestRequest
from models.responses import IngestResponse
from services.ingest_service import IngestService

# Setup logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


@router.post(
    "/ingest",
    response_model=IngestResponse,
    status_code=status.HTTP_200_OK,
    summary="Ingest a repository",
    description="Clone and process a repository for analysis. Generates repo.md and tree.json files.",
    responses={
        200: {
            "description": "Repository ingested successfully",
            "content": {
                "application/json": {
                    "example": {
                        "repo_id": "a1b2c3d4",
                        "status": "completed",
                        "file_count": 150,
                        "total_lines": 12500,
                        "total_size_bytes": 524288,
                        "languages": {"Python": 85, "JavaScript": 10, "Other": 5},
                        "repo_md_path": "./workspace/ingest/a1b2c3d4/repo.md",
                        "tree_json_path": "./workspace/ingest/a1b2c3d4/tree.json",
                        "content_signature": "abc123..."
                    }
                }
            }
        },
        400: {"description": "Invalid request parameters"},
        500: {"description": "Internal server error"}
    },
    tags=["Ingest"]
)
async def ingest_repository(request: IngestRequest) -> IngestResponse:
    """
    Ingest a repository from URL or local path
    
    - **source**: Repository source (URL or local path)
    - **include_patterns**: File patterns to include (default: common code files)
    - **exclude_patterns**: File patterns to exclude (default: node_modules, .git, etc.)
    
    Returns repository metadata and paths to generated files.
    """
    try:
        logger.info(f"Ingesting repository: {request.source}")
        service = IngestService()
        response = service.ingest_repository(request)
        logger.info(f"Ingestion completed: {response.repo_id}")
        return response
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid request: {str(e)}"
        )
    except FileNotFoundError as e:
        logger.error(f"File not found: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository not found: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Ingestion failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Repository ingestion failed. Please try again."
        )


@router.get(
    "/ingest/{repo_id}",
    response_model=Dict[str, str],
    status_code=status.HTTP_200_OK,
    summary="Get repository content",
    description="Retrieve the processed repository content (repo.md)",
    responses={
        200: {
            "description": "Repository content retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "repo_id": "a1b2c3d4",
                        "content": "# Repository Content\n\n## File: main.py\n..."
                    }
                }
            }
        },
        404: {"description": "Repository not found"},
        500: {"description": "Internal server error"}
    },
    tags=["Ingest"]
)
async def get_repository_content(repo_id: str) -> Dict[str, str]:
    """
    Get the processed content of an ingested repository
    
    - **repo_id**: Unique repository identifier
    
    Returns the repo.md content as a string.
    """
    try:
        logger.info(f"Retrieving content for repo: {repo_id}")
        service = IngestService()
        content = service.get_repo_content(repo_id)
        logger.info(f"Content retrieved for repo: {repo_id}")
        return {
            "repo_id": repo_id,
            "content": content
        }
        
    except FileNotFoundError as e:
        logger.error(f"Repository not found: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository '{repo_id}' not found. Please ingest it first."
        )
    except Exception as e:
        logger.error(f"Content retrieval failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve repository content. Please try again."
        )
