"""
Response models for Repo Analyzer API
All models include JSON Schema examples and proper typing
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


class IngestResponse(BaseModel):
    """Response from ingest operation"""
    repo_id: str = Field(
        ...,
        description="Unique repository identifier",
        examples=["a1b2c3d4"]
    )
    status: str = Field(
        ...,
        description="Ingestion status",
        examples=["completed", "failed", "in_progress"]
    )
    file_count: int = Field(
        ...,
        ge=0,
        description="Number of files ingested",
        examples=[150]
    )
    total_lines: int = Field(
        ...,
        ge=0,
        description="Total lines of code",
        examples=[12500]
    )
    languages: Dict[str, int] = Field(
        ...,
        description="File count by language/extension",
        examples=[{".py": 45, ".js": 30, ".md": 5}]
    )
    repo_md_path: str = Field(
        ...,
        description="Path to generated repo.md file",
        examples=["./workspace/ingest/a1b2c3d4/repo.md"]
    )
    tree_json_path: str = Field(
        ...,
        description="Path to generated tree.json file",
        examples=["./workspace/ingest/a1b2c3d4/tree.json"]
    )
    created_at: datetime = Field(
        ...,
        description="Timestamp of ingestion completion"
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "repo_id": "a1b2c3d4",
                    "status": "completed",
                    "file_count": 150,
                    "total_lines": 12500,
                    "languages": {".py": 45, ".js": 30, ".md": 5},
                    "repo_md_path": "./workspace/ingest/a1b2c3d4/repo.md",
                    "tree_json_path": "./workspace/ingest/a1b2c3d4/tree.json",
                    "created_at": "2026-01-31T12:00:00Z"
                }
            ]
        }
    }


class SearchResult(BaseModel):
    """Single semantic search result"""
    file_path: str = Field(
        ...,
        description="Relative path to file in repository",
        examples=["src/auth/login.py"]
    )
    line_number: int = Field(
        ...,
        ge=0,
        description="Line number where match was found",
        examples=[42]
    )
    code_snippet: str = Field(
        ...,
        description="Code snippet containing the match",
        examples=["def authenticate_user(username: str, password: str):"]
    )
    relevance_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Relevance score (0.0 to 1.0)",
        examples=[0.95]
    )
    context: str = Field(
        ...,
        description="Additional context around the match",
        examples=["Authentication module - user login handler"]
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "file_path": "src/auth/login.py",
                    "line_number": 42,
                    "code_snippet": "def authenticate_user(username: str, password: str):",
                    "relevance_score": 0.95,
                    "context": "Authentication module"
                }
            ]
        }
    }


class SemanticSearchResponse(BaseModel):
    """Response from semantic search"""
    repo_id: str = Field(
        ...,
        description="Repository ID that was searched",
        examples=["a1b2c3d4"]
    )
    query: str = Field(
        ...,
        description="Search query that was executed",
        examples=["authentication logic"]
    )
    results: List[SearchResult] = Field(
        ...,
        description="List of search results"
    )
    total_results: int = Field(
        ...,
        ge=0,
        description="Total number of results found",
        examples=[10]
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "repo_id": "a1b2c3d4",
                    "query": "authentication logic",
                    "results": [
                        {
                            "file_path": "src/auth/login.py",
                            "line_number": 42,
                            "code_snippet": "def authenticate_user(username: str, password: str):",
                            "relevance_score": 0.95,
                            "context": "Authentication module"
                        }
                    ],
                    "total_results": 1
                }
            ]
        }
    }


class SeverityEnum(str, Enum):
    """Severity levels for findings"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class CodeQLFinding(BaseModel):
    """Single CodeQL finding"""
    rule_id: str = Field(
        ...,
        description="CodeQL rule identifier",
        examples=["py/sql-injection", "js/xss"]
    )
    severity: SeverityEnum = Field(
        ...,
        description="Severity level of the finding"
    )
    message: str = Field(
        ...,
        description="Description of the finding",
        examples=["Potential SQL injection vulnerability"]
    )
    file_path: str = Field(
        ...,
        description="File path where finding was detected",
        examples=["src/database/queries.py"]
    )
    start_line: int = Field(
        ...,
        ge=0,
        description="Starting line number",
        examples=[125]
    )
    end_line: int = Field(
        ...,
        ge=0,
        description="Ending line number",
        examples=[127]
    )
    recommendation: Optional[str] = Field(
        None,
        description="Recommended fix or mitigation",
        examples=["Use parameterized queries instead of string concatenation"]
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "rule_id": "py/sql-injection",
                    "severity": "critical",
                    "message": "Potential SQL injection vulnerability",
                    "file_path": "src/database/queries.py",
                    "start_line": 125,
                    "end_line": 127,
                    "recommendation": "Use parameterized queries"
                }
            ]
        }
    }


