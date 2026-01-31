import pytest
from services.gemini_service import GeminiService
from unittest.mock import patch, MagicMock

def test_gemini_available_when_key_valid():
    """Test Gemini detection when API key is valid"""
    with patch('google.genai.Client') as mock_client:
        mock_interaction = MagicMock()
        mock_interaction.outputs = [MagicMock(text="OK")]
        mock_client.return_value.interactions.create.return_value = mock_interaction
        
        # Patch the settings to have a valid key
        with patch('config.settings.GEMINI_API_KEY', 'valid_key_12345678'):
            service = GeminiService()
            assert service.gemini_available == True
            assert service.api_key_hash is not None
            assert len(service.api_key_hash) == 8

def test_gemini_unavailable_when_key_missing():
    """Test Gemini detection when API key missing"""
    # Patch settings to have empty key
    with patch('config.settings.GEMINI_API_KEY', ''):
        service = GeminiService()
        assert service.gemini_available == False
        assert service.api_key_hash is None

def test_gemini_unavailable_when_api_fails():
    """Test Gemini detection when API call fails"""
    with patch('google.genai.Client') as mock_client:
        mock_client.return_value.interactions.create.side_effect = Exception("API Error")
        
        with patch('config.settings.GEMINI_API_KEY', 'valid_key'):
            service = GeminiService()
            assert service.gemini_available == False

def test_api_key_never_exposed():
    """Test that full API key is never exposed"""
    with patch('config.settings.GEMINI_API_KEY', 'secret_key'):
        with patch('google.genai.Client'):
            service = GeminiService()
            status = service.get_status()
            
            # Verify API key not in status keys or values
            status_str = str(status).lower()
            assert "secret_key" not in status_str
            assert "api_key" not in status_str.replace("api_key_configured", "").replace("api_key_hash", "")
            
            # Only hash should be present
            if service.gemini_available:
                assert len(status["api_key_hash"]) == 8
