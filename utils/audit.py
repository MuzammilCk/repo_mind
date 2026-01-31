"""
Audit trail for interactions and executions
Contract: Every action must be logged
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from enum import Enum

from utils.logger import get_logger

logger = get_logger(__name__)


class ActorType(str, Enum):
    """Actor types for audit trail"""
    AI = "ai"
    HUMAN = "human"
    SYSTEM = "system"


class AuditLogger:
    """
    Logs all interactions and executions for audit trail
    
    Contract: Complete traceability of all actions
    """
    
    def __init__(self, audit_dir: Path):
        self.audit_dir = audit_dir
        self.audit_dir.mkdir(parents=True, exist_ok=True)
    
    def log_interaction(
        self,
        interaction_id: str,
        actor: ActorType,
        action: str,
        details: Dict[str, Any],
        repo_id: Optional[str] = None
    ) -> None:
        """
        Log an interaction to audit trail
        
        Args:
            interaction_id: Unique interaction ID
            actor: Who performed the action
            action: What action was performed
            details: Additional details
            repo_id: Optional repository ID
        """
        audit_entry = {
            "interaction_id": interaction_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "actor": actor.value,
            "action": action,
            "repo_id": repo_id,
            "details": details
        }
        
        # Write to audit log file
        audit_file = self.audit_dir / f"{interaction_id}.json"
        
        try:
            with open(audit_file, 'w', encoding='utf-8') as f:
                json.dump(audit_entry, f, indent=2)
            
            logger.info(f"Audit log created: {interaction_id}", extra={
                "actor": actor.value,
                "action": action
            })
        except Exception as e:
            logger.error(f"Failed to write audit log: {str(e)}")
    
    def get_interaction_history(
        self,
        repo_id: Optional[str] = None,
        limit: int = 100
    ) -> list[Dict[str, Any]]:
        """
        Get interaction history
        
        Args:
            repo_id: Filter by repository ID
            limit: Maximum number of entries
            
        Returns:
            List of audit entries
        """
        entries = []
        
        for audit_file in sorted(self.audit_dir.glob("*.json"), reverse=True):
            if len(entries) >= limit:
                break
            
            try:
                with open(audit_file, 'r', encoding='utf-8') as f:
                    entry = json.load(f)
                
                # Filter by repo_id if specified
                if repo_id and entry.get("repo_id") != repo_id:
                    continue
                
                entries.append(entry)
            except Exception as e:
                logger.warning(f"Failed to read audit file {audit_file}: {str(e)}")
        
        return entries
