"""
Unit tests for Pydantic request/response models
Tests validation, constraints, and schema compliance
"""

import pytest
from pydantic import ValidationError
from datetime import datetime

from models.requests import (
    RepoSource,
    IngestRequest,
    SemanticSearchRequest,
    CodeQLScanRequest,
    AnalysisRequest,
    AnalysisTypeEnum
)
from models.responses import (
    IngestResponse,
    SearchResult,
    SemanticSearchResponse,
    CodeQLFinding,
    CodeQLResponse,
    Issue,
    AnalysisResponse,
    SeverityEnum
)


class TestRepoSource:
    """Tests for RepoSource model"""
    
    def test_valid_url_source(self):
        """Test valid URL source"""
        source = RepoSource(url="https://github.com/user/repo")
        assert source.url is not None
        assert source.local_path is None
    
    def test_valid_local_path_source(self):
        """Test valid local path source"""
        source = RepoSource(local_path="/path/to/repo")
        assert source.local_path == "/path/to/repo"
        assert source.url is None
    
    def test_both_sources(self):
        """Test providing both sources (should be valid)"""
        source = RepoSource(
            url="https://github.com/user/repo",
            local_path="/path/to/repo"
        )
        assert source.url is not None
        assert source.local_path is not None


class TestIngestRequest:
    """Tests for IngestRequest model"""
    
    def test_valid_ingest_request(self):
        """Test valid ingest request"""
        request = IngestRequest(
            source=RepoSource(url="https://github.com/user/repo"),
            include_patterns=["*.py"],
            exclude_patterns=[".git/*"]
        )
        assert request.source.url is not None
        assert len(request.include_patterns) == 1
    
    def test_default_patterns(self):
        """Test default include/exclude patterns"""
        request = IngestRequest(
            source=RepoSource(url="https://github.com/user/repo")
        )
        assert len(request.include_patterns) > 0
        assert len(request.exclude_patterns) > 0
        assert "*.py" in request.include_patterns
        assert ".git/*" in request.exclude_patterns


class TestSemanticSearchRequest:
    """Tests for SemanticSearchRequest model"""
    
    def test_valid_search_request(self):
        """Test valid search request"""
        request = SemanticSearchRequest(
            repo_id="a1b2c3d4",
            query="authentication logic",
            limit=10
        )
        assert request.repo_id == "a1b2c3d4"
        assert request.query == "authentication logic"
        assert request.limit == 10
    
    def test_default_limit(self):
        """Test default limit value"""
        request = SemanticSearchRequest(
            repo_id="a1b2c3d4",
            query="test query"
        )
        assert request.limit == 10
    
    def test_invalid_limit_too_low(self):
        """Test limit below minimum (should fail)"""
        with pytest.raises(ValidationError) as exc_info:
            SemanticSearchRequest(
                repo_id="a1b2c3d4",
                query="test",
                limit=0
            )
        assert "limit" in str(exc_info.value).lower()
    
    def test_invalid_limit_too_high(self):
        """Test limit above maximum (should fail)"""
        with pytest.raises(ValidationError) as exc_info:
            SemanticSearchRequest(
                repo_id="a1b2c3d4",
                query="test",
                limit=100
            )
        assert "limit" in str(exc_info.value).lower()
    
    def test_empty_repo_id(self):
        """Test empty repo_id (should fail)"""
        with pytest.raises(ValidationError):
            SemanticSearchRequest(
                repo_id="",
                query="test"
            )
    
    def test_empty_query(self):
        """Test empty query (should fail)"""
        with pytest.raises(ValidationError):
            SemanticSearchRequest(
                repo_id="a1b2c3d4",
                query=""
            )


class TestCodeQLScanRequest:
    """Tests for CodeQLScanRequest model"""
    
    def test_valid_codeql_request(self):
        """Test valid CodeQL request"""
        request = CodeQLScanRequest(
            repo_id="a1b2c3d4",
            language="python",
            query_suite="security-extended"
        )
        assert request.repo_id == "a1b2c3d4"
        assert request.language == "python"
        assert request.query_suite == "security-extended"
    
    def test_default_values(self):
        """Test default language and query_suite"""
        request = CodeQLScanRequest(repo_id="a1b2c3d4")
        assert request.language == "python"
        assert request.query_suite == "security-extended"


