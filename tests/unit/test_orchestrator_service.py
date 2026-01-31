"""
Unit tests for OrchestratorService
Tests plan creation, HMAC signature verification, and execution logic
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json
from pathlib import Path

from services.orchestrator import OrchestratorService
from models.requests import OrchestratorRequest


class TestOrchestratorService:
    """Test suite for OrchestratorService"""
    
    def test_create_plan_no_execution(self, sample_orchestrator_request):
        """Test that plan creation does NOT execute any tools"""
        service = OrchestratorService()
        
        plan = service.create_analysis_plan(sample_orchestrator_request)
        
        # Verify plan structure
        assert "plan_id" in plan
        assert plan["status"] == "pending_approval"
        assert plan["approval_required"] is True
        assert "actions" in plan
        assert len(plan["actions"]) > 0
        
        # Verify no execution happened
        assert plan["executed_at"] is None
        assert plan["results"] is None
    
    def test_plan_has_required_fields(self, sample_orchestrator_request):
        """Test plan contains all required fields"""
        service = OrchestratorService()
        plan = service.create_analysis_plan(sample_orchestrator_request)
        
        required_fields = [
            "plan_id", "created_at", "status", "request",
            "actions", "executed_at", "results",
            "approval_required", "approval_instructions"
        ]
        
        for field in required_fields:
            assert field in plan, f"Missing required field: {field}"
    
    def test_plan_persistence(self, sample_orchestrator_request, tmp_path):
        """Test that plans are persisted to disk"""
        # Use temporary directory for plans
        with patch.object(OrchestratorService, '__init__', lambda self: None):
            service = OrchestratorService()
            service.plans_dir = tmp_path / "plans"
            service.plans_dir.mkdir(parents=True, exist_ok=True)
            service.secret_key = "test_secret_key"
            
            plan = service.create_analysis_plan(sample_orchestrator_request)
            
            # Verify file exists
            plan_file = service.plans_dir / f"{plan['plan_id']}.json"
            assert plan_file.exists()
            
            # Verify file content
            with open(plan_file) as f:
                loaded_plan = json.load(f)
            assert loaded_plan["plan_id"] == plan["plan_id"]
    
    def test_generate_signature(self, sample_orchestrator_request):
        """Test HMAC signature generation"""
        service = OrchestratorService()
        plan = service.create_analysis_plan(sample_orchestrator_request)
        
        approved_by = "test@example.com"
        signature = service.generate_signature(plan, approved_by)
        
        # Verify signature format (SHA256 hex digest is 64 characters)
        assert len(signature) == 64
        assert all(c in '0123456789abcdef' for c in signature)
    
    def test_verify_signature_valid(self, sample_orchestrator_request):
        """Test signature verification with valid signature"""
        service = OrchestratorService()
        plan = service.create_analysis_plan(sample_orchestrator_request)
        
        approved_by = "test@example.com"
        signature = service.generate_signature(plan, approved_by)
        
        # Verify signature
        is_valid = service._verify_signature(plan, approved_by, signature)
        assert is_valid is True
    
    def test_verify_signature_invalid(self, sample_orchestrator_request):
        """Test signature verification with invalid signature"""
        service = OrchestratorService()
        plan = service.create_analysis_plan(sample_orchestrator_request)
        
        # Verify with wrong signature
        is_valid = service._verify_signature(plan, "test@example.com", "invalid_signature")
        assert is_valid is False
    
    def test_execute_plan_requires_signature(self, sample_orchestrator_request):
        """Test that plan execution requires valid signature"""
        service = OrchestratorService()
        plan = service.create_analysis_plan(sample_orchestrator_request)
        
        # Try to execute with invalid signature
        with pytest.raises(PermissionError, match="Invalid approval signature"):
            service.execute_plan(
                plan["plan_id"],
                "test@example.com",
                "invalid_signature"
            )
    
    def test_execute_plan_success(self, sample_orchestrator_request):
        """Test successful plan execution with valid signature"""
        service = OrchestratorService()
        plan = service.create_analysis_plan(sample_orchestrator_request)
        
        # Generate valid signature
        approved_by = "test@example.com"
        signature = service.generate_signature(plan, approved_by)
        
        # Execute plan
        result = service.execute_plan(plan["plan_id"], approved_by, signature)
        
        # Verify execution
        assert result["status"] == "completed"
        assert result["executed_at"] is not None
        assert result["results"] is not None
    
    def test_execute_plan_not_found(self):
        """Test execution of non-existent plan"""
        service = OrchestratorService()
        
        with pytest.raises(FileNotFoundError, match="Plan .* not found"):
            service.execute_plan("nonexistent_plan", "user@test.com", "sig")
    
    def test_execute_plan_idempotent(self, sample_orchestrator_request):
        """Test that executing a plan twice doesn't re-execute"""
        service = OrchestratorService()
        plan = service.create_analysis_plan(sample_orchestrator_request)
        
        approved_by = "test@example.com"
        signature = service.generate_signature(plan, approved_by)
        
        # Execute once
        result1 = service.execute_plan(plan["plan_id"], approved_by, signature)
        first_executed_at = result1["executed_at"]
        
        # Execute again
        result2 = service.execute_plan(plan["plan_id"], approved_by, signature)
        
        # Should return same result without re-execution
        assert result2["executed_at"] == first_executed_at
        assert result2["status"] == "completed"
    
    def test_generate_actions_security_analysis(self):
        """Test action generation for security analysis"""
        service = OrchestratorService()
        request = OrchestratorRequest(
            repo_id="test123",
            analysis_type="security"
        )
        
        actions = service._generate_actions(request)
        
        # Should include CodeQL action for security analysis
        action_types = [a["action"] for a in actions]
        assert "ingest_repository" in action_types
        assert "index_repository" in action_types
        assert "run_codeql" in action_types
    
    def test_generate_actions_with_custom_instructions(self):
        """Test action generation with custom instructions"""
        service = OrchestratorService()
        request = OrchestratorRequest(
            repo_id="test123",
            analysis_type="full",
            custom_instructions="Find authentication code"
        )
        
        actions = service._generate_actions(request)
        
        # Should include semantic search action
        action_types = [a["action"] for a in actions]
        assert "semantic_search" in action_types
        
        # Verify search query
        search_action = next(a for a in actions if a["action"] == "semantic_search")
        assert search_action["params"]["query"] == "Find authentication code"
    
    def test_load_plan(self, sample_orchestrator_request, tmp_path):
        """Test loading plan from disk"""
        with patch.object(OrchestratorService, '__init__', lambda self: None):
            service = OrchestratorService()
            service.plans_dir = tmp_path / "plans"
            service.plans_dir.mkdir(parents=True, exist_ok=True)
            service.secret_key = "test_secret_key"
            
            # Create and persist plan
            plan = service.create_analysis_plan(sample_orchestrator_request)
            
            # Load plan
            loaded_plan = service._load_plan(plan["plan_id"])
            
            assert loaded_plan is not None
            assert loaded_plan["plan_id"] == plan["plan_id"]
    
    def test_load_nonexistent_plan(self):
        """Test loading non-existent plan returns None"""
        service = OrchestratorService()
        
        loaded_plan = service._load_plan("nonexistent_plan")
        assert loaded_plan is None
