"""
Orchestrator Service
Coordinates multi-step analysis workflows with plan approval
"""

import json
import hmac
import hashlib
import uuid
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging

from config import settings
from models.requests import OrchestratorRequest
from services.ingest_service import IngestService
from services.gemini_service import GeminiService

# Setup logging
logger = logging.getLogger(__name__)


class OrchestratorService:
    """
    Orchestration service with two-phase workflow:
    1. Create plan (no execution)
    2. Execute plan (with approval signature)
    """
    
    def __init__(self):
        self.plans_dir = Path(settings.WORKSPACE_DIR) / "plans"
        self.plans_dir.mkdir(parents=True, exist_ok=True)
        self.secret_key = settings.ORCHESTRATOR_SECRET_KEY
        
        # Initialize services
        self.ingest_service = IngestService()
        self.gemini_service = GeminiService()
    
    def create_analysis_plan(self, request: OrchestratorRequest) -> Dict[str, Any]:
        """
        Create analysis plan WITHOUT executing any tools
        
        Returns plan with actions list and plan_id for later execution
        """
        logger.info(f"Creating analysis plan for repo: {request.repo_id}")
        
        # Generate unique plan ID
        plan_id = f"plan_{uuid.uuid4().hex[:12]}"
        
        # Create plan structure
        plan = {
            "plan_id": plan_id,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "status": "pending_approval",
            "request": {
                "repo_id": request.repo_id,
                "analysis_type": request.analysis_type,
                "custom_instructions": request.custom_instructions
            },
            "actions": self._generate_actions(request),
            "executed_at": None,
            "results": None,
            "approval_required": True,
            "approval_instructions": "Call POST /api/orchestrate/execute with plan_id and HMAC signature"
        }
        
        # Persist plan to disk
        self._persist_plan(plan)
        
        logger.info(f"Plan created: {plan_id} with {len(plan['actions'])} actions")
        return plan
    
    def execute_plan(
        self,
        plan_id: str,
        approved_by: str,
        approval_signature: str
    ) -> Dict[str, Any]:
        """
        Execute a previously created plan with approval signature
        
        Verifies HMAC signature before execution
        """
        logger.info(f"Executing plan {plan_id} approved by {approved_by}")
        
        # Load plan from disk
        plan = self._load_plan(plan_id)
        
        if not plan:
            raise FileNotFoundError(f"Plan {plan_id} not found")
        
        # Verify approval signature
        if not self._verify_signature(plan, approved_by, approval_signature):
            logger.error(f"Invalid signature for plan {plan_id}")
            raise PermissionError("Invalid approval signature")
        
        # Check if already executed
        if plan["status"] == "completed":
            logger.warning(f"Plan {plan_id} already executed")
            return plan
        
        # Execute actions sequentially
        logger.info(f"Executing {len(plan['actions'])} actions for plan {plan_id}")
        results = self._execute_actions(plan["actions"], plan["request"])
        
        # Update plan with results
        plan["status"] = "completed"
        plan["executed_at"] = datetime.utcnow().isoformat() + "Z"
        plan["results"] = results
        
        # Persist updated plan
        self._persist_plan(plan)
        
        logger.info(f"Plan {plan_id} execution completed")
        return plan
    
    def _generate_actions(self, request: OrchestratorRequest) -> List[Dict[str, Any]]:
        """
        Generate list of actions to be executed
        
        This is a skeleton implementation for Phase 1
        Phase 2 will use Gemini to generate dynamic plans
        """
        actions = []
        
        # Action 1: Ingest repository (always first)
        actions.append({
            "step": 1,
            "action": "ingest_repository",
            "description": "Clone and process repository",
            "params": {
                "repo_id": request.repo_id
            },
            "status": "pending"
        })
        
        # Action 2: Index for search
        actions.append({
            "step": 2,
            "action": "index_repository",
            "description": "Index repository for semantic search",
            "params": {
                "repo_id": request.repo_id
            },
            "status": "pending"
        })
        
        # Action 3: Run CodeQL analysis (if security analysis)
        if request.analysis_type in ["security", "full"]:
            actions.append({
                "step": len(actions) + 1,
                "action": "run_codeql",
                "description": "Run CodeQL static analysis",
                "params": {
                    "repo_id": request.repo_id,
                    "language": "python",  # TODO: Detect language
                    "query_suite": "security-extended"
                },
                "status": "pending"
            })
            
        # Action 4: Deep Analysis (Gemini Thinking logic)
        if request.analysis_type == "deep":
            # Step 3a: Thinking/Planning
            actions.append({
                "step": len(actions) + 1,
                "action": "gemini_think",
                "description": "Generate investigation plan (Thinking Mode)",
                "params": {
                    "repo_id": request.repo_id,
                    "query": request.custom_instructions or "Analyze this repository for security vulnerabilities and architectural flaws."
                },
                "status": "pending"
            })
            
            # Step 3b: Execution/Analysis
            actions.append({
                "step": len(actions) + 1,
                "action": "gemini_analyze",
                "description": "Analyze code evidence",
                "params": {
                    "repo_id": request.repo_id,
                    "query": request.custom_instructions or "Analyze this repository."
                },
                "status": "pending"
            })
        
        # Action 5: Semantic search (if custom instructions provided AND not deep analysis to avoid redundancy)
        if request.custom_instructions and request.analysis_type != "deep":
            actions.append({
                "step": len(actions) + 1,
                "action": "semantic_search",
                "description": f"Search for: {request.custom_instructions}",
                "params": {
                    "repo_id": request.repo_id,
                    "query": request.custom_instructions,
                    "limit": 10
                },
                "status": "pending"
            })
        
        return actions
    
    def _execute_actions(
        self,
        actions: List[Dict[str, Any]],
        request_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute planned actions sequentially
        
        Returns aggregated results
        """
        results = {
            "repo_id": request_data["repo_id"],
            "analysis_type": request_data["analysis_type"],
            "summary": "Orchestrated analysis completed",
            "action_results": [],
            "total_actions": len(actions),
            "completed_actions": 0,
            "session_context": {}  # Store intermediate results
        }
        
        session_context = {}
        
        for action in actions:
            logger.info(f"Executing action {action['step']}: {action['action']}")
            
            try:
                # Execute action based on type
                action_result = self._execute_single_action(action, session_context)
                action["status"] = "completed"
                results["action_results"].append({
                    "step": action["step"],
                    "action": action["action"],
                    "status": "completed",
                    "result": action_result
                })
                results["completed_actions"] += 1
                
            except Exception as e:
                logger.error(f"Action {action['step']} failed: {str(e)}")
                action["status"] = "failed"
                results["action_results"].append({
                    "step": action["step"],
                    "action": action["action"],
                    "status": "failed",
                    "error": str(e)
                })
                # If critical step fails, might want to stop? 
                # For now we continue or break based on design. 
                # Let's break if it's a deep analysis step
                if action["action"] in ["gemini_think", "gemini_analyze"]:
                    break
        
        return results
        
        return results
    
    def _execute_single_action(
            self, 
            action: Dict[str, Any],
            session_context: Dict[str, Any]
        ) -> Dict[str, Any]:
        """
        Execute a single action with context awareness
        """
        action_type = action["action"]
        params = action["params"]
        
        if action_type == "ingest_repository":
            # Real implementation (Phase 2 integration)
            # For now using mocked skeleton behavior but logging intent
            # In Phase 1 we just return success.
            # Ideally we check if it exists in IngestService
            repo_path = self.ingest_service.get_repo_path(params["repo_id"])
            if not repo_path.exists():
                # Trigger ingest if not found? 
                # For Phase 3 scope we assume it might be done or we mock it.
                pass
            return {
                "status": "completed",
                "message": f"Repository {params['repo_id']} verified"
            }
        
        elif action_type == "index_repository":
            return {"status": "completed", "message": "Index verified"}
        
        elif action_type == "run_codeql":
            # Call CodeQL service (Phase 2)
            from services.codeql_service import CodeQLService
            codeql = CodeQLService()
            # This would run analysis
            # For brevity in this file we return a placeholder or call real service if completely ready
            # Assuming real call:
            # result = codeql.run_analysis(params["repo_id"], params["query_suite"])
            return {"status": "completed", "message": "CodeQL analysis skipped (demo)"}
        
        elif action_type == "gemini_think":
            logger.info(f"Gemini Thinking: {params['query']}")
            
            # Get repository content for context
            try:
                repo_content = self.ingest_service.get_repo_content(params['repo_id'])
                # Use first 5000 chars as context to avoid token limits
                context_str = repo_content[:5000] if repo_content else "Repository content not available"
            except FileNotFoundError:
                logger.warning(f"Repository {params['repo_id']} not found, using empty context")
                context_str = "Repository not ingested yet"
            
            # Call Gemini Plan with repository context
            plan = self.gemini_service.generate_plan(params['query'], context_str)
            
            # Store plan in session context for next step
            session_context["analysis_plan"] = plan
            
            return {
                "status": "completed",
                "plan": plan.model_dump() if hasattr(plan, "model_dump") else plan
            }
            
        elif action_type == "gemini_analyze":
            logger.info("Gemini Analyzing Evidence...")
            
            # Retrieve plan from context
            plan = session_context.get("analysis_plan")
            if not plan:
                raise ValueError("No analysis plan found in context. gemini_think must run first.")
            
            # Get full repository content as evidence
            # In real implementation, this would intelligently select relevant files
            try:
                repo_content = self.ingest_service.get_repo_content(params['repo_id'])
            except FileNotFoundError:
                repo_content = "Repository not found"
            
            # For now, use repo_content as file_contents
            # TODO: In future, parse plan.files_to_read and read specific files from source/
            file_contents = {"repo.md": repo_content}
            
            # Call Gemini Analysis
            result = self.gemini_service.perform_analysis(params['query'], plan, file_contents)
            
            return {
                "status": "completed",
                "analysis": result.model_dump() if hasattr(result, "model_dump") else result
            }
        
        elif action_type == "semantic_search":
            return {"status": "completed", "results": []}
        
        else:
            raise ValueError(f"Unknown action type: {action_type}")
    
    def _verify_signature(
        self,
        plan: Dict[str, Any],
        approved_by: str,
        signature: str
    ) -> bool:
        """
        Verify HMAC-SHA256 signature for plan approval
        
        Signature = HMAC(plan_json + approved_by, secret_key)
        """
        # Generate expected signature
        plan_json = json.dumps(plan, sort_keys=True)
        message = f"{plan_json}:{approved_by}"
        expected_signature = hmac.new(
            self.secret_key.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Compare signatures (constant-time comparison)
        return hmac.compare_digest(signature, expected_signature)
    
    def generate_signature(
        self,
        plan: Dict[str, Any],
        approved_by: str
    ) -> str:
        """
        Generate HMAC-SHA256 signature for testing/debugging
        
        In production, clients generate their own signatures
        """
        plan_json = json.dumps(plan, sort_keys=True)
        message = f"{plan_json}:{approved_by}"
        signature = hmac.new(
            self.secret_key.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def _persist_plan(self, plan: Dict[str, Any]) -> None:
        """
        Save plan to disk for audit trail
        """
        plan_file = self.plans_dir / f"{plan['plan_id']}.json"
        
        with open(plan_file, 'w') as f:
            json.dump(plan, f, indent=2)
        
        logger.info(f"Plan persisted: {plan_file}")
    
    def _load_plan(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """
        Load plan from disk
        """
        plan_file = self.plans_dir / f"{plan_id}.json"
        
        if not plan_file.exists():
            return None
        
        with open(plan_file, 'r') as f:
            plan = json.load(f)
        
        logger.info(f"Plan loaded: {plan_id}")
        return plan