class TestAnalysisRequest:
    """Tests for AnalysisRequest model"""
    
    def test_valid_analysis_request(self):
        """Test valid analysis request"""
        request = AnalysisRequest(
            source=RepoSource(url="https://github.com/user/repo"),
            analysis_type=AnalysisTypeEnum.FULL,
            include_semantic_search=True,
            include_security_scan=True
        )
        assert request.source.url is not None
        assert request.analysis_type == AnalysisTypeEnum.FULL
    
    def test_custom_analysis_with_instructions(self):
        """Test custom analysis with instructions"""
        request = AnalysisRequest(
            source=RepoSource(url="https://github.com/user/repo"),
            analysis_type=AnalysisTypeEnum.CUSTOM,
            custom_instructions="Focus on API security"
        )
        assert request.analysis_type == AnalysisTypeEnum.CUSTOM
        assert request.custom_instructions == "Focus on API security"
    
    def test_invalid_analysis_type(self):
        """Test invalid analysis type (should fail)"""
        with pytest.raises(ValidationError):
            AnalysisRequest(
                source=RepoSource(url="https://github.com/user/repo"),
                analysis_type="invalid_type"
            )


class TestIngestResponse:
    """Tests for IngestResponse model"""
    
    def test_valid_ingest_response(self):
        """Test valid ingest response"""
        response = IngestResponse(
            repo_id="a1b2c3d4",
            status="completed",
            file_count=150,
            total_lines=12500,
            languages={".py": 45, ".js": 30},
            repo_md_path="./workspace/ingest/a1b2c3d4/repo.md",
            tree_json_path="./workspace/ingest/a1b2c3d4/tree.json",
            created_at=datetime.utcnow()
        )
        assert response.repo_id == "a1b2c3d4"
        assert response.file_count == 150
        assert response.total_lines == 12500
    
    def test_negative_file_count(self):
        """Test negative file count (should fail)"""
        with pytest.raises(ValidationError):
            IngestResponse(
                repo_id="a1b2c3d4",
                status="completed",
                file_count=-1,
                total_lines=100,
                languages={},
                repo_md_path="path",
                tree_json_path="path",
                created_at=datetime.utcnow()
            )


class TestSearchResult:
    """Tests for SearchResult model"""
    
    def test_valid_search_result(self):
        """Test valid search result"""
        result = SearchResult(
            file_path="src/auth/login.py",
            line_number=42,
            code_snippet="def authenticate_user():",
            relevance_score=0.95,
            context="Authentication module"
        )
        assert result.file_path == "src/auth/login.py"
        assert result.relevance_score == 0.95
    
    def test_invalid_relevance_score_too_high(self):
        """Test relevance score above 1.0 (should fail)"""
        with pytest.raises(ValidationError):
            SearchResult(
                file_path="test.py",
                line_number=1,
                code_snippet="code",
                relevance_score=1.5,
                context=""
            )
    
    def test_invalid_relevance_score_negative(self):
        """Test negative relevance score (should fail)"""
        with pytest.raises(ValidationError):
            SearchResult(
                file_path="test.py",
                line_number=1,
                code_snippet="code",
                relevance_score=-0.1,
                context=""
            )


class TestCodeQLFinding:
    """Tests for CodeQLFinding model"""
    
    def test_valid_codeql_finding(self):
        """Test valid CodeQL finding"""
        finding = CodeQLFinding(
            rule_id="py/sql-injection",
            severity=SeverityEnum.CRITICAL,
            message="Potential SQL injection",
            file_path="src/db/queries.py",
            start_line=125,
            end_line=127,
            recommendation="Use parameterized queries"
        )
        assert finding.rule_id == "py/sql-injection"
        assert finding.severity == SeverityEnum.CRITICAL
    
    def test_invalid_severity(self):
        """Test invalid severity enum (should fail)"""
        with pytest.raises(ValidationError):
            CodeQLFinding(
                rule_id="test",
                severity="invalid",
                message="test",
                file_path="test.py",
                start_line=1,
                end_line=1
            )


