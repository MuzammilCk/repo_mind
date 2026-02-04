"""
FixBot API Endpoint
Orchestrates: issue fetch → patch generation → testing → PR creation
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import os

from services.github_service import GitHubService
from services.code_patcher import CodePatcher
from services.gemini_service import GeminiService

router = APIRouter(prefix="/api/fixbot", tags=["fixbot"])

# Initialize services
github_service = GitHubService()
gemini_service = GeminiService()
code_patcher = CodePatcher(gemini_service)


class FixIssueRequest(BaseModel):
    repo_url: str
    issue_number: int
    create_pr: Optional[bool] = False  # Set to True to auto-create PR
    github_token: Optional[str] = None  # Optional user token for PR creation


class FixIssueResponse(BaseModel):
    success: bool
    issue_title: str
    patches_applied: list
    test_results: dict
    pr_url: Optional[str] = None
    error: Optional[str] = None
    execution_log: list


@router.post("/fix", response_model=FixIssueResponse)
def fix_github_issue(request: FixIssueRequest):
    """
    Fix a GitHub issue autonomously
    
    Workflow:
    1. Fetch issue details
    2. Clone repository
    3. Generate patch using adaptive macro-planning
    4. Apply patch
    5. Run tests (if available)
    6. Create PR (if requested)
    
    Example:
    {
        "repo_url": "https://github.com/user/repo",
        "issue_number": 42,
        "create_pr": false
    }
    """
    execution_log = []
    
    try:
        # Step 1: Fetch issue
        execution_log.append({"step": "fetch_issue", "status": "started"})
        issue_data = github_service.fetch_issue(request.repo_url, request.issue_number)
        
        if "error" in issue_data:
            raise HTTPException(status_code=400, detail=issue_data["error"])
        
        execution_log.append({
            "step": "fetch_issue",
            "status": "complete",
            "title": issue_data["title"]
        })
        
        # Step 2: Clone repository
        execution_log.append({"step": "clone_repo", "status": "started"})
        clone_result = github_service.clone_repo(request.repo_url)
        
        if not clone_result.get("success"):
            raise HTTPException(status_code=500, detail=clone_result.get("error"))
        
        repo_path = clone_result["path"]
        repo_files = clone_result["files"]
        
        execution_log.append({
            "step": "clone_repo",
            "status": "complete",
            "path": repo_path,
            "files_count": len(repo_files)
        })
        
        # Step 3: Generate patch using adaptive planning
        execution_log.append({"step": "generate_patch", "status": "started"})
        patch_result = code_patcher.generate_patch(issue_data, repo_path, repo_files)
        
        if not patch_result.get("success"):
            raise HTTPException(status_code=500, detail=patch_result.get("error"))
        
        patches = patch_result["patches"]
        execution_log.append({
            "step": "generate_patch",
            "status": "complete",
            "patches_count": len(patches),
            "reasoning": patch_result.get("reasoning", "")[:200]
        })
        
        # Step 4: Apply patches
        execution_log.append({"step": "apply_patches", "status": "started"})
        apply_result = code_patcher.apply_patches(patches, repo_path)
        
        if not apply_result.get("success"):
            execution_log.append({
                "step": "apply_patches",
                "status": "failed",
                "errors": apply_result.get("errors")
            })
        else:
            execution_log.append({
                "step": "apply_patches",
                "status": "complete",
                "files_modified": apply_result["applied_files"]
            })
        
        # Step 5: Run tests (placeholder - implement in Day 2)
        test_results = {"success": True, "message": "Test runner not yet implemented"}
        execution_log.append({
            "step": "run_tests",
            "status": "skipped",
            "reason": "Day 2 feature"
        })
        
        # Step 6: Create PR (if requested)
        pr_url = None
        if request.create_pr:
            execution_log.append({"step": "create_pr", "status": "started"})
            
            # Generate PR description
            pr_description = code_patcher.generate_pr_description(
                issue_data,
                patches,
                test_results
            )
            
            # Create PR (requires user token)
            if request.github_token:
                github_with_token = GitHubService(request.github_token)
                pr_result = github_with_token.create_pr(
                    repo_url=request.repo_url,
                    branch_name=f"fixbot/issue-{request.issue_number}",
                    title=f"Fix: {issue_data['title']}",
                    body=pr_description
                )
                
                if pr_result.get("success"):
                    pr_url = pr_result["pr_url"]
                    execution_log.append({
                        "step": "create_pr",
                        "status": "complete",
                        "pr_url": pr_url
                    })
                else:
                    execution_log.append({
                        "step": "create_pr",
                        "status": "failed",
                        "error": pr_result.get("error")
                    })
            else:
                execution_log.append({
                    "step": "create_pr",
                    "status": "skipped",
                    "reason": "No GitHub token provided"
                })
        
        # Cleanup
        github_service.cleanup_repo(repo_path)
        
        return FixIssueResponse(
            success=True,
            issue_title=issue_data["title"],
            patches_applied=apply_result.get("applied_files", []),
            test_results=test_results,
            pr_url=pr_url,
            execution_log=execution_log
        )
        
    except HTTPException:
        raise
    except Exception as e:
        execution_log.append({
            "step": "error",
            "status": "failed",
            "error": str(e)
        })
        
        return FixIssueResponse(
            success=False,
            issue_title="",
            patches_applied=[],
            test_results={},
            error=str(e),
            execution_log=execution_log
        )


@router.get("/status")
def get_status():
    """Health check for FixBot service"""
    return {
        "service": "FixBot",
        "status": "operational",
        "features": {
            "issue_fetching": True,
            "patch_generation": True,
            "test_running": False,  # Day 2
            "pr_creation": True
        }
    }
