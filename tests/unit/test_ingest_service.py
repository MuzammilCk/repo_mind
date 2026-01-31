"""
Unit tests for IngestService
Tests repository processing with mocked dependencies
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from services.ingest_service import IngestService
from models.requests import IngestRequest, RepoSource


class TestIngestService:
    """Test suite for IngestService"""
    
    def test_service_initialization(self):
        """Test service initializes correctly"""
        service = IngestService()
        
        assert service.ingest_dir is not None
        assert service.ingest_dir.exists()
    
    @patch('git.Repo.clone_from')
    def test_clone_repository_success(self, mock_clone):
        """Test successful repository cloning"""
        # Mock successful git clone
        mock_repo = Mock()
        mock_clone.return_value = mock_repo
        
        service = IngestService()
        target_dir = service.ingest_dir / "test_clone"
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Create mock .git directory
        (target_dir / ".git").mkdir(exist_ok=True)
        
        result = service._clone_repository("https://github.com/test/repo", target_dir)
        
        assert result == target_dir
        mock_clone.assert_called_once()
    
    @patch('git.Repo.clone_from')
    def test_clone_repository_failure(self, mock_clone):
        """Test repository cloning failure"""
        import git
        # Mock failed git clone
        mock_clone.side_effect = git.GitCommandError("clone", "Git clone failed")
        
        service = IngestService()
        
        with pytest.raises(RuntimeError, match="Git clone failed"):
            service._clone_repository("invalid_url", Path("/tmp/test"))
    
    def test_read_file_safe_utf8(self, temp_workspace):
        """Test reading UTF-8 file"""
        # Create test file
        test_file = temp_workspace / "test.txt"
        test_file.write_text("Hello, World!", encoding='utf-8')
        
        service = IngestService()
        content, was_truncated = service._read_file_safe(test_file)
        
        assert content == "Hello, World!"
        assert was_truncated is False
    
    def test_read_file_safe_large_file(self, temp_workspace):
        """Test reading large file gets truncated"""
        from services.ingest_service import MAX_BYTES_PER_FILE
        
        # Create large file
        test_file = temp_workspace / "large.txt"
        test_file.write_text("a" * (MAX_BYTES_PER_FILE + 1000), encoding='utf-8')
        
        service = IngestService()
        content, was_truncated = service._read_file_safe(test_file)
        
        assert was_truncated is True
        assert len(content.encode('utf-8')) <= MAX_BYTES_PER_FILE
    
    def test_is_text_content(self):
        """Test text content detection"""
        service = IngestService()
        
        # Text content
        assert service._is_text_content("Hello, World!") is True
        assert service._is_text_content("def foo():\n    pass") is True
        
        # Binary content (with null bytes)
        assert service._is_text_content("Hello\x00World") is False
    
    def test_calculate_stats(self, temp_workspace):
        """Test repository statistics calculation"""
        # Create test repository structure
        repo_dir = temp_workspace / "test-repo"
        repo_dir.mkdir()
        (repo_dir / "file1.py").write_text("print('hello')\n")
        (repo_dir / "file2.py").write_text("print('world')\n")
        (repo_dir / "README.md").write_text("# Test\n")
        
        service = IngestService()
        stats = service._calculate_stats(repo_dir, [], [])
        
        assert stats["file_count"] == 3
        assert stats["total_lines"] >= 3
        assert ".py" in stats["languages"]
        assert ".md" in stats["languages"]
    
    def test_calculate_stats_with_exclusions(self, temp_workspace):
        """Test stats calculation with exclusion patterns"""
        repo_dir = temp_workspace / "test-repo"
        repo_dir.mkdir()
        (repo_dir / "main.py").write_text("code")
        (repo_dir / "test.py").write_text("test")
        (repo_dir / "README.md").write_text("docs")
        
        service = IngestService()
        stats = service._calculate_stats(
            repo_dir,
            include_patterns=[],
            exclude_patterns=["*.md"]
        )
        
        # Should exclude README.md
        assert stats["file_count"] == 2
    
    def test_generate_tree_json(self, temp_workspace):
        """Test tree.json generation"""
        import json
        
        # Create test structure
        repo_dir = temp_workspace / "test-repo"
        repo_dir.mkdir()
        (repo_dir / "file1.py").write_text("code")
        (repo_dir / "subdir").mkdir()
        (repo_dir / "subdir" / "file2.py").write_text("code")
        
        service = IngestService()
        output_path = temp_workspace / "tree.json"
        
        result_path = service._generate_tree_json(repo_dir, output_path)
        
        assert result_path.exists()
        
        # Verify JSON structure
        with open(result_path) as f:
            tree = json.load(f)
        
        assert tree["type"] == "directory"
        assert "children" in tree
    
    def test_generate_signature(self, temp_workspace):
        """Test signature generation"""
        repo_dir = temp_workspace / "test-repo"
        repo_dir.mkdir()
        
        service = IngestService()
        stats = {"file_count": 10, "total_lines": 100}
        
        signature = service._generate_signature(repo_dir, stats)
        
        # Should be SHA256 hex digest (64 characters)
        assert len(signature) == 64
        assert all(c in '0123456789abcdef' for c in signature)
