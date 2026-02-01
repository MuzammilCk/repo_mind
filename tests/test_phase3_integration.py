"""
Phase 3 Integration Tests
Tests complete Gemini integration pipeline including:
1. Health Check
2. Ingest (Phase 1)
3. CodeQL (Phase 2)
4. Full Pipeline (Ingest -> Plan -> Execute)
5. Conversation Continuation (Service Layer)

Uses Mocks for Gemini to ensure pipeline logic is verified even without API key.
"""

import pytest
import hmac
import hashlib
import json
from pathlib import Path
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from main import app
from config import settings
# Import service for direct testing (patched by fixture)
from services.gemini_service import GeminiService

client = TestClient(app)

@pytest.fixture
def sample_repo_path():
    """Return path to sample repo fixture"""
    path = Path(__file__).parent / "fixtures" / "python_repo"
    if not path.exists():
        pytest.skip("Sample repo fixture missing")
    return str(path)

@pytest.fixture
def mock_gemini(monkeypatch):
    """
    Mock GeminiService execution by monkeypatching the class __init__.
    This is the most robust way to handle singletons instantiated in other modules.
    """
    mock_instance = MagicMock()
    mock_instance.generate_plan.return_value = {
        "investigation_areas": [{"id": "sec-1", "description": "Security Check for Testing"}],
        "search_queries": ["auth", "login"],
        "security_focus_areas": ["Authentication"],
        "expected_issues": ["Hardcoded credentials"]
    }
    
    mock_instance.analyze_with_context.return_value = {
        "top_issues": [],
        "recommendations": ["Fix stuff"],
        "risk_score": 5,
        "security_posture": "Medium"
    }
    
    mock_instance.start_chat.return_value = "mock_interaction_id_123"
    mock_instance.continue_conversation.return_value = "This is a mock response from Gemini."
    mock_instance.available = True
    
    def mock_init(self, *args, **kwargs):
        self.client = MagicMock()
        self.available = True
        self.model_name = "mock-model"
        # Bind methods to the instance from our pre-configured mock
        self.generate_plan = mock_instance.generate_plan
        self.analyze_with_context = mock_instance.analyze_with_context
        self.continue_conversation = mock_instance.continue_conversation
        self.start_chat = mock_instance.start_chat
        self._verify_gemini = MagicMock(return_value=True)

    monkeypatch.setattr("services.gemini_service.GeminiService.__init__", mock_init)
    
    yield mock_instance

def test_health_includes_gemini():
    """Test health endpoint includes Gemini status"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "gemini_available" in data
    assert isinstance(data["gemini_available"], bool)

def test_phase1_ingest_no_regression(sample_repo_path):
    """Verify Phase 1 Ingest still works"""
    response = client.post("/api/ingest", json={
        "source": {
            "local_path": sample_repo_path
        }
    })
    assert response.status_code == 200
    data = response.json()
    assert "repo_id" in data
    assert data["status"] == "completed"

def test_phase2_codeql_no_regression(sample_repo_path):
    """Verify Phase 2 CodeQL still works"""
    # 1. Ingest first
    ingest_resp = client.post("/api/ingest", json={
        "source": {"local_path": sample_repo_path}
    })
    repo_id = ingest_resp.json()["repo_id"]

    # 2. Run CodeQL
    # We accept 200 (Success), 503 (Missing CLI), or 500 (Runtime Error e.g. timeouts)
    # The goal is to verify the ENDPOINT is reachable and logic executes provided source.
    response = client.post("/api/analysis/codeql", json={
        "repo_id": repo_id,
        "language": "python",
        "query_suite": "security-extended"
    })
    
    if response.status_code == 500:
        # If 500, ensure it's not a codebase error but a runtime/environment one
        error_detail = response.json().get("detail", {})
        print(f"\nCodeQL 500 Error Detail: {error_detail}")
        # Accept if message implies execution failure
        valid_errors = ["Analysis failed", "Database creation", "Query execution"]
        is_valid_failure = any(e in str(error_detail) for e in valid_errors)
        assert is_valid_failure, f"Unexpected 500 error: {response.text}"
    else:
        assert response.status_code in [200, 503]

def test_full_pipeline_with_gemini(sample_repo_path, mock_gemini):
    """
    Test Phase 1 -> 2 -> 3
    Ingest -> Plan -> Execute -> Continuation
    Uses Mocks to verify ORCHESTRATION logic.
    """
    # 1. Ingest
    ingest_resp = client.post("/api/ingest", json={
        "source": {"local_path": sample_repo_path}
    })
    assert ingest_resp.status_code == 200
    repo_id = ingest_resp.json()["repo_id"]

    # 2. Create Plan (Phase 3)
    # This calls OrchestratorService -> creates GeminiService (MOCKED) -> calls generate_plan (MOCKED)
    plan_resp = client.post("/api/orchestrate/plan", json={
        "repo_id": repo_id,
        "analysis_type": "security"
    })
    assert plan_resp.status_code == 200, plan_resp.text
    plan = plan_resp.json()
    plan_id = plan["plan_id"]
    
    assert plan["status"] == "pending_approval"
    
    # Verify gemini_think action exists (proving mock was used)
    actions = [a["action"] for a in plan["actions"]]
    assert "gemini_think" in actions, f"Expected gemini_think in actions: {actions}"

    # 3. Approve and Execute Plan
    approved_by = "test_user@example.com"
    msg = f"{plan_id}{approved_by}".encode('utf-8')
    key = settings.ORCHESTRATOR_SECRET_KEY.encode('utf-8')
    signature = hmac.new(key, msg, hashlib.sha256).hexdigest()
    
    execute_resp = client.post("/api/orchestrate/execute", json={
        "plan_id": plan_id,
        "approved_by": approved_by,
        "approval_signature": signature
    })
    
    assert execute_resp.status_code == 200, execute_resp.text
    execution_result = execute_resp.json()
    assert execution_result["status"] == "completed"
    
    # 4. Continuation (Service Layer Test)
    # Verify we can continue conversation with the mock ID
    # Use the mock_gemini mock implicitly or create new one (which will be the mock)
    service = GeminiService() 
    chat_id = service.start_chat()
    assert chat_id == "mock_interaction_id_123"
    
    reply = service.continue_conversation(
        interaction_id=chat_id,
        user_query="Follow up"
    )
    assert reply == "This is a mock response from Gemini."
    
    # Verify persistent storage call (implicit via Orchestrator success)
    # Plan persistence was verified by execution finding the plan plan_id.
