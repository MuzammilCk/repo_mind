"""
Ingest Service - Repository cloning and conversion to markdown
Implements safe subprocess calls, encoding fallback, and size limits
"""

import os
import subprocess
import json
import uuid
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from fnmatch import fnmatch

try:
    import git
    GIT_AVAILABLE = True
except ImportError:
    GIT_AVAILABLE = False

from config import settings
from models.requests import IngestRequest
from models.responses import IngestResponse


# Constants for safety guardrails
MAX_BYTES_PER_FILE = 200_000  # 200KB per file to avoid huge embeddings
CMD_TIMEOUT = 600  # 10 minutes timeout for subprocess calls
REPO2TXT_TIMEOUT = 300  # 5 minutes for repo2txt


class IngestService:
    """Service for ingesting repositories with safety guardrails"""
    
    def __init__(self):
        self.ingest_dir = Path(settings.INGEST_DIR)
        self.ingest_dir.mkdir(parents=True, exist_ok=True)
    
    def ingest_repository(self, request: IngestRequest) -> IngestResponse:
        """
        Ingest a repository using repo2txt or custom implementation
        
        Args:
            request: IngestRequest with source and patterns
            
        Returns:
            IngestResponse with paths and stats
            
        Raises:
            ValueError: If neither url nor local_path provided
            RuntimeError: If cloning or processing fails
        """
        repo_id = str(uuid.uuid4())[:8]
        repo_dir = self.ingest_dir / repo_id
        repo_dir.mkdir(parents=True, exist_ok=True)
        
        # Step 1: Clone or use local repository
        if request.source.url:
            local_repo_path = self._clone_repository(
                str(request.source.url), 
                repo_dir / "source"
            )
        elif request.source.local_path:
            local_repo_path = Path(request.source.local_path)
            if not local_repo_path.exists():
                raise ValueError(f"Local path does not exist: {request.source.local_path}")
        else:
            raise ValueError("Either url or local_path must be provided")
        
        # Step 2: Generate repo.md using repo2txt or fallback
        repo_md_path, stats = self._generate_repo_md(
            local_repo_path,
            repo_dir / "repo.md",
            request.include_patterns,
            request.exclude_patterns
        )
        
        # Step 3: Generate tree.json
        tree_json_path = self._generate_tree_json(
            local_repo_path, 
            repo_dir / "tree.json"
        )
        
        # Step 4: Generate content signature for verification
        signature = self._generate_signature(local_repo_path, stats)
        
        return IngestResponse(
            repo_id=repo_id,
            status="completed",
            file_count=stats["file_count"],
            total_lines=stats["total_lines"],
            languages=stats["languages"],
            repo_md_path=str(repo_md_path),
            tree_json_path=str(tree_json_path),
            created_at=datetime.utcnow()
        )
    
    def _clone_repository(self, url: str, target_dir: Path) -> Path:
        """
        Clone a git repository with shallow clone (depth=1)
        
        Args:
            url: Git repository URL
            target_dir: Target directory for clone
            
        Returns:
            Path to cloned repository
            
        Raises:
            RuntimeError: If git is not available or clone fails
        """
        if not GIT_AVAILABLE:
            raise RuntimeError(
                "GitPython not available. Install with: pip install gitpython"
            )
        
        try:
            # Shallow clone with depth=1
            repo = git.Repo.clone_from(
                url, 
                target_dir, 
                depth=1,
                no_single_branch=False
            )
            
            # Verify .git directory exists
            git_dir = target_dir / ".git"
            if not git_dir.exists():
                raise RuntimeError("Clone succeeded but .git directory not found")
            
            return target_dir
            
        except git.GitCommandError as e:
            raise RuntimeError(f"Git clone failed: {str(e)}")
        except Exception as e:
            raise RuntimeError(f"Failed to clone repository: {str(e)}")
    
    def _generate_repo_md(
        self,
        repo_path: Path,
        output_path: Path,
        include_patterns: List[str],
        exclude_patterns: List[str]
    ) -> Tuple[Path, Dict]:
        """
        Generate repo.md using repo2txt or custom implementation
        
        Args:
            repo_path: Path to repository
            output_path: Output path for repo.md
            include_patterns: File patterns to include
            exclude_patterns: File patterns to exclude
            
        Returns:
            Tuple of (output_path, stats_dict)
        """
        # Try repo2txt first
        try:
            result = subprocess.run(
                ["repo2txt", str(repo_path), "-o", str(output_path)],
                capture_output=True,
                text=True,
                timeout=REPO2TXT_TIMEOUT,
                shell=False  # CRITICAL: Never use shell=True
            )
            
            if result.returncode == 0 and output_path.exists():
                stats = self._calculate_stats(repo_path, include_patterns, exclude_patterns)
                return output_path, stats
                
        except subprocess.TimeoutExpired:
            # Timeout - fall back to custom implementation
            pass
        except FileNotFoundError:
            # repo2txt not installed - fall back to custom implementation
            pass
        except Exception:
            # Any other error - fall back to custom implementation
            pass
        
        # Fallback: Custom implementation with robust encoding handling
        return self._custom_repo_to_md(
            repo_path, 
            output_path, 
            include_patterns, 
            exclude_patterns
        )
    
    def _custom_repo_to_md(
        self,
        repo_path: Path,
        output_path: Path,
        include_patterns: List[str],
        exclude_patterns: List[str]
    ) -> Tuple[Path, Dict]:
        """
        Custom implementation to convert repo to markdown with encoding fallback
        
        Args:
            repo_path: Path to repository
            output_path: Output path for repo.md
            include_patterns: File patterns to include
            exclude_patterns: File patterns to exclude
            
        Returns:
            Tuple of (output_path, stats_dict)
        """
        stats = {
            "file_count": 0, 
            "total_lines": 0, 
            "languages": {},
            "skipped_binary": 0,
            "truncated_files": 0
        }
        
        with open(output_path, 'w', encoding='utf-8') as md_file:
            md_file.write(f"# Repository: {repo_path.name}\n\n")
            md_file.write(f"Generated: {datetime.utcnow().isoformat()}\n\n")
            md_file.write("---\n\n")
            
            # Process all files
            for file_path in sorted(repo_path.rglob('*')):
                if not file_path.is_file():
                    continue
                
                # Get relative path
                try:
                    rel_path = file_path.relative_to(repo_path)
                except ValueError:
                    continue
                
                # Check exclusions
                if any(fnmatch(str(rel_path), pattern) for pattern in exclude_patterns):
                    continue
                
                # Check inclusions (if patterns specified)
                if include_patterns:
                    if not any(fnmatch(file_path.name, pattern) for pattern in include_patterns):
                        continue
                
                # Get file extension for language stats
                ext = file_path.suffix or ".txt"
                stats["languages"][ext] = stats["languages"].get(ext, 0) + 1
                stats["file_count"] += 1
                
                # Try to read file with encoding fallback
                content, was_truncated = self._read_file_safe(file_path)
                
                if content is None:
                    # Binary file - skip
                    stats["skipped_binary"] += 1
                    md_file.write(f"## File: {rel_path}\n\n")
                    md_file.write("*Binary file - skipped*\n\n")
                    continue
                
                if was_truncated:
                    stats["truncated_files"] += 1
                
                # Count lines
                lines = content.count('\n')
                stats["total_lines"] += lines
                
                # Write to markdown
                md_file.write(f"## File: {rel_path}\n\n")
                if was_truncated:
                    md_file.write(f"*File truncated to {MAX_BYTES_PER_FILE} bytes*\n\n")
                
                md_file.write(f"```{ext[1:] if ext.startswith('.') else ext}\n")
                md_file.write(content)
                if not content.endswith('\n'):
                    md_file.write('\n')
                md_file.write("```\n\n")
        
        return output_path, stats
    
    def _read_file_safe(self, file_path: Path) -> Tuple[Optional[str], bool]:
        """
        Read file with encoding fallback and size limits
        
        Args:
            file_path: Path to file
            
        Returns:
            Tuple of (content or None if binary, was_truncated)
        """
        try:
            # Check file size
            file_size = file_path.stat().st_size
            was_truncated = file_size > MAX_BYTES_PER_FILE
            
            # Read with size limit
            with open(file_path, 'rb') as f:
                raw_bytes = f.read(MAX_BYTES_PER_FILE)
            
            # Try UTF-8 first
            try:
                content = raw_bytes.decode('utf-8')
                return content, was_truncated
            except UnicodeDecodeError:
                pass
            
            # Fallback to Latin-1 (never fails)
            try:
                content = raw_bytes.decode('latin-1')
                # Check if it looks like text (not binary)
                if self._is_text_content(content):
                    return content, was_truncated
            except:
                pass
            
            # Binary file
            return None, False
            
        except Exception:
            # Any error - treat as binary
            return None, False
    
    def _is_text_content(self, content: str) -> bool:
        """
        Check if content appears to be text (not binary)
        
        Args:
            content: String content
            
        Returns:
            True if appears to be text
        """
        # Check for null bytes (common in binary files)
        if '\x00' in content:
            return False
        
        # Check ratio of printable characters
        printable = sum(c.isprintable() or c in '\n\r\t' for c in content[:1000])
        if len(content) > 0:
            ratio = printable / min(len(content), 1000)
            return ratio > 0.7
        
        return True
    
    def _generate_tree_json(self, repo_path: Path, output_path: Path) -> Path:
        """
        Generate tree.json with repository structure
        
        Args:
            repo_path: Path to repository
            output_path: Output path for tree.json
            
        Returns:
            Path to generated tree.json
        """
        def build_tree(path: Path) -> Dict:
            """Recursively build tree structure"""
            if path.is_file():
                return {
                    "type": "file",
                    "name": path.name,
                    "size": path.stat().st_size
                }
            
            children = []
            try:
                for child in sorted(path.iterdir()):
                    # Skip hidden files/directories
                    if child.name.startswith('.'):
                        continue
                    children.append(build_tree(child))
            except PermissionError:
                # Skip directories we can't read
                pass
            
            return {
                "type": "directory",
                "name": path.name,
                "children": children
            }
        
        tree = build_tree(repo_path)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(tree, f, indent=2)
        
        return output_path
    
    def _calculate_stats(
        self, 
        repo_path: Path,
        include_patterns: List[str],
        exclude_patterns: List[str]
    ) -> Dict:
        """
        Calculate repository statistics
        
        Args:
            repo_path: Path to repository
            include_patterns: File patterns to include
            exclude_patterns: File patterns to exclude
            
        Returns:
            Dictionary with file_count, total_lines, languages
        """
        stats = {"file_count": 0, "total_lines": 0, "languages": {}, "total_size_bytes": 0}
        
        for file_path in repo_path.rglob('*'):
            if not file_path.is_file():
                continue
            
            try:
                rel_path = file_path.relative_to(repo_path)
            except ValueError:
                continue
            
            # Check exclusions
            if any(fnmatch(str(rel_path), pattern) for pattern in exclude_patterns):
                continue
            
            # Check inclusions
            if include_patterns:
                if not any(fnmatch(file_path.name, pattern) for pattern in include_patterns):
                    continue
            
            stats["file_count"] += 1
            ext = file_path.suffix or ".txt"
            stats["languages"][ext] = stats["languages"].get(ext, 0) + 1
            
            # Try to count lines
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = sum(1 for _ in f)
                    stats["total_lines"] += lines
            except:
                pass
        
        return stats
    
    def _generate_signature(self, repo_path: Path, stats: Dict) -> str:
        """
        Generate content signature for verification
        
        Args:
            repo_path: Path to repository
            stats: Statistics dictionary
            
        Returns:
            SHA256 hash signature
        """
        hasher = hashlib.sha256()
        
        # Include timestamp
        hasher.update(datetime.utcnow().isoformat().encode('utf-8'))
        
        # Include repo path
        hasher.update(str(repo_path).encode('utf-8'))
        
        # Include stats
        hasher.update(json.dumps(stats, sort_keys=True).encode('utf-8'))
        
        return hasher.hexdigest()
    
    def get_repo_content(self, repo_id: str) -> str:
        """
        Get the repo.md content for a repository
        
        Args:
            repo_id: Repository ID
            
        Returns:
            Content of repo.md
            
        Raises:
            FileNotFoundError: If repository not found
        """
        repo_md_path = self.ingest_dir / repo_id / "repo.md"
        if not repo_md_path.exists():
            raise FileNotFoundError(f"Repository {repo_id} not found")
        
        return repo_md_path.read_text(encoding='utf-8')
