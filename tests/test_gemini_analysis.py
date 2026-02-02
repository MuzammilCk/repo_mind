import pytest
import json
from unittest.mock import MagicMock, patch
from services.gemini_service import GeminiService
from models.gemini import AnalysisResult, AnalysisPlan, FileToRead

@pytest.fixture
def mock_gemini_service():
    with patch('services.gemini_service.GeminiService._verify_gemini'):
        service = GeminiService()
        service.gemini_available = True
        service.gemini_model = "gemini-2.5-flash"
        service.client = MagicMock()
        return service

def test_format_evidence(mock_gemini_service):
    """Test that evidence is formatted with line numbers"""
    files = {
        "test.py": "def foo():\n    return 1"
    }
    evidence = mock_gemini_service._format_evidence(files)
    
    assert "--- START FILE: test.py ---" in evidence
    assert "   1 | def foo():" in evidence
    assert "   2 |     return 1" in evidence
    assert "--- END FILE: test.py ---" in evidence

def test_perform_analysis_success(mock_gemini_service):
    """Test successful analysis flow"""
    # Mock inputs
    plan = AnalysisPlan(
        approach="Test approach",
        files_to_read=[FileToRead(path="test.py", reason="Test")],
        rationale="Test rationale"
    )
    files = {"test.py": "content"}
    
    # Mock response
    result_json = """
    {
        "summary": "Analysis summary",
        "findings": ["Finding 1"],
        "confidence_score": 0.95,
        "code_changes": [],
        "security_risks": []
    }
    """
    mock_response = MagicMock()
    mock_response.outputs = [MagicMock(text=result_json)]
    mock_gemini_service.client.interactions.create.return_value = mock_response
    
    # Execute
    result = mock_gemini_service.perform_analysis("Query", plan, files)
    
    # Verify
    assert isinstance(result, AnalysisResult)
    assert result.summary == "Analysis summary"
    assert result.confidence_score == 0.95
    
    # Verify prompt content
    call_args = mock_gemini_service.client.interactions.create.call_args
    _, kwargs = call_args
    assert "EVIDENCE:" in kwargs['input']
    assert "test.py" in kwargs['input']
    assert kwargs['config']['temperature'] == 0.1

def test_perform_analysis_api_failure(mock_gemini_service):
    """Test handling of API failure during analysis"""
    mock_gemini_service.client.interactions.create.side_effect = Exception("API Error")
    
    with pytest.raises(ValueError) as exc:
        mock_gemini_service.perform_analysis("Query", {}, {})
    assert "Analysis failed" in str(exc.value)
