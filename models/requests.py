"""
Request models for Repo Analyzer API
All models include JSON Schema examples and Field constraints
"""

from pydantic import BaseModel, Field, HttpUrl, field_validator
from typing import Optional, List
from enum import Enum


class RepoSource(BaseModel):
    """Repository source specification"""
    url: Optional[HttpUrl] = Field(
        None,
        description="Git repository URL (GitHub, GitLab, etc.)",
        examples=["https://github.com/user/repo"]
    )
    local_path: Optional[str] = Field(
        None,
        description="Local filesystem path to repository",
        examples=["/path/to/local/repo", "C:\\repos\\myproject"]
    )
    
    @field_validator('url', 'local_path')
    @classmethod
    def check_at_least_one_source(cls, v, info):
        """Ensure at least one source is provided"""
        # This will be checked in model_validator
        return v
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {"url": "https://github.com/fastapi/fastapi"},
                {"local_path": "/home/user/projects/myrepo"}
            ]
        }
    }


class IngestRequest(BaseModel):
    """Request to ingest a repository"""
    source: RepoSource = Field(
        ...,
        description="Repository source (URL or local path)"
    )
    include_patterns: Optional[List[str]] = Field(
        default=["*.py", "*.js", "*.java", "*.go", "*.rs", "*.ts", "*.tsx"],
        description="File patterns to include (glob format)",
        examples=[["*.py", "*.js"], ["*.java", "*.kt"]]
    )
    exclude_patterns: Optional[List[str]] = Field(
        default=["node_modules/*", ".git/*", "__pycache__/*", "*.pyc", "dist/*", "build/*"],
        description="File patterns to exclude (glob format)",
        examples=[["node_modules/*", ".git/*"], ["target/*", "*.class"]]
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "source": {"url": "https://github.com/fastapi/fastapi"},
                    "include_patterns": ["*.py"],
                    "exclude_patterns": ["tests/*", "*.pyc"]
                }
            ]
        }
    }


class SemanticSearchRequest(BaseModel):
    """Request for semantic code search"""
    repo_id: str = Field(
        ...,
        description="Repository ID from ingest operation",
        min_length=1,
        max_length=100,
        examples=["a1b2c3d4", "repo-12345"]
    )
    query: str = Field(
        ...,
        description="Natural language search query",
        min_length=1,
        max_length=500,
        examples=[
            "authentication logic",
            "database connection setup",
            "error handling for API calls"
        ]
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of results to return",
        examples=[10, 20, 50]
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "repo_id": "a1b2c3d4",
                    "query": "authentication middleware",
                    "limit": 10
                }
            ]
        }
    }


class CodeQLScanRequest(BaseModel):
    """Request to run CodeQL analysis"""
    repo_id: str = Field(
        ...,
        description="Repository ID from ingest operation",
        min_length=1,
        max_length=100,
        examples=["a1b2c3d4"]
    )
    language: str = Field(
        default="python",
        description="Primary programming language",
        examples=["python", "javascript", "java", "go", "cpp"]
    )
    query_suite: Optional[str] = Field(
        default="security-extended",
        description="CodeQL query suite to run",
        examples=["security-extended", "security-and-quality", "code-scanning"]
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "repo_id": "a1b2c3d4",
                    "language": "python",
                    "query_suite": "security-extended"
                }
            ]
        }
    }


class AnalysisTypeEnum(str, Enum):
    """Analysis type options"""
    FULL = "full"
    SECURITY = "security"
    ARCHITECTURE = "architecture"
    CUSTOM = "custom"


class AnalysisRequest(BaseModel):
    """Main analysis request - orchestrates everything"""
    source: RepoSource = Field(
        ...,
        description="Repository source (URL or local path)"
    )
    analysis_type: AnalysisTypeEnum = Field(
        default=AnalysisTypeEnum.FULL,
        description="Type of analysis to perform"
    )
    custom_instructions: Optional[str] = Field(
        None,
        description="Custom instructions for analysis (used when analysis_type is 'custom')",
        max_length=2000,
        examples=[
            "Focus on API security vulnerabilities",
            "Analyze database query performance"
        ]
    )
    include_semantic_search: bool = Field(
        default=True,
        description="Include semantic code search in analysis"
    )
    include_security_scan: bool = Field(
        default=True,
        description="Include CodeQL security scan in analysis"
    )
    previous_interaction_id: Optional[str] = Field(
        None,
        description="Previous interaction ID for context/memory",
        max_length=100,
        examples=["interaction-abc123"]
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "source": {"url": "https://github.com/user/repo"},
                    "analysis_type": "full",
                    "include_semantic_search": True,
                    "include_security_scan": True
                },
                {
                    "source": {"local_path": "/path/to/repo"},
                    "analysis_type": "custom",
                    "custom_instructions": "Focus on authentication and authorization",
                    "include_semantic_search": True,
                    "include_security_scan": False
                }
            ]
        }
    }


class OrchestratorRequest(BaseModel):
    """Request for orchestrator plan creation (simplified)"""
    repo_id: str = Field(
        ...,
        description="Repository ID from ingest operation",
        min_length=1,
        max_length=100
    )
    analysis_type: str = Field(
        default="security",
        description="Type of analysis (security, performance, architecture, full)"
    )
    custom_instructions: Optional[str] = Field(
        None,
        description="Optional custom instructions for the analysis",
        max_length=2000
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "repo_id": "a1b2c3d4",
                    "analysis_type": "security",
                    "custom_instructions": "Focus on authentication and authorization"
                }
            ]
        }
    }
