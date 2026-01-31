"""
Unit tests for SearchService
Tests with mocked SeaGOAT outputs for deterministic validation
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import subprocess
from pathlib import Path

from services.search_service import SearchService, MAX_RESULTS, MAX_SNIPPET_LENGTH
from models.requests import SemanticSearchRequest
from models.responses import SemanticSearchResponse, SearchResult


# Sample mocked SeaGOAT outputs in grep-line format
MOCK_SEAGOAT_OUTPUT = """src/auth/login.py:42:def authenticate_user(username, password):
src/auth/login.py:43:    if not username or not password:
src/auth/login.py:44:        return False
src/utils/helpers.py:10:def validate_credentials(user, pwd):
src/utils/helpers.py:11:    return user and pwd
"""

MOCK_EMPTY_OUTPUT = ""

MOCK_LARGE_OUTPUT = "\n".join([
    f"file{i}.py:{i}:def function_{i}():" for i in range(100)
])


class TestSearchService:
    """Tests for SearchService"""
    
    @pytest.fixture
    def search_service(self):
        """Create SearchService instance"""
        return SearchService()
    
    @pytest.fixture
    def sample_repo_structure(self, tmp_path):
        """Create sample repository structure"""
        repo_dir = tmp_path / "workspace" / "ingest" / "test123" / "source"
        repo_dir.mkdir(parents=True)
        
        # Create some files
        (repo_dir / "main.py").write_text("def main():\n    pass\n")
        (repo_dir / "utils.py").write_text("def helper():\n    pass\n")
        
        return repo_dir
    
    def test_parse_seagoat_output_basic(self, search_service):
        """Test parsing basic SeaGOAT output"""
        results = search_service._parse_seagoat_output(MOCK_SEAGOAT_OUTPUT, 10)
        
        assert len(results) == 2  # 2 unique files
        assert all(isinstance(r, SearchResult) for r in results)
        
        # Check first result
        assert results[0].file_path == "src/auth/login.py"
        assert results[0].line_number == 42
        assert "authenticate_user" in results[0].code_snippet
        assert 0.0 <= results[0].relevance_score <= 1.0
    
    def test_parse_seagoat_output_deterministic(self, search_service):
        """Test that parsing is deterministic - same input produces same output"""
        results1 = search_service._parse_seagoat_output(MOCK_SEAGOAT_OUTPUT, 10)
        results2 = search_service._parse_seagoat_output(MOCK_SEAGOAT_OUTPUT, 10)
        
        assert len(results1) == len(results2)
        
        for r1, r2 in zip(results1, results2):
            assert r1.file_path == r2.file_path
            assert r1.line_number == r2.line_number
            assert r1.code_snippet == r2.code_snippet
            assert r1.relevance_score == r2.relevance_score
    
    def test_parse_empty_output(self, search_service):
        """Test parsing empty output"""
        results = search_service._parse_seagoat_output(MOCK_EMPTY_OUTPUT, 10)
        assert len(results) == 0
    
    def test_result_capping(self, search_service):
        """Test that results are capped at limit"""
        # Request only 5 results from large output
        results = search_service._parse_seagoat_output(MOCK_LARGE_OUTPUT, 5)
        assert len(results) <= 5
    
    def test_max_results_cap(self, search_service):
        """Test that results never exceed MAX_RESULTS"""
        # Request 1000 results but should be capped at MAX_RESULTS
        results = search_service._parse_seagoat_output(MOCK_LARGE_OUTPUT, 1000)
        assert len(results) <= MAX_RESULTS
    
    def test_snippet_truncation(self, search_service):
        """Test that long snippets are truncated"""
        # Create output with very long line
        long_line = "x" * (MAX_SNIPPET_LENGTH + 100)
        long_output = f"test.py:1:{long_line}"
        
        results = search_service._parse_seagoat_output(long_output, 10)
        
        assert len(results) == 1
        assert len(results[0].code_snippet) <= MAX_SNIPPET_LENGTH + 20  # Allow for truncation marker
        assert "[truncated]" in results[0].code_snippet
    
    def test_json_adapter_output(self, search_service):
        """Test JSON adapter creates valid structure"""
        json_output = search_service._create_json_adapter_output(
            MOCK_SEAGOAT_OUTPUT, 
            10
        )
        
        assert "results" in json_output
        assert "total_results" in json_output
        assert "capped_at" in json_output
        assert isinstance(json_output["results"], list)
        assert json_output["total_results"] == len(json_output["results"])
    
    @patch('subprocess.run')
    def test_index_repository_success(self, mock_run, search_service, sample_repo_structure, monkeypatch):
        """Test successful repository indexing"""
        # Mock subprocess success
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        
        # Mock ingest_dir to use sample structure
        monkeypatch.setattr(
            search_service, 
            'ingest_dir', 
            sample_repo_structure.parent.parent.parent
        )
        
        result = search_service.index_repository("test123")
        
        assert result["status"] == "indexed"
        assert result["repo_id"] == "test123"
        assert result["doc_count"] >= 0
        assert "index_time_seconds" in result
        assert "indexed_at" in result
        
        # Verify subprocess was called correctly
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert call_args[1]["shell"] is False  # Verify no shell=True
        assert call_args[1]["timeout"] == 60
    
    @patch('subprocess.run')
    def test_index_repository_not_found(self, mock_run, search_service):
        """Test indexing non-existent repository"""
        with pytest.raises(FileNotFoundError) as exc_info:
            search_service.index_repository("nonexistent")
        
        assert "not found" in str(exc_info.value).lower()
    
    @patch('subprocess.run')
    def test_index_timeout(self, mock_run, search_service, sample_repo_structure, monkeypatch):
        """Test indexing timeout handling"""
        # Mock timeout
        mock_run.side_effect = subprocess.TimeoutExpired("seagoat", 60)
        
        monkeypatch.setattr(
            search_service, 
            'ingest_dir', 
            sample_repo_structure.parent.parent.parent
        )
        
        with pytest.raises(RuntimeError) as exc_info:
            search_service.index_repository("test123")
        
        assert "timeout" in str(exc_info.value).lower()
    
    @patch('subprocess.run')
    def test_search_success(self, mock_run, search_service, sample_repo_structure, monkeypatch):
        """Test successful search"""
        # Mock subprocess success with sample output
        mock_run.return_value = Mock(
            returncode=0, 
            stdout=MOCK_SEAGOAT_OUTPUT, 
            stderr=""
        )
        
        monkeypatch.setattr(
            search_service, 
            'ingest_dir', 
            sample_repo_structure.parent.parent.parent
        )
        
        request = SemanticSearchRequest(
            repo_id="test123",
            query="authentication",
            limit=10
        )
        
        response = search_service.search(request)
        
        assert isinstance(response, SemanticSearchResponse)
        assert response.repo_id == "test123"
        assert response.query == "authentication"
        assert len(response.results) > 0
        assert response.total_results == len(response.results)
        
        # Verify subprocess was called correctly
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert call_args[1]["shell"] is False  # Verify no shell=True
        assert call_args[1]["timeout"] == 30
    
    @patch('subprocess.run')
    def test_search_repository_not_found(self, mock_run, search_service):
        """Test searching non-existent repository"""
        request = SemanticSearchRequest(
            repo_id="nonexistent",
            query="test",
            limit=10
        )
        
        with pytest.raises(FileNotFoundError) as exc_info:
            search_service.search(request)
        
        assert "not found" in str(exc_info.value).lower()
    
    @patch('subprocess.run')
    def test_search_timeout(self, mock_run, search_service, sample_repo_structure, monkeypatch):
        """Test search timeout handling"""
        # Mock timeout
        mock_run.side_effect = subprocess.TimeoutExpired("seagoat", 30)
        
        monkeypatch.setattr(
            search_service, 
            'ingest_dir', 
            sample_repo_structure.parent.parent.parent
        )
        
        request = SemanticSearchRequest(
            repo_id="test123",
            query="test",
            limit=10
        )
        
        with pytest.raises(RuntimeError) as exc_info:
            search_service.search(request)
        
        assert "timeout" in str(exc_info.value).lower()
    
    @patch('subprocess.run')
    def test_search_empty_results(self, mock_run, search_service, sample_repo_structure, monkeypatch):
        """Test search with no results"""
        # Mock empty output
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        
        monkeypatch.setattr(
            search_service, 
            'ingest_dir', 
            sample_repo_structure.parent.parent.parent
        )
        
        request = SemanticSearchRequest(
            repo_id="test123",
            query="nonexistent_function",
            limit=10
        )
        
        response = search_service.search(request)
        
        assert len(response.results) == 0
        assert response.total_results == 0
    
    @patch('subprocess.run')
    def test_search_respects_limit(self, mock_run, search_service, sample_repo_structure, monkeypatch):
        """Test that search respects the limit parameter"""
        # Mock large output
        mock_run.return_value = Mock(
            returncode=0, 
            stdout=MOCK_LARGE_OUTPUT, 
            stderr=""
        )
        
        monkeypatch.setattr(
            search_service, 
            'ingest_dir', 
            sample_repo_structure.parent.parent.parent
        )
        
        request = SemanticSearchRequest(
            repo_id="test123",
            query="function",
            limit=5
        )
        
        response = search_service.search(request)
        
        assert len(response.results) <= 5
    
    def test_relevance_score_range(self, search_service):
        """Test that relevance scores are in valid range"""
        results = search_service._parse_seagoat_output(MOCK_SEAGOAT_OUTPUT, 10)
        
        for result in results:
            assert 0.0 <= result.relevance_score <= 1.0
    
    def test_file_path_extraction(self, search_service):
        """Test correct file path extraction"""
        results = search_service._parse_seagoat_output(MOCK_SEAGOAT_OUTPUT, 10)
        
        file_paths = [r.file_path for r in results]
        assert "src/auth/login.py" in file_paths
        assert "src/utils/helpers.py" in file_paths
    
    def test_line_number_extraction(self, search_service):
        """Test correct line number extraction"""
        results = search_service._parse_seagoat_output(MOCK_SEAGOAT_OUTPUT, 10)
        
        # First result should have line 42
        login_result = next(r for r in results if "login.py" in r.file_path)
        assert login_result.line_number == 42
    
    def test_code_snippet_content(self, search_service):
        """Test that code snippets contain expected content"""
        results = search_service._parse_seagoat_output(MOCK_SEAGOAT_OUTPUT, 10)
        
        login_result = next(r for r in results if "login.py" in r.file_path)
        assert "authenticate_user" in login_result.code_snippet
        assert "username" in login_result.code_snippet or "password" in login_result.code_snippet


class TestSearchServiceEdgeCases:
    """Edge case tests for SearchService"""
    
    @pytest.fixture
    def search_service(self):
        return SearchService()
    
    def test_malformed_grep_line(self, search_service):
        """Test handling of malformed grep-line output"""
        malformed = "this is not a valid grep line\nneither is this"
        results = search_service._parse_seagoat_output(malformed, 10)
        
        # Should handle gracefully and return empty or skip malformed lines
        assert isinstance(results, list)
    
    def test_special_characters_in_path(self, search_service):
        """Test handling of special characters in file paths"""
        special_output = "path/with spaces/file.py:10:def test():\npath-with-dashes.py:20:class Test:"
        results = search_service._parse_seagoat_output(special_output, 10)
        
        assert len(results) >= 0  # Should not crash
    
    def test_zero_limit(self, search_service):
        """Test with limit of 0"""
        results = search_service._parse_seagoat_output(MOCK_SEAGOAT_OUTPUT, 0)
        assert len(results) == 0
    
    def test_negative_limit(self, search_service):
        """Test with negative limit (should handle gracefully)"""
        results = search_service._parse_seagoat_output(MOCK_SEAGOAT_OUTPUT, -1)
        assert len(results) == 0
