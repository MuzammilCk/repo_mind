import pytest
from unittest.mock import MagicMock, patch
from services.gemini_service import GeminiService
from models.gemini import AnalysisPlan

@pytest.fixture
def mock_gemini_service():
    """Returns a GeminiService with mocked verification"""
    with patch('services.gemini_service.GeminiService._verify_gemini'):
        service = GeminiService()
        service.gemini_available = True
        service.gemini_model = "gemini-2.5-flash"
        service.client = MagicMock()
        return service

def test_generate_plan_success(mock_gemini_service):
    """Test successful plan generation pipeline"""
    # Mock response data
    plan_json = """
    {
        "approach": "Check authentication middleware",
        "rationale": "Auth flow starts there",
        "files_to_read": [
            {
                "path": "api/middleware.py",
                "reason": "Contains auth logic"
            },
            {
                "path": "main.py",
                "reason": "Mounts middleware"
            }
        ]
    }
    """
    
    # Setup mock chain
    mock_response = MagicMock()
    mock_response.outputs = [MagicMock(text=plan_json)]
    mock_gemini_service.client.interactions.create.return_value = mock_response
    
    # Execute
    plan = mock_gemini_service.generate_plan(
        query="How does auth work?",
        file_context="main.py\napi/middleware.py"
    )
    
    # Verify
    assert isinstance(plan, AnalysisPlan)
    assert plan.approach == "Check authentication middleware"
    assert len(plan.files_to_read) == 2
    assert plan.files_to_read[0].path == "api/middleware.py"
    
    # Verify prompt construction (args passed to create)
    call_args = mock_gemini_service.client.interactions.create.call_args
    assert call_args is not None
    _, kwargs = call_args
    assert "CONTEXT:\nmain.py" in kwargs['input']
    assert "USER QUERY:\nHow does auth work?" in kwargs['input']
    assert kwargs['config']['temperature'] == 0.2

def test_generate_plan_api_failure(mock_gemini_service):
    """Test handling of API errors"""
    mock_gemini_service.client.interactions.create.side_effect = Exception("API Unavailable")
    
    with pytest.raises(ValueError) as exc:
        mock_gemini_service.generate_plan("query", "context")
    assert "Plan generation failed" in str(exc.value)

def test_generate_plan_invalid_json(mock_gemini_service):
    """Test handling of invalid JSON from model"""
    mock_response = MagicMock()
    mock_response.outputs = [MagicMock(text="{invalid json")]
    mock_gemini_service.client.interactions.create.return_value = mock_response
    
    with pytest.raises(ValueError) as exc:
        mock_gemini_service.generate_plan("query", "context")
    assert "Failed to parse JSON" in str(exc.value)
