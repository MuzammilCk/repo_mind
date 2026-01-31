"""
Pytest configuration and shared fixtures
"""

import pytest
from pathlib import Path
import tempfile
import shutil
from typing import Generator


@pytest.fixture
def temp_workspace() -> Generator[Path, None, None]:
    """
    Create temporary workspace directory for tests
    
    Automatically cleaned up after test completes
    """
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def mock_settings():
    """
    Mock settings for testing
    
    Temporarily sets DEBUG=True and restores original value
    """
    from config import settings
    original_debug = settings.DEBUG
    original_log_level = settings.LOG_LEVEL
    
    settings.DEBUG = True
    settings.LOG_LEVEL = "DEBUG"
    
    yield settings
    
    settings.DEBUG = original_debug
    settings.LOG_LEVEL = original_log_level


@pytest.fixture
def reset_metrics():
    """
    Reset metrics collector before each test
    
    Ensures clean state for metrics tests
    """
    from utils.metrics import metrics_collector
    metrics_collector.reset()
    yield metrics_collector
    metrics_collector.reset()


@pytest.fixture
def sample_repo_metadata():
    """Sample repository metadata for testing"""
    return {
        "repo_id": "test_repo_123",
        "name": "test-repository",
        "url": "https://github.com/test/repo",
        "language": "python",
        "file_count": 42,
        "total_size_bytes": 1024000
    }


@pytest.fixture
def sample_orchestrator_request():
    """Sample orchestrator request for testing"""
    from models.requests import OrchestratorRequest
    return OrchestratorRequest(
        repo_id="test123",
        analysis_type="security",
        custom_instructions="Focus on authentication"
    )
