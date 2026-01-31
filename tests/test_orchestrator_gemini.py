import pytest
from unittest.mock import MagicMock, patch
from services.orchestrator import OrchestratorService
from models.requests import OrchestratorRequest
from models.gemini import AnalysisPlan, AnalysisResult, FileToRead

@pytest.fixture
def mock_services():
    with patch('services.orchestrator.IngestService') as MockIngest, \
         patch('services.orchestrator.GeminiService') as MockGemini:
        
        # Setup Orchestrator with mocks
        orchestrator = OrchestratorService()
        orchestrator.ingest_service = MockIngest.return_value
        orchestrator.gemini_service = MockGemini.return_value
        
        # Configure IngestService mock
        orchestrator.ingest_service.get_repo_path.return_value = MagicMock()
        orchestrator.ingest_service.get_file_structure.return_value = ["file1.py", "file2.py"]
        
        # Configure GeminiService mock
        # Plan
        plan = AnalysisPlan(
            approach="Test Plan",
            rationale="Test Logic",
            files_to_read=[FileToRead(path="file1.py", reason="Test")]
        )
        orchestrator.gemini_service.generate_plan.return_value = plan
        
        # Analysis
        result = AnalysisResult(
            summary="Test Result",
            findings=["Found bug"],
            confidence_score=0.9,
            code_changes=[],
            security_risks=[]
        )
        orchestrator.gemini_service.perform_analysis.return_value = result
        
        return orchestrator

def test_generate_actions_deep_analysis(mock_services):
    """Test that 'deep' analysis type generates Gemini steps"""
    request = OrchestratorRequest(repo_id="test-repo", analysis_type="deep")
    actions = mock_services._generate_actions(request)
    
    action_types = [a["action"] for a in actions]
    assert "gemini_think" in action_types
    assert "gemini_analyze" in action_types
    assert len(actions) >= 3  # Ingest + Think + Analyze

def test_execute_plan_flow(mock_services):
    """Test full execution flow of a deep analysis plan"""
    # 1. Generate Plan
    request = OrchestratorRequest(repo_id="test-repo", analysis_type="deep")
    plan_dict = mock_services.create_analysis_plan(request)
    
    # Generate signature for execution
    sig = mock_services.generate_signature(plan_dict, "admin")
    
    # Mock file reading in _execute_single_action
    # Since we use pathlib in the service, we need to mock the path behavior carefully
    # OR we rely on the mocked get_repo_path returning a MagicMock that handles open()
    # Let's simplify and assume the logic works if we don't crash on file read
    mock_file = MagicMock()
    mock_file.read_text.return_value = "content"
    mock_file.exists.return_value = True
    mock_file.is_file.return_value = True
    mock_file.resolve.return_value = MagicMock() # for safety check
    # Ensure resolve check passes (startswith)
    repo_path_mock = mock_services.ingest_service.get_repo_path.return_value
    repo_path_mock.resolve.return_value = MagicMock()
    repo_path_mock.resolve.return_value.__str__.return_value = "/tmp/repo"
    
    mock_file.resolve.return_value.__str__.return_value = "/tmp/repo/file1.py"
    
    # Chain the path / operator
    repo_path_mock.__truediv__.return_value = mock_file
    
    # 2. Execute Plan
    result_plan = mock_services.execute_plan(plan_dict["plan_id"], "admin", sig)
    
    # 3. Verify Results
    assert result_plan["status"] == "completed"
    results = result_plan["results"]
    
    # Find action results
    think_result = next(r for r in results["action_results"] if r["action"] == "gemini_think")
    analyze_result = next(r for r in results["action_results"] if r["action"] == "gemini_analyze")
    
    assert think_result["status"] == "completed"
    assert analyze_result["status"] == "completed"
    assert analyze_result["result"]["analysis"]["summary"] == "Test Result"
    
    # Verify Gemini called correctly
    mock_services.gemini_service.generate_plan.assert_called_once()
    mock_services.gemini_service.perform_analysis.assert_called_once()
