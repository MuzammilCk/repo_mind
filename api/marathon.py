"""
Marathon Agent API endpoint
For Gemini 3 Hackathon - Autonomous OSS Discovery
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from services.gemini_service import GeminiService

router = APIRouter(prefix="/api/marathon", tags=["marathon"])

gemini_service = GeminiService()


class MarathonRequest(BaseModel):
    goal: str
    max_iterations: Optional[int] = 15
    thinking_level: Optional[str] = "high"


@router.post("/run")
async def run_marathon_agent(request: MarathonRequest):
    """
    Run the Marathon Agent - Autonomous OSS Discovery
    
    Example goal: "Build me a task management app with React and FastAPI"
    """
    try:
        result = gemini_service.marathon_agent(
            user_goal=request.goal,
            max_iterations=request.max_iterations,
            thinking_level=request.thinking_level
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
