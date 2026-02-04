"""
GitHub Service for FixBot
Handles: issue fetching, repo cloning, PR creation
"""
from github import Github, GithubException
from typing import Dict, Any, Optional
import os
import tempfile
import shutil
import subprocess
from pathlib import Path


class GitHubService:
    def __init__(self, access_token: Optional[str] = None):
        """Initialize GitHub service with optional personal access token"""
        self.token = access_token or os.getenv("GITHUB_TOKEN")
        self.client = Github(self.token) if self.token else Github()
        
    def fetch_issue(self, repo_url: str, issue_number: int) -> Dict[str, Any]:
        """
        Fetch GitHub issue details
        
        Args:
            repo_url: Full GitHub repo URL (e.g., 'https://github.com/facebook/react')
            issue_number: Issue number to fetch
            
        Returns:
            Dict with: title, body, labels, language, files_mentioned
        """
        try:
            # Parse repo from URL
            repo_name = repo_url.replace("https://github.com/", "").replace(".git", "")
            repo = self.client.get_repo(repo_name)
            issue = repo.get_issue(issue_number)
            
            # Extract mentioned files from issue body
            files_mentioned = self._extract_file_mentions(issue.body or "")
            
            return {
                "title": issue.title,
                "body": issue.body,
                "labels": [label.name for label in issue.labels],
                "language": repo.language,
                "state": issue.state,
                "files_mentioned": files_mentioned,
                "repo_name": repo_name,
                "created_at": issue.created_at.isoformat(),
                "url": issue.html_url
            }
        except GithubException as e:
            return {"error": f"GitHub API error: {str(e)}"}
        except Exception as e:
            return {"error": f"Failed to fetch issue: {str(e)}"}
    
    def clone_repo(self, repo_url: str, target_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        Clone GitHub repository to temporary directory
        
        Args:
            repo_url: Full GitHub repo URL
            target_dir: Optional target directory (creates temp dir if None)
            
        Returns:
            Dict with: path, success, error
        """
        try:
            if target_dir is None:
                target_dir = tempfile.mkdtemp(prefix="fixbot_")
            
            # Clone repo
            result = subprocess.run(
                ["git", "clone", "--depth", "1", repo_url, target_dir],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                return {
                    "success": False,
                    "error": f"Git clone failed: {result.stderr}"
                }
            
            return {
                "success": True,
                "path": target_dir,
                "files": self._list_repo_files(target_dir)
            }
            
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Clone timeout (repo too large)"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def create_pr(
        self, 
        repo_url: str, 
        branch_name: str,
        title: str,
        body: str,
        base_branch: str = "main"
    ) -> Dict[str, Any]:
        """
        Create pull request with generated fix
        
        Args:
            repo_url: Full GitHub repo URL
            branch_name: Name of branch with fix
            title: PR title
            body: PR description (include test results)
            base_branch: Target branch (default: main)
            
        Returns:
            Dict with: pr_url, pr_number, success
        """
        try:
            repo_name = repo_url.replace("https://github.com/", "").replace(".git", "")
            repo = self.client.get_repo(repo_name)
            
            pr = repo.create_pull(
                title=title,
                body=body,
                head=branch_name,
                base=base_branch
            )
            
            return {
                "success": True,
                "pr_url": pr.html_url,
                "pr_number": pr.number
            }
            
        except GithubException as e:
            return {"success": False, "error": f"PR creation failed: {str(e)}"}
    
    def _extract_file_mentions(self, text: str) -> list:
        """Extract file paths mentioned in issue body"""
        import re
        # Match common file path patterns
        patterns = [
            r'`([a-zA-Z0-9_/\-\.]+\.[a-zA-Z]+)`',  # `src/file.js`
            r'in ([a-zA-Z0-9_/\-\.]+\.[a-zA-Z]+)',  # in src/file.js
        ]
        
        files = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            files.extend(matches)
        
        return list(set(files))  # Remove duplicates
    
    def _list_repo_files(self, repo_path: str, max_files: int = 100) -> list:
        """List files in cloned repo (limit to avoid huge repos)"""
        files = []
        for root, dirs, filenames in os.walk(repo_path):
            # Skip .git directory
            if '.git' in root:
                continue
            for filename in filenames:
                rel_path = os.path.relpath(os.path.join(root, filename), repo_path)
                files.append(rel_path)
                if len(files) >= max_files:
                    return files
        return files
    
    def cleanup_repo(self, repo_path: str):
        """Delete cloned repository"""
        try:
            shutil.rmtree(repo_path)
        except Exception as e:
            print(f"Failed to cleanup {repo_path}: {e}")
