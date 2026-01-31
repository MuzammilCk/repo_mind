"""
Tests for safety contracts and guardrails
Ensures AI cannot invent facts or bypass safety rules
"""

import pytest
from pathlib import Path
import json

from utils.validators import EvidenceValidator, EvidenceEntry, PlanValidator
from utils.audit import AuditLogger, ActorType
from utils.rate_limiter import RateLimiter
from services.gemini_config import PLANNING_CONFIG, ANALYSIS_CONFIG, GENERATION_CONFIG


class TestEvidenceValidator:
    """Test evidence validation - Contract: AI cannot cite non-existent code"""
    
    def test_reject_nonexistent_evidence(self, temp_workspace):
        """Test validator rejects non-existent file evidence"""
        validator = EvidenceValidator(temp_workspace)
        
        evidence = EvidenceEntry(
            file_path="nonexistent.py",
            line_number=10,
            content="fake code",
            source="repo.md"
        )
        
        result = validator.validate_evidence(evidence, "test_repo")
        assert result is False
    
    def test_reject_nonexistent_source_file(self, temp_workspace):
        """Test validator rejects evidence when source file doesn't exist"""
        validator = EvidenceValidator(temp_workspace)
        
        evidence = EvidenceEntry(
            file_path="test.py",
            line_number=1,
            content="some code",
            source="repo.md"
        )
        
        # Source file doesn't exist
        result = validator.validate_evidence(evidence, "missing_repo")
        assert result is False
    
    def test_reject_content_mismatch(self, temp_workspace):
        """Test validator rejects evidence with content that doesn't match"""
        # Create test repo.md
        repo_dir = temp_workspace / "ingest" / "test_repo"
        repo_dir.mkdir(parents=True)
        repo_md = repo_dir / "repo.md"
        repo_md.write_text("Line 1\nLine 2: def foo():\nLine 3\n")
        
        validator = EvidenceValidator(temp_workspace)
        
        # Content doesn't exist in file
        evidence = EvidenceEntry(
            file_path="test.py",
            line_number=2,
            content="def bar():",  # Wrong content
            source="repo.md"
        )
        
        result = validator.validate_evidence(evidence, "test_repo")
        assert result is False
    
    def test_accept_valid_evidence(self, temp_workspace):
        """Test validator accepts valid evidence"""
        # Create test repo.md
        repo_dir = temp_workspace / "ingest" / "test_repo"
        repo_dir.mkdir(parents=True)
        repo_md = repo_dir / "repo.md"
        repo_md.write_text("Line 1\nLine 2: def foo():\nLine 3\n")
        
        validator = EvidenceValidator(temp_workspace)
        
        evidence = EvidenceEntry(
            file_path="test.py",
            line_number=2,
            content="def foo():",
            source="repo.md"
        )
        
        result = validator.validate_evidence(evidence, "test_repo")
        assert result is True
    
    def test_validate_plan_evidence_rejects_invalid(self, temp_workspace):
        """Test plan evidence validation rejects plans with invalid evidence"""
        # Create test repo
        repo_dir = temp_workspace / "ingest" / "test_repo"
        repo_dir.mkdir(parents=True)
        repo_md = repo_dir / "repo.md"
        repo_md.write_text("valid content\n")
        
        validator = EvidenceValidator(temp_workspace)
        
        plan = {
            "plan_id": "test123",
            "evidence": [
                {
                    "file_path": "test.py",
                    "line_number": 1,
                    "content": "invalid content",  # Doesn't exist
                    "source": "repo.md"
                }
            ]
        }
        
        result = validator.validate_plan_evidence(plan, "test_repo")
        assert result.valid is False
        assert len(result.errors) > 0


