import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from main import app
from models.responses import CodeQLResponse, CodeQLFinding, SeverityEnum

client = TestClient(app)

@pytest.fixture
def mock_service():
    with patch("api.analysis.codeql_service") as mock:
        yield mock

def test_codeql_endpoint_success(mock_service):
    """Test successful CodeQL scan request"""
    # Setup mock response
    mock_response = CodeQLResponse(
        repo_id="repo123",
        language="python",
        findings=[
            CodeQLFinding(
                rule_id="test",
                severity=SeverityEnum.CRITICAL,
                message="msg",
                file_path="f.py",
                start_line=1,
                end_line=1
            )
        ],
        total_findings=1,
        critical_count=1,
        high_count=0,
        medium_count=0,
        low_count=0
    )
    mock_service.analyze_repository.return_value = mock_response
    mock_service.codeql_available = True
    
    response = client.post(
        "/api/analysis/codeql",
        json={
            "repo_id": "repo123",
            "language": "python",
            "query_suite": "security-extended"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["repo_id"] == "repo123"
    assert data["total_findings"] == 1
    mock_service.analyze_repository.assert_called_once()

def test_codeql_unavailable(mock_service):
    """Test 503 when CodeQL is not available"""
    mock_service.codeql_available = False
    
    response = client.post(
        "/api/analysis/codeql",
        json={
            "repo_id": "repo123",
            "language": "python",
            "query_suite": "security-extended"
        }
    )
    
    assert response.status_code == 503
    assert "CodeQL CLI not available" in response.json()["detail"]["error"]

def test_invalid_query_suite(mock_service):
    """Test 422 for invalid query suite"""
    mock_service.codeql_available = True
    mock_service._validate_query_suite.side_effect = ValueError("Invalid suite")
    mock_service.ALLOWED_QUERY_SUITES = {"security-extended"}
    
    response = client.post(
        "/api/analysis/codeql",
        json={
            "repo_id": "repo123",
            "language": "python",
            "query_suite": "invalid-suite"
        }
    )
    
    assert response.status_code == 422
    assert "Invalid query suite" in response.json()["detail"]["error"]

def test_repository_not_found(mock_service):
    """Test 404 when repository is not found"""
    mock_service.codeql_available = True
    mock_service.analyze_repository.side_effect = FileNotFoundError("Repo not found")
    
    response = client.post(
        "/api/analysis/codeql",
        json={
            "repo_id": "missing_repo",
            "language": "python",
            "query_suite": "security-extended"
        }
    )
    
    assert response.status_code == 404
    assert "Repository not found" in response.json()["detail"]["error"]

def test_analysis_timeout(mock_service):
    """Test 504 when analysis times out"""
    mock_service.codeql_available = True
    mock_service.analyze_repository.side_effect = TimeoutError("Timed out")
    
    response = client.post(
        "/api/analysis/codeql",
        json={
            "repo_id": "repo123",
            "language": "python",
            "query_suite": "security-extended"
        }
    )
    
    assert response.status_code == 504
    assert "Operation timeout" in response.json()["detail"]["error"]
