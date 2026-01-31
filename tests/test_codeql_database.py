import pytest
from pathlib import Path
from services.codeql_service import CodeQLService
from unittest.mock import patch, MagicMock
import subprocess
import shutil

def test_validate_repo_id_format():
    """Test repo_id validation"""
    service = CodeQLService()
    
    # Valid format (8 chars hex)
    # We must patch valid path existence to test format only, 
    # OR catch the FileNotFoundError which comes AFTER format validation
    
    # Invalid format - UPPERCASE
    with pytest.raises(ValueError, match="Invalid repo_id format"):
        service._validate_repo_id("ABC12345")
    
    # Invalid format - too short
    with pytest.raises(ValueError, match="Invalid repo_id format"):
        service._validate_repo_id("abc") 
        
    # Invalid format - too long
    with pytest.raises(ValueError, match="Invalid repo_id format"):
        service._validate_repo_id("abc123456")
        
    # Invalid format - non-hex
    with pytest.raises(ValueError, match="Invalid repo_id format"):
        service._validate_repo_id("zzzzzzzz")

def test_repo_not_ingested():
    """Test error when repo not ingested"""
    service = CodeQLService()
    
    with pytest.raises(FileNotFoundError, match="Run ingest endpoint first"):
        service._validate_repo_id("00000000")

def test_database_creation_timeout():
    """Test timeout handling"""
    service = CodeQLService()
    # Mock capability to avoid early exit
    service.codeql_available = True
    
    with patch('subprocess.run', side_effect=subprocess.TimeoutExpired('codeql', 600)):
        with pytest.raises(RuntimeError, match="timed out"):
            service._create_database(Path("/fake"), Path("/fake-db"), "python")

def test_database_creation_success():
    """Test successful database creation"""
    service = CodeQLService()
    service.codeql_available = True
    
    # Mock subprocess run
    mock_run = MagicMock()
    mock_run.returncode = 0
    
    # Mock file existence for marker file
    with patch('subprocess.run', return_value=mock_run), \
         patch('pathlib.Path.exists', side_effect=lambda: True), \
         patch('shutil.rmtree') as mock_rm:
        
        result = service._create_database(Path("/source"), Path("/db"), "python")
        
        assert result["success"] is True
        assert result["marker_file_exists"] is True

def test_database_creation_failure():
    """Test database creation failure via return code"""
    service = CodeQLService()
    service.codeql_available = True
    
    mock_run = MagicMock()
    mock_run.returncode = 1
    mock_run.stderr = "Error creating database at /db"
    
    with patch('subprocess.run', return_value=mock_run), \
         patch('shutil.rmtree'):
        
        with pytest.raises(RuntimeError, match="Database creation failed"):
            service._create_database(Path("/source"), Path("/db"), "python")

def test_database_creation_missing_marker():
    """Test database creation returning 0 but missing marker file"""
    service = CodeQLService()
    service.codeql_available = True
    
    mock_run = MagicMock()
    mock_run.returncode = 0
    
    # Mock exists to return False (marker missing)
    # We need strictly controlled side effects for path.exists
    # 1. db exists (initial check) -> False (simplifies test)
    # 2. marker exists -> False
    
    # We'll rely on the logic: if db_path exists, remove it.
    # To properly simulate "marker not found", we must let subprocess run,
    # then when checking marker_file.exists(), return False.
    
    with patch('subprocess.run', return_value=mock_run), \
         patch('pathlib.Path.exists', return_value=False), \
         patch('shutil.rmtree'):
            
        with pytest.raises(RuntimeError, match="Database creation appeared successful but marker"):
            service._create_database(Path("/source"), Path("/db"), "python")