class TestPlanValidator:
    """Test plan validation - Contract: All work orders must be strict JSON"""
    
    def test_reject_missing_required_fields(self):
        """Test validator rejects plans missing required fields"""
        validator = PlanValidator()
        
        invalid_plan = {
            "plan_id": "test123"
            # Missing actions, approval_required, created_at
        }
        
        result = validator.validate_plan_schema(invalid_plan)
        assert result.valid is False
        assert len(result.errors) >= 3  # At least 3 missing fields
    
    def test_reject_invalid_actions_type(self):
        """Test validator rejects non-list actions"""
        validator = PlanValidator()
        
        invalid_plan = {
            "plan_id": "test123",
            "actions": "not a list",  # Should be list
            "approval_required": True,
            "created_at": "2026-01-31T00:00:00Z"
        }
        
        result = validator.validate_plan_schema(invalid_plan)
        assert result.valid is False
        assert "Actions must be a list" in result.errors
    
    def test_reject_action_missing_fields(self):
        """Test validator rejects actions missing required fields"""
        validator = PlanValidator()
        
        invalid_plan = {
            "plan_id": "test123",
            "actions": [
                {"params": {}}  # Missing 'action' field
            ],
            "approval_required": True,
            "created_at": "2026-01-31T00:00:00Z"
        }
        
        result = validator.validate_plan_schema(invalid_plan)
        assert result.valid is False
        assert any("missing 'action' field" in err for err in result.errors)
    
    def test_accept_valid_plan(self):
        """Test validator accepts valid plan"""
        validator = PlanValidator()
        
        valid_plan = {
            "plan_id": "test123",
            "actions": [
                {"action": "ingest", "params": {"repo_url": "https://github.com/test/repo"}}
            ],
            "approval_required": True,
            "created_at": "2026-01-31T00:00:00Z"
        }
        
        result = validator.validate_plan_schema(valid_plan)
        assert result.valid is True
        assert len(result.errors) == 0
    
    def test_validate_and_fix_invalid_json(self):
        """Test validator handles invalid JSON"""
        validator = PlanValidator()
        
        invalid_json = "{ invalid json }"
        
        plan, errors = validator.validate_and_fix(invalid_json)
        assert plan is None
        assert len(errors) > 0
        assert any("Invalid JSON" in err for err in errors)


class TestAuditLogger:
    """Test audit logging - Contract: Complete traceability"""
    
    def test_log_interaction(self, temp_workspace):
        """Test interaction logging"""
        audit_logger = AuditLogger(temp_workspace / "audit")
        
        audit_logger.log_interaction(
            interaction_id="test_001",
            actor=ActorType.AI,
            action="create_plan",
            details={"plan_id": "plan_123"}
        )
        
        # Verify audit file created
        audit_file = temp_workspace / "audit" / "test_001.json"
        assert audit_file.exists()
        
        # Verify content
        with open(audit_file) as f:
            entry = json.load(f)
        
        assert entry["interaction_id"] == "test_001"
        assert entry["actor"] == "ai"
        assert entry["action"] == "create_plan"
        assert entry["details"]["plan_id"] == "plan_123"
    
    def test_get_interaction_history(self, temp_workspace):
        """Test retrieving interaction history"""
        audit_logger = AuditLogger(temp_workspace / "audit")
        
        # Log multiple interactions
        audit_logger.log_interaction("test_001", ActorType.AI, "action1", {})
        audit_logger.log_interaction("test_002", ActorType.HUMAN, "action2", {}, repo_id="repo1")
        audit_logger.log_interaction("test_003", ActorType.SYSTEM, "action3", {})
        
        # Get all history
        history = audit_logger.get_interaction_history()
        assert len(history) == 3
        
        # Filter by repo_id
        repo_history = audit_logger.get_interaction_history(repo_id="repo1")
        assert len(repo_history) == 1
        assert repo_history[0]["interaction_id"] == "test_002"


