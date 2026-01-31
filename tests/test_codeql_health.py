import pytest
from services.codeql_service import CodeQLService
from unittest.mock import patch, MagicMock
import subprocess

def test_codeql_available_when_installed():
    """Test CodeQL detection when binary exists"""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="CodeQL command-line toolchain release 2.15.0",
            stderr=""
        )
        
        service = CodeQLService()
        assert service.codeql_available == True
        assert "2.15.0" in service.codeql_version

def test_codeql_unavailable_when_missing():
    """Test CodeQL detection when binary missing"""
    with patch('subprocess.run', side_effect=FileNotFoundError()):
        service = CodeQLService()
        assert service.codeql_available == False
        assert service.codeql_version is None

def test_codeql_timeout_handled():
    """Test timeout handling for version check"""
    with patch('subprocess.run', side_effect=subprocess.TimeoutExpired('codeql', 10)):
        service = CodeQLService()
        assert service.codeql_available == False
