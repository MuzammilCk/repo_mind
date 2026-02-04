"""
Code Patcher Service for FixBot
Uses Gemini's adaptive macro-planning to generate code fixes
"""
from typing import Dict, Any, List
import os
from pathlib import Path


class CodePatcher:
    def __init__(self, gemini_service):
        """Initialize with GeminiService instance"""
        self.gemini = gemini_service
        
    def generate_patch(
        self,
        issue_data: Dict[str, Any],
        repo_path: str,
        repo_files: List[str]
    ) -> Dict[str, Any]:
        """
        Generate code patch for GitHub issue using adaptive planning
        
        Args:
            issue_data: Issue details from GitHubService.fetch_issue()
            repo_path: Path to cloned repository
            repo_files: List of files in repo
            
        Returns:
            Dict with: patches (list of file changes), reasoning, success
        """
        # Build context for Gemini
        context = self._build_fix_context(issue_data, repo_path, repo_files)
        
        # Use marathon_agent with custom goal
        goal = f"""Fix this GitHub issue:

ISSUE: {issue_data['title']}
DESCRIPTION: {issue_data['body']}
LANGUAGE: {issue_data['language']}
FILES MENTIONED: {', '.join(issue_data.get('files_mentioned', []))}

TASK:
1. Analyze the issue and identify root cause
2. Generate a minimal code patch to fix the issue
3. Ensure the fix doesn't break existing functionality

Return the exact file changes needed as a structured patch."""

        try:
            result = self.gemini.marathon_agent(
                user_goal=goal,
                max_iterations=10,
                thinking_level="high"
            )
            
            # Parse result to extract patches
            patches = self._extract_patches_from_result(result, repo_path)
            
            return {
                "success": True,
                "patches": patches,
                "reasoning": result.get("response", ""),
                "tool_calls": result.get("tool_calls", [])
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Patch generation failed: {str(e)}"
            }
    
    def apply_patches(self, patches: List[Dict], repo_path: str) -> Dict[str, Any]:
        """
        Apply generated patches to repository files
        
        Args:
            patches: List of {file_path, old_content, new_content}
            repo_path: Path to repository
            
        Returns:
            Dict with: applied_files, success, errors
        """
        applied = []
        errors = []
        
        for patch in patches:
            try:
                file_path = os.path.join(repo_path, patch['file_path'])
                
                # Read current content
                with open(file_path, 'r', encoding='utf-8') as f:
                    current = f.read()
                
                # Apply patch (simple replacement for now)
                if patch.get('old_content') in current:
                    new_content = current.replace(
                        patch['old_content'],
                        patch['new_content']
                    )
                    
                    # Write patched content
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    
                    applied.append(patch['file_path'])
                else:
                    errors.append(f"Content mismatch in {patch['file_path']}")
                    
            except Exception as e:
                errors.append(f"Failed to patch {patch.get('file_path')}: {str(e)}")
        
        return {
            "success": len(errors) == 0,
            "applied_files": applied,
            "errors": errors
        }
    
    def generate_pr_description(
        self,
        issue_data: Dict[str, Any],
        patches: List[Dict],
        test_results: Dict[str, Any]
    ) -> str:
        """
        Generate PR description using Gemini
        
        Args:
            issue_data: Original issue details
            patches: Applied patches
            test_results: Test execution results
            
        Returns:
            Formatted PR description
        """
        prompt = f"""Generate a professional GitHub PR description for this fix:

ORIGINAL ISSUE: {issue_data['title']}
ISSUE URL: {issue_data.get('url', 'N/A')}

CHANGES MADE:
{self._format_patches_for_pr(patches)}

TEST RESULTS:
{self._format_test_results(test_results)}

Write a clear, concise PR description that:
1. References the issue number
2. Explains what was fixed
3. Shows test results
4. Is ready to merge

Format in GitHub markdown."""

        try:
            # Use Gemini to generate description
            from google import genai
            client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
            
            response = client.models.generate_content(
                model="gemini-3.0-flash-preview",
                contents=prompt
            )
            
            return response.text
            
        except Exception as e:
            # Fallback to template
            return self._fallback_pr_description(issue_data, patches, test_results)
    
    def _build_fix_context(
        self,
        issue_data: Dict,
        repo_path: str,
        repo_files: List[str]
    ) -> str:
        """Build context string for Gemini"""
        # Read mentioned files if they exist
        file_contents = {}
        for file_path in issue_data.get('files_mentioned', [])[:3]:  # Limit to 3 files
            full_path = os.path.join(repo_path, file_path)
            if os.path.exists(full_path):
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        file_contents[file_path] = f.read()[:2000]  # First 2000 chars
                except:
                    pass
        
        context = f"""
Repository: {issue_data.get('repo_name')}
Language: {issue_data.get('language')}
Total Files: {len(repo_files)}

Relevant Files:
{chr(10).join(f'- {path}: {content[:200]}...' for path, content in file_contents.items())}
"""
        return context
    
    def _extract_patches_from_result(
        self,
        result: Dict,
        repo_path: str
    ) -> List[Dict]:
        """Extract structured patches from marathon_agent result"""
        # This is a simplified version - in production, you'd parse
        # the Gemini response more carefully
        patches = []
        
        response_text = result.get("response", "")
        
        # Look for code blocks in response
        import re
        code_blocks = re.findall(r'```(\w+)?\n(.*?)```', response_text, re.DOTALL)
        
        for lang, code in code_blocks:
            # Try to infer file path from context
            # This is naive - improve based on actual Gemini output format
            patches.append({
                "file_path": "unknown.py",  # TODO: Extract from context
                "old_content": "",  # TODO: Extract from diff
                "new_content": code,
                "language": lang
            })
        
        return patches
    
    def _format_patches_for_pr(self, patches: List[Dict]) -> str:
        """Format patches for PR description"""
        lines = []
        for patch in patches:
            lines.append(f"- Modified `{patch['file_path']}`")
        return "\n".join(lines)
    
    def _format_test_results(self, test_results: Dict) -> str:
        """Format test results for PR"""
        if not test_results:
            return "No tests run"
        
        if test_results.get("success"):
            return f"✅ All tests passing ({test_results.get('passed', 0)} passed)"
        else:
            return f"❌ Tests failed: {test_results.get('error', 'Unknown error')}"
    
    def _fallback_pr_description(
        self,
        issue_data: Dict,
        patches: List[Dict],
        test_results: Dict
    ) -> str:
        """Fallback PR description template"""
        return f"""## Fixes #{issue_data.get('url', '').split('/')[-1]}

**Issue**: {issue_data['title']}

**Changes**:
{self._format_patches_for_pr(patches)}

**Test Results**:
{self._format_test_results(test_results)}

---
*Generated by FixBot - Autonomous Issue Solver*
"""