class TestCodeQLResponse:
    """Tests for CodeQLResponse model"""
    
    def test_valid_codeql_response(self):
        """Test valid CodeQL response"""
        response = CodeQLResponse(
            repo_id="a1b2c3d4",
            language="python",
            findings=[],
            total_findings=0,
            critical_count=0,
            high_count=0,
            medium_count=0,
            low_count=0
        )
        assert response.repo_id == "a1b2c3d4"
        assert response.total_findings == 0
    
    def test_negative_counts(self):
        """Test negative severity counts (should fail)"""
        with pytest.raises(ValidationError):
            CodeQLResponse(
                repo_id="a1b2c3d4",
                language="python",
                findings=[],
                total_findings=0,
                critical_count=-1,
                high_count=0,
                medium_count=0,
                low_count=0
            )


class TestIssue:
    """Tests for Issue model"""
    
    def test_valid_issue(self):
        """Test valid issue"""
        issue = Issue(
            title="SQL Injection",
            description="User input not sanitized",
            severity=SeverityEnum.CRITICAL,
            evidence=["src/db/queries.py:125-127"],
            fix_steps=["Use parameterized queries"],
            priority=1
        )
        assert issue.title == "SQL Injection"
        assert issue.priority == 1
    
    def test_invalid_priority_too_low(self):
        """Test priority below 1 (should fail)"""
        with pytest.raises(ValidationError):
            Issue(
                title="Test",
                description="Test",
                severity=SeverityEnum.LOW,
                evidence=[],
                fix_steps=[],
                priority=0
            )
    
    def test_invalid_priority_too_high(self):
        """Test priority above 10 (should fail)"""
        with pytest.raises(ValidationError):
            Issue(
                title="Test",
                description="Test",
                severity=SeverityEnum.LOW,
                evidence=[],
                fix_steps=[],
                priority=11
            )


class TestAnalysisResponse:
    """Tests for AnalysisResponse model"""
    
    def test_valid_analysis_response(self):
        """Test valid analysis response"""
        response = AnalysisResponse(
            repo_id="a1b2c3d4",
            interaction_id="interaction-xyz789",
            architecture_summary="FastAPI application",
            top_issues=[],
            recommendations=["Add input validation"],
            report_path="./workspace/output/report.md",
            raw_report_json={},
            created_at=datetime.utcnow()
        )
        assert response.repo_id == "a1b2c3d4"
        assert response.interaction_id == "interaction-xyz789"


class TestModelSerialization:
    """Tests for model serialization/deserialization"""
    
    def test_ingest_request_json_round_trip(self):
        """Test IngestRequest JSON serialization round-trip"""
        original = IngestRequest(
            source=RepoSource(url="https://github.com/user/repo"),
            include_patterns=["*.py"],
            exclude_patterns=[".git/*"]
        )
        
        # Serialize to JSON
        json_data = original.model_dump_json()
        
        # Deserialize back
        restored = IngestRequest.model_validate_json(json_data)
        
        assert restored.source.url == original.source.url
        assert restored.include_patterns == original.include_patterns
    
    def test_ingest_response_json_round_trip(self):
        """Test IngestResponse JSON serialization round-trip"""
        now = datetime.utcnow()
        original = IngestResponse(
            repo_id="a1b2c3d4",
            status="completed",
            file_count=100,
            total_lines=5000,
            languages={".py": 50},
            repo_md_path="path/to/repo.md",
            tree_json_path="path/to/tree.json",
            created_at=now
        )
        
        # Serialize to JSON
        json_data = original.model_dump_json()
        
        # Deserialize back
        restored = IngestResponse.model_validate_json(json_data)
        
        assert restored.repo_id == original.repo_id
        assert restored.file_count == original.file_count