class CodeQLResponse(BaseModel):
    """Response from CodeQL scan"""
    repo_id: str = Field(
        ...,
        description="Repository ID that was scanned",
        examples=["a1b2c3d4"]
    )
    language: str = Field(
        ...,
        description="Programming language analyzed",
        examples=["python"]
    )
    findings: List[CodeQLFinding] = Field(
        ...,
        description="List of security findings"
    )
    total_findings: int = Field(
        ...,
        ge=0,
        description="Total number of findings",
        examples=[15]
    )
    critical_count: int = Field(
        ...,
        ge=0,
        description="Number of critical severity findings",
        examples=[2]
    )
    high_count: int = Field(
        ...,
        ge=0,
        description="Number of high severity findings",
        examples=[5]
    )
    medium_count: int = Field(
        ...,
        ge=0,
        description="Number of medium severity findings",
        examples=[6]
    )
    low_count: int = Field(
        ...,
        ge=0,
        description="Number of low severity findings",
        examples=[2]
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "repo_id": "a1b2c3d4",
                    "language": "python",
                    "findings": [],
                    "total_findings": 15,
                    "critical_count": 2,
                    "high_count": 5,
                    "medium_count": 6,
                    "low_count": 2
                }
            ]
        }
    }


class Issue(BaseModel):
    """Analyzed issue with fix recommendations"""
    title: str = Field(
        ...,
        description="Issue title",
        max_length=200,
        examples=["SQL Injection in User Query Handler"]
    )
    description: str = Field(
        ...,
        description="Detailed description of the issue",
        examples=["User input is directly concatenated into SQL query without sanitization"]
    )
    severity: SeverityEnum = Field(
        ...,
        description="Severity level"
    )
    evidence: List[str] = Field(
        ...,
        description="Evidence (file paths, line numbers, CodeQL findings)",
        examples=[["src/database/queries.py:125-127", "CodeQL rule: py/sql-injection"]]
    )
    fix_steps: List[str] = Field(
        ...,
        description="Recommended steps to fix the issue",
        examples=[
            [
                "Replace string concatenation with parameterized queries",
                "Use SQLAlchemy ORM or prepared statements",
                "Add input validation"
            ]
        ]
    )
    priority: int = Field(
        ...,
        ge=1,
        le=10,
        description="Priority level (1=highest, 10=lowest)",
        examples=[1]
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "title": "SQL Injection Vulnerability",
                    "description": "User input concatenated into SQL query",
                    "severity": "critical",
                    "evidence": ["src/database/queries.py:125-127"],
                    "fix_steps": ["Use parameterized queries", "Add input validation"],
                    "priority": 1
                }
            ]
        }
    }


class AnalysisResponse(BaseModel):
    """Complete analysis response"""
    repo_id: str = Field(
        ...,
        description="Repository ID",
        examples=["a1b2c3d4"]
    )
    interaction_id: str = Field(
        ...,
        description="Gemini interaction ID for follow-ups",
        examples=["interaction-xyz789"]
    )
    architecture_summary: str = Field(
        ...,
        description="High-level architecture summary",
        examples=["FastAPI application with PostgreSQL database and Redis cache"]
    )
    top_issues: List[Issue] = Field(
        ...,
        description="Top priority issues found"
    )
    recommendations: List[str] = Field(
        ...,
        description="General recommendations",
        examples=[
            [
                "Implement input validation across all endpoints",
                "Add rate limiting to API routes",
                "Enable CORS with specific origins"
            ]
        ]
    )
    report_path: str = Field(
        ...,
        description="Path to detailed analysis report",
        examples=["./workspace/output/a1b2c3d4/analysis_report.md"]
    )
    raw_report_json: Dict[str, Any] = Field(
        ...,
        description="Raw analysis data in JSON format"
    )
    created_at: datetime = Field(
        ...,
        description="Analysis completion timestamp"
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "repo_id": "a1b2c3d4",
                    "interaction_id": "interaction-xyz789",
                    "architecture_summary": "FastAPI application with PostgreSQL",
                    "top_issues": [],
                    "recommendations": ["Add input validation", "Enable rate limiting"],
                    "report_path": "./workspace/output/a1b2c3d4/report.md",
                    "raw_report_json": {},
                    "created_at": "2026-01-31T12:00:00Z"
                }
            ]
        }
    }
