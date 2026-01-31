"""
Search Service - Semantic code search using SeaGOAT
Implements CLI wrapper with JSON adapter for deterministic parsing
"""

import subprocess
import json
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime

from config import settings
from models.requests import SemanticSearchRequest
from models.responses import SemanticSearchResponse, SearchResult


# Constants for safety guardrails
INDEX_TIMEOUT = 60  # 60 seconds for indexing
SEARCH_TIMEOUT = 30  # 30 seconds for search
MAX_RESULTS = 50  # Maximum results to return
MAX_SNIPPET_LENGTH = 500  # Maximum snippet length in characters


class SearchService:
    """Service for semantic code search using SeaGOAT"""
    
    def __init__(self):
        self.ingest_dir = Path(settings.INGEST_DIR)
        self.ingest_dir.mkdir(parents=True, exist_ok=True)
    
    def index_repository(self, repo_id: str) -> Dict:
        """
        Index a repository for semantic search using SeaGOAT
        
        Args:
            repo_id: Repository ID from ingest operation
            
        Returns:
            Dictionary with indexing metadata (status, doc_count, time)
            
        Raises:
            FileNotFoundError: If repository source not found
            RuntimeError: If indexing fails
        """
        repo_source_dir = self.ingest_dir / repo_id / "source"
        
        if not repo_source_dir.exists():
            raise FileNotFoundError(
                f"Repository source not found: {repo_id}. "
                f"Please ingest the repository first."
            )
        
        start_time = datetime.utcnow()
        
        try:
            # SeaGOAT automatically indexes when first queried
            # We'll do a test query to trigger indexing
            result = subprocess.run(
                ["seagoat", "test", str(repo_source_dir)],
                capture_output=True,
                text=True,
                timeout=INDEX_TIMEOUT,
                shell=False,  # CRITICAL: Never use shell=True
                cwd=str(repo_source_dir)
            )
            
            # Calculate indexing time
            index_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Count files in repository for doc_count
            doc_count = sum(1 for _ in repo_source_dir.rglob('*') if _.is_file())
            
            return {
                "status": "indexed",
                "repo_id": repo_id,
                "doc_count": doc_count,
                "index_time_seconds": round(index_time, 2),
                "indexed_at": datetime.utcnow().isoformat()
            }
            
        except subprocess.TimeoutExpired:
            raise RuntimeError(
                f"Indexing timeout exceeded ({INDEX_TIMEOUT}s). "
                f"Repository may be too large."
            )
        except FileNotFoundError:
            raise RuntimeError(
                "SeaGOAT not found. Install with: pip install seagoat"
            )
        except Exception as e:
            raise RuntimeError(f"Failed to index repository: {str(e)}")
    
    def search(self, request: SemanticSearchRequest) -> SemanticSearchResponse:
        """
        Perform semantic search on indexed repository
        
        Args:
            request: SemanticSearchRequest with repo_id, query, and limit
            
        Returns:
            SemanticSearchResponse with structured results
            
        Raises:
            FileNotFoundError: If repository not found
            RuntimeError: If search fails
        """
        repo_source_dir = self.ingest_dir / request.repo_id / "source"
        
        if not repo_source_dir.exists():
            raise FileNotFoundError(
                f"Repository not found: {request.repo_id}. "
                f"Please ingest and index the repository first."
            )
        
        try:
            # Execute SeaGOAT search
            result = subprocess.run(
                ["seagoat", request.query, str(repo_source_dir)],
                capture_output=True,
                text=True,
                timeout=SEARCH_TIMEOUT,
                shell=False,  # CRITICAL: Never use shell=True
                cwd=str(repo_source_dir)
            )
            
            # Parse CLI output using JSON adapter
            search_results = self._parse_seagoat_output(
                result.stdout, 
                request.limit
            )
            
            return SemanticSearchResponse(
                repo_id=request.repo_id,
                query=request.query,
                results=search_results,
                total_results=len(search_results)
            )
            
        except subprocess.TimeoutExpired:
            raise RuntimeError(
                f"Search timeout exceeded ({SEARCH_TIMEOUT}s). "
                f"Try a more specific query."
            )
        except Exception as e:
            raise RuntimeError(f"Search failed: {str(e)}")
    
    def _parse_seagoat_output(
        self, 
        output: str, 
        limit: int
    ) -> List[SearchResult]:
        """
        Parse SeaGOAT CLI output into structured SearchResult objects
        JSON adapter for deterministic parsing
        
        Args:
            output: Raw CLI output from SeaGOAT
            limit: Maximum number of results to return
            
        Returns:
            List of SearchResult objects
        """
        results = []
        
        if not output or not output.strip():
            return results
        
        # SeaGOAT uses grep-line format: path/to/file.py:line_num:content
        lines = output.strip().split('\n')
        
        # Group lines by file
        current_file = None
        current_lines = []
        file_results = {}
        
        for line in lines:
            # Match grep-line format: filepath:linenum:content
            match = re.match(r'^([^:]+):(\d+):(.*)$', line)
            
            if match:
                file_path = match.group(1)
                line_num = int(match.group(2))
                content = match.group(3)
                
                if file_path not in file_results:
                    file_results[file_path] = []
                
                file_results[file_path].append({
                    'line_number': line_num,
                    'content': content
                })
        
        # Convert to SearchResult objects
        for file_path, file_lines in file_results.items():
            if len(results) >= min(limit, MAX_RESULTS):
                break
            
            # Sort by line number
            file_lines.sort(key=lambda x: x['line_number'])
            
            # Create snippet from consecutive lines
            snippet_lines = [fl['content'] for fl in file_lines[:5]]  # Max 5 lines
            snippet = '\n'.join(snippet_lines)
            
            # Truncate snippet if too long
            if len(snippet) > MAX_SNIPPET_LENGTH:
                snippet = snippet[:MAX_SNIPPET_LENGTH] + "... [truncated]"
            
            # Calculate relevance score (simple heuristic: earlier results = higher score)
            relevance_score = max(0.5, 1.0 - (len(results) * 0.05))
            
            # Get first line number
            first_line = file_lines[0]['line_number']
            
            results.append(SearchResult(
                file_path=file_path,
                line_number=first_line,
                code_snippet=snippet,
                relevance_score=round(relevance_score, 2),
                context=f"Found in {file_path}"
            ))
        
        return results[:min(limit, MAX_RESULTS)]
    
    def _create_json_adapter_output(
        self, 
        raw_output: str, 
        limit: int
    ) -> Dict:
        """
        JSON adapter to convert raw CLI output to validated JSON structure
        
        Args:
            raw_output: Raw CLI output
            limit: Result limit
            
        Returns:
            Validated JSON dictionary
        """
        results = self._parse_seagoat_output(raw_output, limit)
        
        return {
            "results": [
                {
                    "file_path": r.file_path,
                    "line_number": r.line_number,
                    "code_snippet": r.code_snippet,
                    "relevance_score": r.relevance_score,
                    "context": r.context
                }
                for r in results
            ],
            "total_results": len(results),
            "capped_at": min(limit, MAX_RESULTS)
        }
