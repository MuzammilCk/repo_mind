"""
Gemini API configuration with safety contracts
Enforces deterministic, evidence-based responses
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class GeminiSafetyConfig(BaseModel):
    """
    Safety configuration for Gemini API calls
    
    Contract: Low temperature, deterministic settings
    """
    
    temperature: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Temperature for generation (≤0.3 for safety)"
    )
    
    top_p: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Top-p sampling"
    )
    
    top_k: int = Field(
        default=40,
        ge=1,
        description="Top-k sampling"
    )
    
    max_output_tokens: int = Field(
        default=8192,
        description="Maximum output tokens"
    )
    
    thinking_level: str = Field(
        default="medium",
        pattern="^(low|medium|high)$",
        description="Thinking level (medium/high for planning)"
    )
    
    response_mime_type: str = Field(
        default="application/json",
        description="Force JSON output for work orders"
    )
    
    def to_generation_config(self) -> Dict[str, Any]:
        """Convert to Gemini generation config"""
        return {
            "temperature": self.temperature,
            "top_p": self.top_p,
            "top_k": self.top_k,
            "max_output_tokens": self.max_output_tokens,
            "response_mime_type": self.response_mime_type
        }


# Predefined safety configs
PLANNING_CONFIG = GeminiSafetyConfig(
    temperature=0.2,
    top_p=0.8,
    thinking_level="high",
    response_mime_type="application/json"
)

ANALYSIS_CONFIG = GeminiSafetyConfig(
    temperature=0.3,
    top_p=0.85,
    thinking_level="medium",
    response_mime_type="application/json"
)

GENERATION_CONFIG = GeminiSafetyConfig(
    temperature=0.1,
    top_p=0.7,
    thinking_level="medium",
    response_mime_type="application/json"
)
