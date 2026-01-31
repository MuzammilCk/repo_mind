"""
Unit tests for CodeQLService
Tests with mocked CodeQL outputs and sample SARIF files
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
import subprocess
from pathlib import Path

from services.codeql_service import (
    CodeQLService, 
    SARIF_SEVERITY_MAP,
    DB_CREATE_TIMEOUT,
    ANALYZE_TIMEOUT
)
from models.requests import CodeQLScanRequest
from models.responses import CodeQLResponse, CodeQLFinding, SeverityEnum


class TestCodeQLService:
    """Tests for CodeQLService"""
    
    @pytest.fixture
    def sample_sarif_path(self):
        """Path to sample SARIF file"""
        return Path(__file__).parent / "fixtures" / "sample.sarif"
    
    @pytest.fixture
    def sample_repo_structure(self, tmp_path):
        """Create sample repository structure"""
        repo_dir = tmp_path / "workspace" / "ingest" / "test123" / "source"
        repo_dir.mkdir(parents=True)
        
        # Create some Python files
        (repo_dir / "main.py").write_text("import os\nprint('hello')\n")
        (repo_dir / "utils.py").write_text("def helper():\n    pass\n")
        
        return repo_dir
    
    def test_severity_mapping(self):
        """Test SARIF severity mapping is correct"""
        assert SARIF_SEVERITY_MAP["error"] == SeverityEnum.CRITICAL
        assert SARIF_SEVERITY_MAP["warning"] == SeverityEnum.HIGH
        assert SARIF_SEVERITY_MAP["note"] == SeverityEnum.MEDIUM
        assert SARIF_SEVERITY_MAP["none"] == SeverityEnum.LOW
    
    @patch('subprocess.run')
    def test_verify_codeql_success(self, mock_run):
        """Test successful CodeQL verification"""
        # Mock successful version check
        mock_run.return_value = Mock(returncode=0, stdout="CodeQL 2.11.0", stderr="")
        
        # Should not raise
        service = CodeQLService()
        assert service is not None
    
    @patch('subprocess.run')
    def test_verify_codeql_not_installed(self, mock_run):
        """Test CodeQL not installed"""
        # Mock FileNotFoundError
        mock_run.side_effect = FileNotFoundError("codeql not found")
        
        with pytest.raises(RuntimeError) as exc_info:
            CodeQLService()
        
        assert "not found" in str(exc_info.value).lower()
        assert "github.com" in str(exc_info.value)  # Should include installation URL
    
    @patch('subprocess.run')
    def test_verify_codeql_timeout(self, mock_run):
        """Test CodeQL version check timeout"""
        # Mock timeout
        mock_run.side_effect = subprocess.TimeoutExpired("codeql", 10)
        
        with pytest.raises(RuntimeError) as exc_info:
            CodeQLService()
        
        assert "timeout" in str(exc_info.value).lower()
    
    @patch('subprocess.run')
    def test_parse_sarif_basic(self, mock_run, sample_sarif_path):
        """Test parsing basic SARIF file"""
        # Mock version check
        mock_run.return_value = Mock(returncode=0, stdout="CodeQL 2.11.0", stderr="")
        
        service = CodeQLService()
        findings = service._parse_sarif(sample_sarif_path)
        
        assert len(findings) == 3  # Sample SARIF has 3 findings
        assert all(isinstance(f, CodeQLFinding) for f in findings)
    
    @patch('subprocess.run')
    def test_parse_sarif_severity_mapping(self, mock_run, sample_sarif_path):
        """Test SARIF severity levels are mapped correctly"""
        # Mock version check
        mock_run.return_value = Mock(returncode=0, stdout="CodeQL 2.11.0", stderr="")
        
        service = CodeQLService()
        findings = service._parse_sarif(sample_sarif_path)
        
        # Check severity mapping
        # error -> critical
        sql_injection = next(f for f in findings if "sql-injection" in f.rule_id)
        assert sql_injection.severity == SeverityEnum.CRITICAL
        
        # warning -> high
        weak_crypto = next(f for f in findings if "weak-crypto" in f.rule_id)
        assert weak_crypto.severity == SeverityEnum.HIGH
        
        # note -> medium
        unused_import = next(f for f in findings if "unused-import" in f.rule_id)
        assert unused_import.severity == SeverityEnum.MEDIUM
    
    @patch('subprocess.run')
    def test_parse_sarif_file_paths(self, mock_run, sample_sarif_path):
        """Test file paths are extracted correctly from SARIF"""
        # Mock version check
        mock_run.return_value = Mock(returncode=0, stdout="CodeQL 2.11.0", stderr="")
        
        service = CodeQLService()
        findings = service._parse_sarif(sample_sarif_path)
        
        file_paths = [f.file_path for f in findings]
        file_paths = [f.file_path for f in findings]
        assert "src/db.py" in file_paths
        assert "src/utils.py" in file_paths
        assert "src/auth.py" in file_paths
    
    @patch('subprocess.run')
    def test_parse_sarif_line_numbers(self, mock_run, sample_sarif_path):
        """Test line numbers are extracted correctly from SARIF"""
        # Mock version check
        mock_run.return_value = Mock(returncode=0, stdout="CodeQL 2.11.0", stderr="")
        
        service = CodeQLService()
        findings = service._parse_sarif(sample_sarif_path)
        
        # Check SQL injection finding
        sql_injection = next(f for f in findings if "sql-injection" in f.rule_id)
        assert sql_injection.start_line == 45
        assert sql_injection.end_line == 45
        
        # Check weak crypto finding
        weak_crypto = next(f for f in findings if "weak-crypto" in f.rule_id)
        assert weak_crypto.start_line == 102
        assert weak_crypto.end_line == 105
    
    @patch('subprocess.run')
    def test_parse_sarif_recommendations(self, mock_run, sample_sarif_path):
        """Test recommendations are extracted from SARIF"""
        # Mock version check
        mock_run.return_value = Mock(returncode=0, stdout="CodeQL 2.11.0", stderr="")
        
        service = CodeQLService()
        findings = service._parse_sarif(sample_sarif_path)
        
        # Check SQL injection recommendation
        sql_injection = next(f for f in findings if "sql-injection" in f.rule_id)
        assert sql_injection.recommendation is not None
        assert "parameterized" in sql_injection.recommendation.lower()
    
    @patch('subprocess.run')
    def test_parse_empty_sarif(self, mock_run, tmp_path):
        """Test parsing SARIF with no results"""
        # Mock version check
        mock_run.return_value = Mock(returncode=0, stdout="CodeQL 2.11.0", stderr="")
        
        # Create empty SARIF
        empty_sarif = tmp_path / "empty.sarif"
        empty_sarif.write_text(json.dumps({
            "version": "2.1.0",
            "runs": [{"results": []}]
        }))
        
        service = CodeQLService()
        findings = service._parse_sarif(empty_sarif)
        
        assert len(findings) == 0
    
    @patch('subprocess.run')
    def test_parse_malformed_sarif(self, mock_run, tmp_path):
        """Test parsing malformed SARIF JSON"""
        # Mock version check
        mock_run.return_value = Mock(returncode=0, stdout="CodeQL 2.11.0", stderr="")
        
        # Create malformed SARIF
        malformed_sarif = tmp_path / "malformed.sarif"
        malformed_sarif.write_text("{ invalid json")
        
        service = CodeQLService()
        
        with pytest.raises(RuntimeError) as exc_info:
            service._parse_sarif(malformed_sarif)
        
        assert "invalid" in str(exc_info.value).lower()
    
    @patch('subprocess.run')
    def test_count_severities(self, mock_run, sample_sarif_path):
        """Test severity counting"""
        # Mock version check
        mock_run.return_value = Mock(returncode=0, stdout="CodeQL 2.11.0", stderr="")
        
        service = CodeQLService()
        findings = service._parse_sarif(sample_sarif_path)
        counts = service._count_severities(findings)
        
        assert counts["critical"] == 1  # 1 error
        assert counts["high"] == 1  # 1 warning
        assert counts["medium"] == 1  # 1 note
        assert counts["low"] == 0  # 0 none
    
    @patch('subprocess.run')
    def test_analyze_repository_not_found(self, mock_run):
        """Test analyzing non-existent repository"""
        # Mock version check
        mock_run.return_value = Mock(returncode=0, stdout="CodeQL 2.11.0", stderr="")
        
        service = CodeQLService()
        request = CodeQLScanRequest(
            repo_id="nonexistent",
            language="python",
            query_suite="security-extended"
        )
        
        with pytest.raises(FileNotFoundError) as exc_info:
            service.analyze_repository(request)
        
        assert "not found" in str(exc_info.value).lower()
    
    @patch('subprocess.run')
    def test_create_database_timeout(self, mock_run, sample_repo_structure, monkeypatch):
        """Test database creation timeout"""
        # Mock version check first, then timeout on database create
        mock_run.side_effect = [
            Mock(returncode=0, stdout="CodeQL 2.11.0", stderr=""),  # version check
            subprocess.TimeoutExpired("codeql", DB_CREATE_TIMEOUT)  # database create
        ]
        
        service = CodeQLService()
        monkeypatch.setattr(
            service,
            'ingest_dir',
            sample_repo_structure.parent.parent
        )
        
        request = CodeQLScanRequest(
            repo_id="test123",
            language="python",
            query_suite="security-extended"
        )
        
        with pytest.raises(RuntimeError) as exc_info:
            service.analyze_repository(request)
        
        assert "timeout" in str(exc_info.value).lower()
    
    @patch('subprocess.run')
    def test_analyze_timeout(self, mock_run, sample_repo_structure, monkeypatch, tmp_path):
        """Test analysis timeout"""
        # Mock version check, successful DB create, then timeout on analyze
        mock_run.side_effect = [
            Mock(returncode=0, stdout="CodeQL 2.11.0", stderr=""),  # version check
            Mock(returncode=0, stdout="DB created", stderr=""),  # database create
            subprocess.TimeoutExpired("codeql", ANALYZE_TIMEOUT)  # analyze
        ]
        
        service = CodeQLService()
        monkeypatch.setattr(
            service,
            'ingest_dir',
            sample_repo_structure.parent.parent
        )
        monkeypatch.setattr(
            service,
            'db_dir',
            tmp_path / "dbs"
        )
        
        request = CodeQLScanRequest(
            repo_id="test123",
            language="python",
            query_suite="security-extended"
        )
        
        with pytest.raises(RuntimeError) as exc_info:
            service.analyze_repository(request)
        
        assert "timeout" in str(exc_info.value).lower()
    
    @patch('subprocess.run')
    def test_no_shell_true(self, mock_run):
        """Test that subprocess calls never use shell=True"""
        # Mock version check
        mock_run.return_value = Mock(returncode=0, stdout="CodeQL 2.11.0", stderr="")
        
        service = CodeQLService()
        
        # Check all subprocess calls
        for call in mock_run.call_args_list:
            kwargs = call[1]
            assert kwargs.get("shell") is False or "shell" not in kwargs
    
    @patch('subprocess.run')
    def test_map_severity_unknown(self, mock_run):
        """Test mapping unknown SARIF level defaults to medium"""
        # Mock version check
        mock_run.return_value = Mock(returncode=0, stdout="CodeQL 2.11.0", stderr="")
        
        service = CodeQLService()
        severity = service._map_severity("unknown_level")
        
        assert severity == SeverityEnum.MEDIUM


class TestCodeQLServiceEdgeCases:
    """Edge case tests for CodeQLService"""
    
    @patch('subprocess.run')
    def test_sarif_without_locations(self, mock_run, tmp_path):
        """Test SARIF finding without location is skipped"""
        # Mock version check
        mock_run.return_value = Mock(returncode=0, stdout="CodeQL 2.11.0", stderr="")
        
        # Create SARIF with finding but no location
        sarif_data = {
            "version": "2.1.0",
            "runs": [{
                "results": [{
                    "ruleId": "test-rule",
                    "level": "error",
                    "message": {"text": "Test message"},
                    "locations": []  # Empty locations
                }]
            }]
        }
        
        sarif_path = tmp_path / "no_location.sarif"
        sarif_path.write_text(json.dumps(sarif_data))
        
        service = CodeQLService()
        findings = service._parse_sarif(sarif_path)
        
        # Should skip finding without location
        assert len(findings) == 0
    
    @patch('subprocess.run')
    def test_sarif_missing_fields(self, mock_run, tmp_path):
        """Test SARIF with missing optional fields"""
        # Mock version check
        mock_run.return_value = Mock(returncode=0, stdout="CodeQL 2.11.0", stderr="")
        
        # Create minimal SARIF
        sarif_data = {
            "version": "2.1.0",
            "runs": [{
                "results": [{
                    "locations": [{
                        "physicalLocation": {
                            "artifactLocation": {"uri": "test.py"},
                            "region": {"startLine": 10}
                        }
                    }]
                }]
            }]
        }
        
        sarif_path = tmp_path / "minimal.sarif"
        sarif_path.write_text(json.dumps(sarif_data))
        
        service = CodeQLService()
        findings = service._parse_sarif(sarif_path)
        
        # Should handle missing fields gracefully
        assert len(findings) == 1
        assert findings[0].rule_id == "unknown"
        assert findings[0].message == "No description available"