class TestRateLimiter:
    """Test rate limiting - Contract: Prevent runaway execution"""
    
    def test_rate_limit_enforcement(self):
        """Test rate limiter blocks excessive calls"""
        limiter = RateLimiter(max_calls_per_minute=2, max_calls_per_hour=10)
        
        # First two calls should succeed
        assert limiter.check_rate_limit("test_tool") is True
        assert limiter.check_rate_limit("test_tool") is True
        
        # Third call should fail (exceeds per-minute limit)
        assert limiter.check_rate_limit("test_tool") is False
    
    def test_rate_limit_per_tool(self):
        """Test rate limits are per-tool"""
        limiter = RateLimiter(max_calls_per_minute=2)
        
        # Different tools have separate limits
        assert limiter.check_rate_limit("tool1") is True
        assert limiter.check_rate_limit("tool1") is True
        assert limiter.check_rate_limit("tool2") is True
        assert limiter.check_rate_limit("tool2") is True
        
        # Each tool's third call fails
        assert limiter.check_rate_limit("tool1") is False
        assert limiter.check_rate_limit("tool2") is False
    
    def test_rate_limit_reset(self):
        """Test rate limit reset"""
        limiter = RateLimiter(max_calls_per_minute=2)
        
        # Exhaust limit
        limiter.check_rate_limit("test_tool")
        limiter.check_rate_limit("test_tool")
        assert limiter.check_rate_limit("test_tool") is False
        
        # Reset
        limiter.reset("test_tool")
        
        # Should work again
        assert limiter.check_rate_limit("test_tool") is True


class TestGeminiConfig:
    """Test Gemini safety configuration - Contract: Low temperature, deterministic"""
    
    def test_planning_config_low_temperature(self):
        """Test planning config has low temperature (≤0.3)"""
        assert PLANNING_CONFIG.temperature <= 0.3
        assert PLANNING_CONFIG.temperature == 0.2
    
    def test_analysis_config_low_temperature(self):
        """Test analysis config has low temperature (≤0.3)"""
        assert ANALYSIS_CONFIG.temperature <= 0.3
        assert ANALYSIS_CONFIG.temperature == 0.3
    
    def test_generation_config_low_temperature(self):
        """Test generation config has very low temperature"""
        assert GENERATION_CONFIG.temperature <= 0.3
        assert GENERATION_CONFIG.temperature == 0.1
    
    def test_json_output_enforcement(self):
        """Test configs enforce JSON output"""
        assert PLANNING_CONFIG.response_mime_type == "application/json"
        assert ANALYSIS_CONFIG.response_mime_type == "application/json"
        assert GENERATION_CONFIG.response_mime_type == "application/json"
    
    def test_to_generation_config(self):
        """Test conversion to Gemini generation config"""
        config = PLANNING_CONFIG.to_generation_config()
        
        assert "temperature" in config
        assert "top_p" in config
        assert "top_k" in config
        assert "max_output_tokens" in config
        assert "response_mime_type" in config
        assert config["response_mime_type"] == "application/json"


class TestSafetyIntegration:
    """Integration tests for safety contracts"""
    
    def test_end_to_end_plan_validation(self, temp_workspace):
        """Test complete plan validation workflow"""
        # Create test repository
        repo_dir = temp_workspace / "ingest" / "test_repo"
        repo_dir.mkdir(parents=True)
        repo_md = repo_dir / "repo.md"
        repo_md.write_text("def authenticate(password):\n    return bcrypt.hash(password)\n")
        
        # Create plan with evidence
        plan = {
            "plan_id": "security_analysis_001",
            "actions": [
                {
                    "action": "analyze_security",
                    "params": {"focus": "authentication"}
                }
            ],
            "approval_required": True,
            "created_at": "2026-01-31T00:00:00Z",
            "evidence": [
                {
                    "file_path": "auth.py",
                    "line_number": 1,
                    "content": "def authenticate(password):",
                    "source": "repo.md"
                }
            ]
        }
        
        # Validate plan schema
        plan_validator = PlanValidator()
        schema_result = plan_validator.validate_plan_schema(plan)
        assert schema_result.valid is True
        
        # Validate evidence
        evidence_validator = EvidenceValidator(temp_workspace)
        evidence_result = evidence_validator.validate_plan_evidence(plan, "test_repo")
        assert evidence_result.valid is True
        
        # Log to audit trail
        audit_logger = AuditLogger(temp_workspace / "audit")
        audit_logger.log_interaction(
            interaction_id="plan_validation_001",
            actor=ActorType.SYSTEM,
            action="validate_plan",
            details={"plan_id": plan["plan_id"], "valid": True}
        )
        
        # Verify audit log
        audit_file = temp_workspace / "audit" / "plan_validation_001.json"
        assert audit_file.exists()
