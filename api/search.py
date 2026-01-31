"""
Search API Router
Endpoints for semantic code search
"""

from fastapi import APIRouter, HTTPException, status
from typing import Dict
import logging

from models.requests import SemanticSearchRequest
from models.responses import SemanticSearchResponse
from services.search_service import SearchService

# Setup logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


@router.post(
    "/search/semantic",
    response_model=SemanticSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Semantic code search",
    description="Search code semantically using SeaGOAT. Returns relevant code snippets with context.",
    responses={
        200: {
            "description": "Search completed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "repo_id": "a1b2c3d4",
                        "query": "authentication",
                        "results": [
                            {
                                "file_path": "src/auth/login.py",
                                "line_number": 42,
                                "code_snippet": "def authenticate_user(username, password):",
                                "relevance_score": 0.95,
                                "context": "Found in src/auth/login.py"
                            }
                        ],
                        "total_results": 5
                    }
                }
            }
        },
        400: {"description": "Invalid request parameters"},
        404: {"description": "Repository not found or not indexed"},
        500: {"description": "Internal server error"}
    },
    tags=["Search"]
)
async def semantic_search(request: SemanticSearchRequest) -> SemanticSearchResponse:
    """
    Perform semantic code search on an ingested repository
    
    - **repo_id**: Repository identifier
    - **query**: Search query (natural language or code snippet)
    - **limit**: Maximum number of results (default: 10, max: 50)
    
    Returns relevant code snippets with relevance scores.
    """
    try:
        logger.info(f"Searching repo {request.repo_id} for: {request.query}")
        service = SearchService()
        response = service.search(request)
        logger.info(f"Search completed: {response.total_results} results")
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
            detail=f"Repository '{request.repo_id}' not found. Please ingest and index it first."
        )
    except RuntimeError as e:
        logger.error(f"Search failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Search service error. Please ensure SeaGOAT is installed and the repository is indexed."
        )
    except Exception as e:
        logger.error(f"Search failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Search failed. Please try again."
        )


@router.post(
    "/search/index/{repo_id}",
    response_model=Dict,
    status_code=status.HTTP_200_OK,
    summary="Index repository for search",
    description="Index a repository with SeaGOAT for semantic search. Must be done before searching.",
    responses={
        200: {
            "description": "Repository indexed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "repo_id": "a1b2c3d4",
                        "status": "indexed",
                        "doc_count": 150,
                        "index_time_seconds": 12.5,
                        "indexed_at": "2026-01-31T17:50:00Z"
                    }
                }
            }
        },
        404: {"description": "Repository not found"},
        500: {"description": "Internal server error"}
    },
    tags=["Search"]
)
async def index_repository(repo_id: str) -> Dict:
    """
    Index a repository for semantic search
    
    - **repo_id**: Repository identifier
    
    Returns indexing metadata including document count and time taken.
    """
    try:
        logger.info(f"Indexing repository: {repo_id}")
        service = SearchService()
        result = service.index_repository(repo_id)
        logger.info(f"Indexing completed for repo: {repo_id}")
        return result
        
    except FileNotFoundError as e:
        logger.error(f"Repository not found: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository '{repo_id}' not found. Please ingest it first."
        )
    except RuntimeError as e:
        logger.error(f"Indexing failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Indexing service error. Please ensure SeaGOAT is installed."
        )
    except Exception as e:
        logger.error(f"Indexing failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Indexing failed. Please try again."
        )
