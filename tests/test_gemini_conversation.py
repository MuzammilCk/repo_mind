import pytest
import uuid
from unittest.mock import MagicMock, patch
from services.gemini_service import GeminiService

@pytest.fixture
def mock_gemini_service():
    with patch('services.gemini_service.GeminiService._verify_gemini'):
        service = GeminiService()
        service.gemini_available = True
        service.gemini_model = "gemini-2.0-flash-exp"
        service.client = MagicMock()
        service.active_chats = {}
        return service

def test_start_chat(mock_gemini_service):
    """Test starting a new chat session"""
    mock_chat = MagicMock()
    mock_gemini_service.client.chats.create.return_value = mock_chat
    
    chat_id = mock_gemini_service.start_chat(system_prompt="Test Prompt")
    
    assert chat_id is not None
    assert isinstance(chat_id, str)
    assert chat_id in mock_gemini_service.active_chats
    assert mock_gemini_service.active_chats[chat_id] == mock_chat
    
    # Verify prompt passed
    call_args = mock_gemini_service.client.chats.create.call_args
    assert call_args[1]['config']['system_instructions'] == "Test Prompt"

def test_continue_chat_success(mock_gemini_service):
    """Test sending a message to an existing chat"""
    # Setup existing chat
    chat_id = "test-uuid"
    mock_chat = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "Chat Response"
    mock_chat.send_message.return_value = mock_response
    
    mock_gemini_service.active_chats[chat_id] = mock_chat
    
    # Execute
    response = mock_gemini_service.continue_chat(chat_id, "Hello")
    
    assert response == "Chat Response"
    mock_chat.send_message.assert_called_once()
    assert mock_chat.send_message.call_args[0][0] == "Hello"

def test_continue_chat_invalid_id(mock_gemini_service):
    """Test continuing a non-existent chat"""
    with pytest.raises(ValueError) as exc:
        mock_gemini_service.continue_chat("invalid-id", "Hello")
    assert "not found" in str(exc.value)

def test_chat_api_failure(mock_gemini_service):
    """Test API failure during chat"""
    chat_id = "test-id"
    mock_chat = MagicMock()
    mock_chat.send_message.side_effect = Exception("API Error")
    mock_gemini_service.active_chats[chat_id] = mock_chat
    
    with pytest.raises(ValueError) as exc:
        mock_gemini_service.continue_chat(chat_id, "Hello")
    assert "Chat failed" in str(exc.value)
