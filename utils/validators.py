"""
Evidence and plan validation utilities
Ensures AI cannot invent facts or bypass safety contracts
"""

from typing import Dict, List, Optional, Any
from pathlib import Path
import json
from pydantic import BaseModel, ValidationError

from utils.logger import get_logger

logger = get_logger(__name__)


class EvidenceEntry(BaseModel):
    """Evidence entry with file path and line reference"""
    file_path: str
    line_number: Optional[int] = None
    line_range: Optional[tuple[int, int]] = None
    content: str
    source: str  # "repo.md", "codeql", "seagoat"


class PlanValidationResult(BaseModel):
    """Result of plan validation"""
    valid: bool
    errors: List[str] = []
    warnings: List[str] = []


class EvidenceValidator:
    """
    Validates that evidence entries actually exist in source files
    
    Contract: AI cannot cite non-existent code
    """
    
    def __init__(self, workspace_dir: Path):
        self.workspace_dir = workspace_dir
    
    def validate_evidence(
        self, 
        evidence: EvidenceEntry,
        repo_id: str
    ) -> bool:
        """
        Verify evidence exists in actual files
        
        Args:
            evidence: Evidence entry to validate
            repo_id: Repository ID
            
        Returns:
            True if evidence is valid
        """
        try:
            # Get source file path
            if evidence.source == "repo.md":
                source_file = self.workspace_dir / "ingest" / repo_id / "repo.md"
            elif evidence.source == "codeql":
                source_file = self.workspace_dir / "output" / repo_id / "codeql_results.sarif"
            elif evidence.source == "seagoat":
                source_file = self.workspace_dir / "output" / repo_id / "seagoat_results.json"
            else:
                logger.warning(f"Unknown evidence source: {evidence.source}")
                return False
            
            if not source_file.exists():
                logger.warning(f"Evidence source file not found: {source_file}")
                return False
            
            # Read file content
            content = source_file.read_text(encoding='utf-8')
            
            # Verify content exists
            if evidence.content not in content:
                logger.warning(f"Evidence content not found in {source_file}")
                return False
            
            # If line number specified, verify it
            if evidence.line_number:
                lines = content.split('\n')
                if evidence.line_number > len(lines):
                    logger.warning(f"Line number {evidence.line_number} exceeds file length")
                    return False
                
                # Check if content appears near specified line
                line_content = lines[evidence.line_number - 1]
                if evidence.content.strip() not in line_content:
                    logger.warning(f"Content mismatch at line {evidence.line_number}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating evidence: {str(e)}")
            return False
    
    def validate_plan_evidence(
        self,
        plan: Dict[str, Any],
        repo_id: str
    ) -> PlanValidationResult:
        """
        Validate all evidence entries in a plan
        
        Args:
            plan: Plan dictionary
            repo_id: Repository ID
            
        Returns:
            Validation result with errors/warnings
        """
        result = PlanValidationResult(valid=True)
        
        # Extract evidence from plan
        if "evidence" not in plan:
            result.warnings.append("No evidence field in plan")
            return result
        
        evidence_list = plan["evidence"]
        if not isinstance(evidence_list, list):
            result.valid = False
            result.errors.append("Evidence must be a list")
            return result
        
        # Validate each evidence entry
        for idx, evidence_data in enumerate(evidence_list):
            try:
                evidence = EvidenceEntry(**evidence_data)
                
                if not self.validate_evidence(evidence, repo_id):
                    result.valid = False
                    result.errors.append(
                        f"Evidence {idx} validation failed: {evidence.file_path}"
                    )
            except ValidationError as e:
                result.valid = False
                result.errors.append(f"Evidence {idx} schema error: {str(e)}")
        
        return result


class PlanValidator:
    """
    Validates plan JSON structure and content
    
    Contract: All work orders must be strict JSON
    """
    
    def validate_plan_schema(self, plan: Dict[str, Any]) -> PlanValidationResult:
        """
        Validate plan has required fields and correct types
        
        Args:
            plan: Plan dictionary
            
        Returns:
            Validation result
        """
        result = PlanValidationResult(valid=True)
        
        # Required fields
        required_fields = [
            "plan_id",
            "actions",
            "approval_required",
            "created_at"
        ]
        
        for field in required_fields:
            if field not in plan:
                result.valid = False
                result.errors.append(f"Missing required field: {field}")
        
        # Validate actions structure
        if "actions" in plan:
            if not isinstance(plan["actions"], list):
                result.valid = False
                result.errors.append("Actions must be a list")
            else:
                for idx, action in enumerate(plan["actions"]):
                    if not isinstance(action, dict):
                        result.valid = False
                        result.errors.append(f"Action {idx} must be a dict")
                        continue
                    
                    if "action" not in action:
                        result.valid = False
                        result.errors.append(f"Action {idx} missing 'action' field")
                    
                    if "params" not in action:
                        result.warnings.append(f"Action {idx} missing 'params' field")
        
        return result
    
    def validate_and_fix(
        self,
        plan_json: str,
        max_retries: int = 2
    ) -> tuple[Optional[Dict[str, Any]], List[str]]:
        """
        Validate JSON and attempt to fix if invalid
        
        Args:
            plan_json: JSON string
            max_retries: Maximum fix attempts
            
        Returns:
            Tuple of (parsed_plan or None, errors)
        """
        errors = []
        
        try:
            plan = json.loads(plan_json)
            result = self.validate_plan_schema(plan)
            
            if result.valid:
                return plan, []
            else:
                errors.extend(result.errors)
                return None, errors
                
        except json.JSONDecodeError as e:
            errors.append(f"Invalid JSON: {str(e)}")
            return None, errors
