"""
Unit tests for IngestService
Tests cloning, repo2txt fallback, encoding handling, size limits, and binary file detection
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

from services.ingest_service import IngestService, MAX_BYTES_PER_FILE
from models.requests import IngestRequest, RepoSource


class TestIngestService:
    """Tests for IngestService"""
    
    @pytest.fixture
    def ingest_service(self):
        """Create IngestService instance"""
        return IngestService()
    
    @pytest.fixture
    def sample_repo(self, tmp_path):
        """Create a sample repository for testing"""
        repo_dir = tmp_path / "sample_repo"
        repo_dir.mkdir()
        
        # Create some Python files
        (repo_dir / "main.py").write_text(
            "def main():\n    print('Hello, World!')\n\nif __name__ == '__main__':\n    main()\n"
        )
        
        (repo_dir / "utils.py").write_text(
            "def add(a, b):\n    return a + b\n\ndef subtract(a, b):\n    return a - b\n"
        )
        
        # Create a subdirectory
        src_dir = repo_dir / "src"
        src_dir.mkdir()
        
        (src_dir / "helper.py").write_text(
            "class Helper:\n    def __init__(self):\n        pass\n"
        )
        
        # Create a README
        (repo_dir / "README.md").write_text(
            "# Sample Repository\n\nThis is a test repository.\n"
        )
        
        # Create a file to be excluded
        (repo_dir / "test.pyc").write_text("binary content")
        
        return repo_dir
    
    @pytest.fixture
    def binary_repo(self, tmp_path):
        """Create a repository with binary files"""
        repo_dir = tmp_path / "binary_repo"
        repo_dir.mkdir()
        
        # Create a text file
        (repo_dir / "text.txt").write_text("This is text content\n")
        
        # Create a binary file
        binary_file = repo_dir / "binary.bin"
        binary_file.write_bytes(b'\x00\x01\x02\x03\x04\x05\xFF\xFE')
        
        return repo_dir
    
    @pytest.fixture
    def large_file_repo(self, tmp_path):
        """Create a repository with a large file"""
        repo_dir = tmp_path / "large_repo"
        repo_dir.mkdir()
        
        # Create a file larger than MAX_BYTES_PER_FILE
        large_content = "x" * (MAX_BYTES_PER_FILE + 1000)
        (repo_dir / "large.txt").write_text(large_content)
        
        # Create a normal file
        (repo_dir / "normal.txt").write_text("Normal content\n")
        
        return repo_dir
    
    def test_ingest_local_repository(self, ingest_service, sample_repo):
        """Test ingesting a local repository"""
        request = IngestRequest(
            source=RepoSource(local_path=str(sample_repo)),
            include_patterns=["*.py", "*.md"],
            exclude_patterns=["*.pyc"]
        )
        
        response = ingest_service.ingest_repository(request)
        
        assert response.status == "completed"
        assert response.file_count > 0
        assert response.total_lines > 0
        assert ".py" in response.languages
        assert Path(response.repo_md_path).exists()
        assert Path(response.tree_json_path).exists()
    
    def test_repo_md_generation(self, ingest_service, sample_repo):
        """Test repo.md generation"""
        request = IngestRequest(
            source=RepoSource(local_path=str(sample_repo)),
            include_patterns=["*.py"],
            exclude_patterns=["*.pyc"]
        )
        
        response = ingest_service.ingest_repository(request)
        
        # Read generated repo.md
        repo_md_content = Path(response.repo_md_path).read_text()
        
        assert "# Repository:" in repo_md_content
        assert "Generated:" in repo_md_content
        assert "main.py" in repo_md_content
        assert "def main():" in repo_md_content
    
    def test_tree_json_generation(self, ingest_service, sample_repo):
        """Test tree.json generation"""
        import json
        
        request = IngestRequest(
            source=RepoSource(local_path=str(sample_repo))
        )
        
        response = ingest_service.ingest_repository(request)
        
        # Read and parse tree.json
        with open(response.tree_json_path, 'r') as f:
            tree = json.load(f)
        
        assert tree["type"] == "directory"
        assert tree["name"] == "sample_repo"
        assert "children" in tree
        assert len(tree["children"]) > 0
    
    def test_binary_file_handling(self, ingest_service, binary_repo):
        """Test that binary files are skipped"""
        request = IngestRequest(
            source=RepoSource(local_path=str(binary_repo))
        )
        
        response = ingest_service.ingest_repository(request)
        
        # Read repo.md
        repo_md_content = Path(response.repo_md_path).read_text()
        
        # Text file should be included
        assert "text.txt" in repo_md_content
        assert "This is text content" in repo_md_content
        
        # Binary file should be marked as skipped
        assert "binary.bin" in repo_md_content
        assert "Binary file - skipped" in repo_md_content
    
    def test_large_file_truncation(self, ingest_service, large_file_repo):
        """Test that large files are truncated"""
        request = IngestRequest(
            source=RepoSource(local_path=str(large_file_repo))
        )
        
        response = ingest_service.ingest_repository(request)
        
        # Read repo.md
        repo_md_content = Path(response.repo_md_path).read_text()
        
        # Should mention truncation
        assert "truncated" in repo_md_content.lower()
        assert "large.txt" in repo_md_content
    
    def test_include_patterns(self, ingest_service, sample_repo):
        """Test include patterns filtering"""
        request = IngestRequest(
            source=RepoSource(local_path=str(sample_repo)),
            include_patterns=["*.md"],  # Only markdown files
            exclude_patterns=[]
        )
        
        response = ingest_service.ingest_repository(request)
        
        # Should only include .md files
        assert ".md" in response.languages
        assert ".py" not in response.languages
    
    def test_exclude_patterns(self, ingest_service, sample_repo):
        """Test exclude patterns filtering"""
        request = IngestRequest(
            source=RepoSource(local_path=str(sample_repo)),
            include_patterns=["*.py", "*.md"],
            exclude_patterns=["src/*"]  # Exclude src directory
        )
        
        response = ingest_service.ingest_repository(request)
        
        # Read repo.md
        repo_md_content = Path(response.repo_md_path).read_text()
        
        # Should not include files from src/
        assert "helper.py" not in repo_md_content
        
        # Should include root level files
        assert "main.py" in repo_md_content
    
    def test_stats_calculation(self, ingest_service, sample_repo):
        """Test statistics calculation"""
        request = IngestRequest(
            source=RepoSource(local_path=str(sample_repo)),
            include_patterns=["*.py", "*.md"],
            exclude_patterns=["*.pyc"]
        )
        
        response = ingest_service.ingest_repository(request)
        
        assert response.file_count > 0
        assert response.total_lines > 0
        assert isinstance(response.languages, dict)
        assert len(response.languages) > 0
    
    def test_get_repo_content(self, ingest_service, sample_repo):
        """Test retrieving repo content"""
        request = IngestRequest(
            source=RepoSource(local_path=str(sample_repo))
        )
        
        response = ingest_service.ingest_repository(request)
        
        # Get content
        content = ingest_service.get_repo_content(response.repo_id)
        
        assert len(content) > 0
        assert "# Repository:" in content
    
    def test_get_repo_content_not_found(self, ingest_service):
        """Test retrieving non-existent repo"""
        with pytest.raises(FileNotFoundError):
            ingest_service.get_repo_content("nonexistent")
    
    def test_invalid_local_path(self, ingest_service):
        """Test with invalid local path"""
        request = IngestRequest(
            source=RepoSource(local_path="/nonexistent/path")
        )
        
        with pytest.raises(ValueError):
            ingest_service.ingest_repository(request)
    
    def test_no_source_provided(self, ingest_service):
        """Test with neither URL nor local path"""
        request = IngestRequest(
            source=RepoSource()
        )
        
        with pytest.raises(ValueError):
            ingest_service.ingest_repository(request)
    
    def test_encoding_fallback(self, ingest_service, tmp_path):
        """Test encoding fallback from UTF-8 to Latin-1"""
        repo_dir = tmp_path / "encoding_repo"
        repo_dir.mkdir()
        
        # Create a file with Latin-1 encoding
        latin1_file = repo_dir / "latin1.txt"
        latin1_file.write_bytes("Café résumé".encode('latin-1'))
        
        request = IngestRequest(
            source=RepoSource(local_path=str(repo_dir))
        )
        
        response = ingest_service.ingest_repository(request)
        
        # Should successfully ingest with fallback
        assert response.status == "completed"
        assert response.file_count == 1
    
    def test_repo_id_generation(self, ingest_service, sample_repo):
        """Test that repo IDs are unique"""
        request = IngestRequest(
            source=RepoSource(local_path=str(sample_repo))
        )
        
        response1 = ingest_service.ingest_repository(request)
        response2 = ingest_service.ingest_repository(request)
        
        # IDs should be different
        assert response1.repo_id != response2.repo_id
    
    def test_created_at_timestamp(self, ingest_service, sample_repo):
        """Test that created_at timestamp is set"""
        request = IngestRequest(
            source=RepoSource(local_path=str(sample_repo))
        )
        
        response = ingest_service.ingest_repository(request)
        
        assert isinstance(response.created_at, datetime)
        assert response.created_at <= datetime.utcnow()


class TestIngestServiceEdgeCases:
    """Edge case tests for IngestService"""
    
    @pytest.fixture
    def ingest_service(self):
        return IngestService()
    
    def test_empty_repository(self, ingest_service, tmp_path):
        """Test ingesting an empty repository"""
        empty_repo = tmp_path / "empty_repo"
        empty_repo.mkdir()
        
        request = IngestRequest(
            source=RepoSource(local_path=str(empty_repo))
        )
        
        response = ingest_service.ingest_repository(request)
        
        assert response.status == "completed"
        assert response.file_count == 0
        assert response.total_lines == 0
    
    def test_hidden_files_excluded(self, ingest_service, tmp_path):
        """Test that hidden files are excluded from tree.json"""
        import json
        
        repo_dir = tmp_path / "hidden_repo"
        repo_dir.mkdir()
        
        # Create regular file
        (repo_dir / "visible.txt").write_text("visible")
        
        # Create hidden file
        (repo_dir / ".hidden").write_text("hidden")
        
        request = IngestRequest(
            source=RepoSource(local_path=str(repo_dir))
        )
        
        response = ingest_service.ingest_repository(request)
        
        # Check tree.json
        with open(response.tree_json_path, 'r') as f:
            tree = json.load(f)
        
        # Hidden files should not be in tree
        child_names = [child["name"] for child in tree["children"]]
        assert "visible.txt" in child_names
        assert ".hidden" not in child_names
