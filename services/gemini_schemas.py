"""
JSON schemas for Gemini Interaction API responses.
Explicit schemas for anti-hallucination.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator

# Schema 1: Analysis Plan
class InvestigationArea(BaseModel):
    """Single investigation area in analysis plan"""
    area: str = Field(..., description="Area name (architecture, security, etc.)")
    aspects: List[str] = Field(..., description="Specific aspects to examine")
    tools: List[str] = Field(..., description="Tools to use (semantic_search, codeql)")
    priority: int = Field(..., ge=1, le=5, description="Priority 1-5")

class AnalysisPlanSchema(BaseModel):
    """Complete analysis plan schema"""
    investigation_areas: List[InvestigationArea] = Field(..., min_items=1, max_items=10)
    search_queries: List[str] = Field(..., max_items=20, description="SeaGOAT queries")
    security_focus_areas: List[str] = Field(..., max_items=10)
    expected_issues: List[str] = Field(..., max_items=10)
    
    @field_validator('search_queries')
    @classmethod
    def validate_queries(cls, v):
        """Ensure queries are not empty strings"""
        return [q.strip() for q in v if q and q.strip()]

# Schema 2: Issue
class IssueSchema(BaseModel):
    """Single issue in analysis"""
    title: str = Field(..., min_length=5, max_length=200)
    description: str = Field(..., min_length=10, max_length=2000)
    severity: str = Field(..., pattern="^(critical|high|medium|low)$")
    evidence: List[str] = Field(..., min_items=1, max_items=20, description="file:line citations")
    fix_steps: List[str] = Field(..., min_items=1, max_items=5)
    priority: int = Field(..., ge=1, le=5)
    
    @field_validator('evidence')
    @classmethod
    def validate_evidence_format(cls, v):
        """Ensure evidence follows file:line format"""
        validated = []
        for item in v:
            if ':' not in item:
                raise ValueError(f"Evidence must be in 'file:line' format, got: {item}")
            validated.append(item.strip())
        return validated

# Schema 3: Analysis Response
class AnalysisSchema(BaseModel):
    """Complete analysis response schema"""
    architecture_summary: str = Field(..., min_length=50, max_length=5000)
    top_issues: List[IssueSchema] = Field(..., min_items=0, max_items=10)
    recommendations: List[str] = Field(..., min_items=1, max_items=10)
    
    @field_validator('top_issues')
    @classmethod
    def validate_issues_ordered(cls, v):
        """Ensure issues are ordered by priority"""
        if not v:
            return v
        priorities = [issue.priority for issue in v]
        if priorities != sorted(priorities):
            raise ValueError("Issues must be ordered by priority (1=highest)")
        return v

# Schema Registry
SCHEMA_REGISTRY = {
    "analysis_plan": AnalysisPlanSchema,
    "analysis": AnalysisSchema
}
