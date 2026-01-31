import pytest
import json
from pathlib import Path
from services.codeql_service import CodeQLService
from unittest.mock import patch, MagicMock
import subprocess

def test_query_suite_validation():
    """Test query suite whitelist"""
    service = CodeQLService()
    
    # Valid suite
    assert service._validate_query_suite("security-extended") == "security-extended"
    
    # Invalid suite
    with pytest.raises(ValueError, match="Invalid query suite"):
        service._validate_query_suite("malicious-injection")

def test_run_queries_success(tmp_path):
    """Test successful query execution"""
    service = CodeQLService()
    service.codeql_available = True
    
    # Mock subprocess run
    mock_run = MagicMock()
    mock_run.returncode = 0
    
    # Create valid SARIF file
    sarif_file = tmp_path / "results.sarif"
    sarif_content = {
        "runs": [
            {
                "results": [{}, {}]  # 2 results
            }
        ]
    }
    sarif_file.write_text(json.dumps(sarif_content))
    
    with patch('subprocess.run', return_value=mock_run):
        result = service._run_queries(
            Path("/fake-db"),
            "python",
            "security-extended",
            sarif_file
        )
        
        assert result["success"] is True
        assert result["total_results"] == 2

def test_run_queries_failure():
    """Test query execution failure"""
    service = CodeQLService()
    service.codeql_available = True
    
    mock_run = MagicMock()
    mock_run.returncode = 1
    mock_run.stderr = "Error running queries"
    
    with patch('subprocess.run', return_value=mock_run):
        with pytest.raises(RuntimeError, match="Query execution failed"):
            service._run_queries(
                Path("/fake-db"),
                "python",
                "security-extended",
                Path("/fake/out.sarif")
            )

def test_run_queries_unknown_suite():
    """Test unknown query suite for language"""
    service = CodeQLService()
    service.codeql_available = True
    
    mock_run = MagicMock()
    mock_run.returncode = 1
    mock_run.stderr = "Could not resolve query suite python-unknown.qls"
    
    with patch('subprocess.run', return_value=mock_run):
        with pytest.raises(ValueError, match="Verify language/suite combination"):
            service._run_queries(
                Path("/fake-db"),
                "python",
                "security-extended",
                Path("/fake/out.sarif")
            )

def test_sarif_validation_failure(tmp_path):
    """Test SARIF file validation - invalid JSON"""
    service = CodeQLService()
    service.codeql_available = True
    
    mock_run = MagicMock()
    mock_run.returncode = 0
    
    # Create invalid JSON file
    invalid_sarif = tmp_path / "invalid.sarif"
    invalid_sarif.write_text("not json")
    
    with patch('subprocess.run', return_value=mock_run):
        with pytest.raises(RuntimeError, match="SARIF file is not valid JSON"):
            service._run_queries(
                Path("/fake-db"),
                "python", 
                "security-extended",
                invalid_sarif
            )

def test_sarif_file_missing(tmp_path):
    """Test SARIF file missing after execution"""
    service = CodeQLService()
    service.codeql_available = True
    
    mock_run = MagicMock()
    mock_run.returncode = 0
    
    missing_sarif = tmp_path / "missing.sarif"
    if missing_sarif.exists():
        missing_sarif.unlink()
        
    with patch('subprocess.run', return_value=mock_run):
        with pytest.raises(RuntimeError, match="SARIF file not created"):
            service._run_queries(
                Path("/fake-db"),
                "python",
                "security-extended",
                missing_sarif
            )

def test_query_timeout():
    """Test timeout handling"""
    service = CodeQLService()
    service.codeql_available = True
    
    with patch('subprocess.run', side_effect=subprocess.TimeoutExpired('cmd', 600)):
        with pytest.raises(RuntimeError, match="timed out"):
            service._run_queries(
                Path("/fake-db"),
                "python",
                "security-extended",
                Path("/fake/out.sarif")
            )
