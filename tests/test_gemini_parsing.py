import pytest
from pydantic import BaseModel, ValidationError
from services.gemini_service import GeminiService
from models.gemini import AnalysisPlan, FileToRead

class SimpleModel(BaseModel):
    name: str
    count: int

@pytest.fixture
def service():
    # Only need the parsing method, so we can mock/ignore init verification
    # But since init calls verify, we should probably mock that
    with pytest.helpers.mock_gemini_init():
        return GeminiService()

# Helper for mocking init if helper not available in conftest yet
@pytest.fixture
def clean_service():
    from unittest.mock import patch
    with patch('services.gemini_service.GeminiService._verify_gemini'):
        svc = GeminiService()
        svc.gemini_available = True
        return svc

def test_parse_clean_json(clean_service):
    """Test parsing standard JSON string"""
    json_str = '{"name": "test", "count": 1}'
    result = clean_service.parse_response(json_str, SimpleModel)
    assert result.name == "test"
    assert result.count == 1

def test_parse_markdown_json(clean_service):
    """Test parsing JSON wrapped in markdown code blocks"""
    json_str = '```json\n{"name": "test", "count": 2}\n```'
    result = clean_service.parse_response(json_str, SimpleModel)
    assert result.name == "test"
    assert result.count == 2

def test_parse_markdown_no_lang(clean_service):
    """Test parsing JSON wrapped in generic code blocks"""
    json_str = '```\n{"name": "test", "count": 3}\n```'
    result = clean_service.parse_response(json_str, SimpleModel)
    assert result.name == "test"
    assert result.count == 3

def test_parse_invalid_json(clean_service):
    """Test error handling for malformed JSON"""
    json_str = '{"name": "test", "count": }'  # Invalid JSON
    with pytest.raises(ValueError) as excinfo:
        clean_service.parse_response(json_str, SimpleModel)
    assert "Failed to parse JSON" in str(excinfo.value)

def test_parse_schema_validation_failure(clean_service):
    """Test error handling when JSON matches structure but fails validation"""
    json_str = '{"name": "test", "count": "invalid"}'  # Count should be int
    with pytest.raises(ValueError) as excinfo:
        clean_service.parse_response(json_str, SimpleModel)
    assert "Schema validation failed" in str(excinfo.value)

def test_parse_analysis_plan_success(clean_service):
    """Test parsing a complex real-world AnalysisPlan"""
    json_str = '''
    {
        "approach": "Top-down analysis",
        "rationale": "Starting with main entry point",
        "files_to_read": [
            {
                "path": "main.py",
                "reason": "Entry point"
            }
        ]
    }
    '''
    result = clean_service.parse_response(json_str, AnalysisPlan)
    assert result.approach == "Top-down analysis"
    assert len(result.files_to_read) == 1
    assert result.files_to_read[0].path == "main.py"
