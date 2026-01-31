"""
Orchestrator API Router
Endpoints for plan creation and execution with approval
"""

from fastapi import APIRouter, HTTPException, status
from typing import Dict
from pydantic import BaseModel, Field
import logging

from models.requests import OrchestratorRequest
from services.orchestrator import OrchestratorService

# Setup logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


class ExecutePlanRequest(BaseModel):
    """Request model for plan execution"""
    plan_id: str = Field(..., description="Plan ID to execute")
    approved_by: str = Field(..., description="Email or ID of approver")
    approval_signature: str = Field(..., description="HMAC-SHA256 signature for approval")
    
    class Config:
        json_schema_extra = {
            "example": {
                "plan_id": "plan_abc123456789",
                "approved_by": "user@example.com",
                "approval_signature": "a1b2c3d4e5f6..."
            }
        }


@router.post(
    "/orchestrate/plan",
    response_model=Dict,
    status_code=status.HTTP_200_OK,
    summary="Create analysis plan",
    description="Create an analysis plan WITHOUT executing any tools. Returns plan with actions list.",
    responses={
        200: {
            "description": "Plan created successfully (not executed)",
            "content": {
                "application/json": {
                    "example": {
                        "plan_id": "plan_abc123456789",
                        "created_at": "2026-01-31T18:00:00Z",
                        "status": "pending_approval",
                        "request": {
                            "repo_id": "test123",
                            "analysis_type": "security",
                            "custom_instructions": "Focus on authentication"
                        },
                        "actions": [
                            {
                                "step": 1,
                                "action": "ingest_repository",
                                "description": "Clone and process repository",
                                "params": {"repo_id": "test123"},
                                "status": "pending"
                            },
                            {
                                "step": 2,
                                "action": "run_codeql",
                                "description": "Run CodeQL static analysis",
                                "params": {
                                    "repo_id": "test123",
                                    "language": "python",
                                    "query_suite": "security-extended"
                                },
                                "status": "pending"
                            }
                        ],
                        "approval_required": True,
                        "approval_instructions": "Call POST /api/orchestrate/execute with plan_id and HMAC signature"
                    }
                }
            }
        },
        400: {"description": "Invalid request parameters"},
        500: {"description": "Internal server error"}
    },
    tags=["Orchestrator"]
)
async def create_plan(request: OrchestratorRequest) -> Dict:
    """
    Create analysis plan WITHOUT executing tools
    
    - **repo_id**: Repository identifier
    - **analysis_type**: Type of analysis (security, performance, architecture, etc.)
    - **custom_instructions**: Optional custom instructions
    
    **IMPORTANT**: This endpoint creates a plan but does NOT execute it.
    To execute, call POST /api/orchestrate/execute with approval signature.
    """
    try:
        logger.info(f"Creating plan for repo: {request.repo_id}")
        service = OrchestratorService()
        plan = service.create_analysis_plan(request)
        logger.info(f"Plan created: {plan['plan_id']} (NOT executed)")
        return plan
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid request: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Plan creation failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Plan creation failed. Please try again."
        )


@router.post(
    "/orchestrate/execute",
    response_model=Dict,
    status_code=status.HTTP_200_OK,
    summary="Execute approved plan",
    description="Execute a previously created plan with HMAC approval signature.",
    responses={
        200: {
            "description": "Plan executed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "plan_id": "plan_abc123456789",
                        "status": "completed",
                        "executed_at": "2026-01-31T18:05:00Z",
                        "results": {
                            "repo_id": "test123",
                            "analysis_type": "security",
                            "summary": "Orchestrated analysis completed",
                            "action_results": [
                                {
                                    "step": 1,
                                    "action": "ingest_repository",
                                    "status": "completed",
                                    "result": {"status": "completed"}
                                }
                            ],
                            "total_actions": 3,
                            "completed_actions": 3
                        }
                    }
                }
            }
        },
        403: {"description": "Invalid approval signature"},
        404: {"description": "Plan not found"},
        500: {"description": "Internal server error"}
    },
    tags=["Orchestrator"]
)
async def execute_plan(request: ExecutePlanRequest) -> Dict:
    """
    Execute an approved plan with HMAC signature verification
    
    - **plan_id**: Plan ID from create_plan endpoint
    - **approved_by**: Email or ID of person approving
    - **approval_signature**: HMAC-SHA256 signature
    
    **Signature Generation:**
    ```python
    import hmac, hashlib, json
    plan_json = json.dumps(plan, sort_keys=True)
    message = f"{plan_json}:{approved_by}"
    signature = hmac.new(secret_key.encode(), message.encode(), hashlib.sha256).hexdigest()
    ```
    
    **IMPORTANT**: Signature verification prevents unauthorized execution.
    """
    try:
        logger.info(f"Executing plan: {request.plan_id} approved by {request.approved_by}")
        service = OrchestratorService()
        result = service.execute_plan(
            request.plan_id,
            request.approved_by,
            request.approval_signature
        )
        logger.info(f"Plan executed: {request.plan_id}")
        return result
        
    except FileNotFoundError as e:
        logger.error(f"Plan not found: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan '{request.plan_id}' not found. Please create a plan first."
        )
    except PermissionError as e:
        logger.error(f"Invalid signature: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid approval signature. Signature verification failed."
        )
    except Exception as e:
        logger.error(f"Plan execution failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Plan execution failed. Please try again."
        )


@router.get(
    "/orchestrate/plan/{plan_id}",
    response_model=Dict,
    status_code=status.HTTP_200_OK,
    summary="Get plan details",
    description="Retrieve details of a created plan",
    responses={
        200: {"description": "Plan details retrieved"},
        404: {"description": "Plan not found"}
    },
    tags=["Orchestrator"]
)
async def get_plan(plan_id: str) -> Dict:
    """
    Get details of a created plan
    
    - **plan_id**: Plan ID
    
    Returns plan details including status and actions.
    """
    try:
        logger.info(f"Retrieving plan: {plan_id}")
        service = OrchestratorService()
        plan = service._load_plan(plan_id)
        
        if not plan:
            raise FileNotFoundError(f"Plan {plan_id} not found")
        
        return plan
        
    except FileNotFoundError as e:
        logger.error(f"Plan not found: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan '{plan_id}' not found."
        )
    except Exception as e:
        logger.error(f"Plan retrieval failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Plan retrieval failed. Please try again."
        )
