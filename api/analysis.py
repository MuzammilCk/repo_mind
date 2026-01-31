from fastapi import APIRouter, HTTPException
from typing import Optional

from models.requests import CodeQLScanRequest
from models.responses import CodeQLResponse
from services.codeql_service import CodeQLService

router = APIRouter(prefix="/analysis", tags=["analysis"])
codeql_service = CodeQLService()

@router.post("/codeql", response_model=CodeQLResponse)
async def run_codeql_scan(request: CodeQLScanRequest):
    """
    Run CodeQL security and quality analysis on an ingested repository.
    
    **Prerequisites:**
    - Repository must be ingested first (POST /api/ingest)
    - CodeQL CLI must be installed
    
    **Error Codes:**
    - 404: Repository not found (not ingested)
    - 422: Invalid language or query suite
    - 503: CodeQL not available
    - 504: Operation timeout
    - 500: Other errors
    
    **Example:**
    ```json
    {
      "repo_id": "abc12345",
      "language": "python",
      "query_suite": "security-extended"
    }
    ```
    """
    try:
        # Check CodeQL availability first
        if not codeql_service.codeql_available:
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "CodeQL CLI not available",
                    "message": "Download from: https://github.com/github/codeql-cli-binaries",
                    "docs": "https://docs.github.com/en/code-security/codeql-cli"
                }
            )
        
        # Validate query suite early (before subprocess)
        try:
            codeql_service._validate_query_suite(request.query_suite)
        except ValueError as e:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "Invalid query suite",
                    "message": str(e),
                    "allowed_suites": list(codeql_service.ALLOWED_QUERY_SUITES)
                }
            )
        
        # Run the full analysis pipeline
        result = codeql_service.analyze_repository(request)
        return result
        
    except FileNotFoundError as e:
        # Repository not ingested
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Repository not found",
                "message": str(e),
                "hint": "Run POST /api/ingest first"
            }
        )
        
    except ValueError as e:
        # Validation error (repo_id format, language mismatch, etc.)
        raise HTTPException(
            status_code=422,
            detail={
                "error": "Validation error",
                "message": str(e)
            }
        )
        
    except TimeoutError as e:
        # Subprocess timeout
        raise HTTPException(
            status_code=504,
            detail={
                "error": "Operation timeout",
                "message": str(e)
            }
        )
        
    except RuntimeError as e:
        # CodeQL errors, subprocess failures, etc.
        error_message = str(e)
        
        # Check if it's a CodeQL availability issue
        if "not available" in error_message.lower():
            raise HTTPException(status_code=503, detail=str(e))
        
        # Other runtime errors
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Analysis failed",
                "message": error_message
            }
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions (don't catch them in generic handler)
        raise
        
    except Exception as e:
        # Catch-all for unexpected errors
        # Log full traceback server-side but don't expose it
        import traceback
        print(f"❌ Unexpected error in CodeQL analysis:")
        print(traceback.format_exc())
        
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Internal server error",
                "message": "An unexpected error occurred. Check server logs."
            }
        )
