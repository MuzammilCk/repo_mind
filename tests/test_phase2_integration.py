import pytest
from fastapi.testclient import TestClient
from main import app
from pathlib import Path
import json
import os

client = TestClient(app)

def test_health_includes_codeql():
    """Test health endpoint includes CodeQL status"""
    response = client.get("/health")
    assert response.status_code == 200
    
    data = response.json()
    assert "codeql_available" in data
    assert "codeql_version" in data
    assert isinstance(data["codeql_available"], bool)

def test_phase1_still_works():
    """Test Phase 1 ingest still functional"""
    # Use the python_repo fixture we created
    ingest_request = {
        "source": {
            "local_path": str(Path(__file__).parent / "fixtures" / "python_repo")
        }
    }
    
    response = client.post("/api/ingest", json=ingest_request)
    assert response.status_code == 200
    
    data = response.json()
    assert "repo_id" in data
    assert data["status"] == "completed"

@pytest.mark.skipif(
    os.environ.get("CODEQL_PATH") is None and not Path("codeql").exists() and not Path("C:/codeql/codeql.exe").exists(),
    reason="CodeQL not installed"
)
def test_full_pipeline_ingest_to_codeql():
    """Test complete pipeline: ingest → CodeQL scan"""
    
    # Step 1: Ingest a test repository
    ingest_request = {
        "source": {
            "local_path": str(Path(__file__).parent / "fixtures" / "python_repo")
        }
    }
    
    ingest_response = client.post("/api/ingest", json=ingest_request)
    assert ingest_response.status_code == 200
    
    repo_id = ingest_response.json()["repo_id"]
    
    # Step 2: Run CodeQL scan on the ingested repo
    codeql_request = {
        "repo_id": repo_id,
        "language": "python",
        "query_suite": "security-extended"
    }
    
    codeql_response = client.post("/api/analysis/codeql", json=codeql_request)
    
    # If CodeQL is missing, we might get 503, but the skipif should handle it.
    if codeql_response.status_code == 503:
         pytest.skip("CodeQL not available in service")
         
    assert codeql_response.status_code == 200
    
    data = codeql_response.json()
    assert data["repo_id"] == repo_id
    assert "findings" in data
    assert "total_findings" in data
    assert isinstance(data["findings"], list)

def test_invalid_repo_id_returns_404():
    """Test 404 for non-existent repo_id"""
    # Force CodeQL availability to True so we can hit the repo check
    from unittest.mock import patch
    
    # Patch the INSTANCE in api.analysis
    with patch('api.analysis.codeql_service.codeql_available', True):
        codeql_request = {
            "repo_id": "00000000",  # Doesn't exist
            "language": "python",
            "query_suite": "security-extended"
        }
        
        response = client.post("/api/analysis/codeql", json=codeql_request)
        assert response.status_code == 404
        
        data = response.json()
        assert "Repository not found" in data["detail"]["error"]

def test_invalid_query_suite_returns_422():
    """Test 422 for invalid query suite"""
    # Force CodeQL availability to True
    from unittest.mock import patch
    
    with patch('api.analysis.codeql_service.codeql_available', True):
        codeql_request = {
            "repo_id": "validid1", 
            "language": "python",
            "query_suite": "malicious-injection"
        }
        
        response = client.post("/api/analysis/codeql", json=codeql_request)
        
        assert response.status_code == 422
        data = response.json()
        assert "Invalid query suite" in data["detail"]["error"]

def test_codeql_unavailable_returns_503():
    """Test 503 when CodeQL not installed"""
    from unittest.mock import patch
    
    with patch('api.analysis.codeql_service.codeql_available', False):
        codeql_request = {
            "repo_id": "test1234",
            "language": "python",
            "query_suite": "security-extended"
        }
        
        response = client.post("/api/analysis/codeql", json=codeql_request)
        assert response.status_code == 503
        
        data = response.json()
        assert "not available" in data["detail"]["error"]
