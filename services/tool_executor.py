"""
Tool execution functions for Marathon Agent
"""
import requests
import json
from typing import Dict, List, Any, Optional
from urllib.parse import quote_plus
import logging

# Deep Integration Services
try:
    from services.ingest_service import IngestService
    from services.codeql_service import CodeQLService
    from models.requests import IngestRequest, RepoSource, CodeQLScanRequest
    INTEGRATION_AVAILABLE = True
except ImportError:
    INTEGRATION_AVAILABLE = False
    logging.warning("⚠️ Deep integration services not found. Running in API-only mode.")


def search_github_repos(query: str, language: Optional[str] = None, max_results: int = 5) -> Dict[str, Any]:
    """
    Search GitHub for repositories
    """
    try:
        # Build search query
        search_query = query
        if language:
            search_query += f" language:{language}"
        
        url = f"https://api.github.com/search/repositories?q={quote_plus(search_query)}&sort=stars&order=desc&per_page={max_results}"
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        repos = []
        
        for item in data.get('items', [])[:max_results]:
            repos.append({
                "name": item['full_name'],
                "url": item['html_url'],
                "description": item['description'] or "No description",
                "stars": item['stargazers_count'],
                "language": item['language'],
                "topics": item.get('topics', [])
            })
        
        return {
            "status": "success",
            "count": len(repos),
            "repositories": repos
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


def analyze_repository(repo_url: str, focus_areas: List[str] = None) -> Dict[str, Any]:
    """
    Analyze a GitHub repository structure and content (API Metadata)
    """
    if focus_areas is None:
        focus_areas = ["architecture", "dependencies"]
    
    try:
        # Extract owner and repo from URL
        parts = repo_url.rstrip('/').split('/')
        owner, repo = parts[-2], parts[-1]
        
        # Get repo info
        api_url = f"https://api.github.com/repos/{owner}/{repo}"
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        repo_data = response.json()
        
        analysis = {
            "status": "success",
            "repository": f"{owner}/{repo}",
            "language": repo_data.get('language'),
            "size_kb": repo_data.get('size'),
            "topics": repo_data.get('topics', [])
        }
        
        # Get file structure (root level)
        if "file_structure" in focus_areas:
            contents_url = f"https://api.github.com/repos/{owner}/{repo}/contents"
            contents_response = requests.get(contents_url, timeout=10)
            if contents_response.status_code == 200:
                files = contents_response.json()
                analysis["root_files"] = [f['name'] for f in files if f['type'] == 'file']
                analysis["directories"] = [f['name'] for f in files if f['type'] == 'dir']
        
        # Check for common dependency files
        if "dependencies" in focus_areas:
            dependency_files = {}
            for dep_file in ['package.json', 'requirements.txt', 'Cargo.toml', 'go.mod', 'pom.xml']:
                file_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{dep_file}"
                file_response = requests.get(file_url, timeout=5)
                if file_response.status_code == 200:
                    dependency_files[dep_file] = "found"
            
            analysis["dependency_files"] = dependency_files
        
        return analysis
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


def search_npm_packages(query: str, max_results: int = 5) -> Dict[str, Any]:
    """
    Search npm registry for packages
    """
    try:
        url = f"https://registry.npmjs.org/-/v1/search?text={quote_plus(query)}&size={max_results}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        packages = []
        
        for obj in data.get('objects', [])[:max_results]:
            pkg = obj.get('package', {})
            packages.append({
                "name": pkg.get('name'),
                "description": pkg.get('description', ''),
                "version": pkg.get('version'),
                "author": pkg.get('author', {}).get('name') if isinstance(pkg.get('author'), dict) else str(pkg.get('author', '')),
                "npm_url": pkg.get('links', {}).get('npm')
            })
        
        return {
            "status": "success",
            "count": len(packages),
            "packages": packages
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


def search_pypi_packages(query: str, max_results: int = 5) -> Dict[str, Any]:
    """
    Search PyPI for packages
    """
    try:
        url = f"https://pypi.org/pypi?%3Aaction=search&term={quote_plus(query)}"
        return {
            "status": "limited",
            "message": "PyPI search requires web scraping. Use specific package names for best results.",
            "suggestion": "Try using 'requests', 'fastapi', 'django', 'flask' for common packages"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


def generate_mvp_files(
    project_name: str,
    tech_stack: Dict[str, str],
    features: List[str],
    architecture_pattern: str = "monolith"
) -> Dict[str, Any]:
    """
    Generate MVP file structure and content
    """
    try:
        language = tech_stack.get('language', '').lower()
        framework = tech_stack.get('framework', '').lower()
        
        files_generated = {
            "status": "success",
            "project_name": project_name,
            "tech_stack": tech_stack,
            "architecture": architecture_pattern,
            "files": []
        }
        
        # Generate based on language/framework
        if language == "python" and "fastapi" in framework:
            files_generated["files"] = [
                {
                    "path": "main.py",
                    "type": "application_entry",
                    "description": "FastAPI application entry point"
                },
                {
                    "path": "requirements.txt",
                    "type": "dependencies",
                    "description": "Python dependencies"
                },
                {
                    "path": "models.py",
                    "type": "data_models",
                    "description": "Pydantic models for request/response"
                },
                {
                    "path": "database.py",
                    "type": "database",
                    "description": "Database connection and setup"
                }
            ]
        elif language == "javascript" and "react" in framework:
            files_generated["files"] = [
                {
                    "path": "package.json",
                    "type": "dependencies",
                    "description": "Node.js dependencies and scripts"
                },
                {
                    "path": "src/App.jsx",
                    "type": "application_entry",
                    "description": "React application root component"
                },
                {
                    "path": "src/index.js",
                    "type": "entry_point",
                    "description": "Application entry point"
                }
            ]
        else:
            files_generated["files"] = [
                {
                    "path": "README.md",
                    "type": "documentation",
                    "description": "Project documentation"
                }
            ]
        
        files_generated["features_count"] = len(features)
        files_generated["features"] = features
        
        return files_generated
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


import threading
import uuid
import time

# Global job store for async tasks (MVP in-memory)
ASYNC_JOBS = {}

def _run_scan_async(job_id: str, repo_url: str, language: str):
    """Background worker for security scan"""
    try:
        ASYNC_JOBS[job_id]["status"] = "running"
        result = run_security_scan(repo_url, language, background=False)
        ASYNC_JOBS[job_id]["result"] = result
        ASYNC_JOBS[job_id]["status"] = "completed"
    except Exception as e:
        ASYNC_JOBS[job_id]["status"] = "failed"
        ASYNC_JOBS[job_id]["error"] = str(e)

def check_scan_status(job_id: str) -> Dict[str, Any]:
    """
    Check the status of a background security scan
    """
    job = ASYNC_JOBS.get(job_id)
    if not job:
        return {"status": "error", "message": "Job ID not found"}
    
    if job["status"] == "completed":
        return job["result"]
    elif job["status"] == "failed":
        return {"status": "error", "error": job.get("error")}
    else:
        return {
            "status": "running", 
            "message": "Scan is still in progress. Please check again later.",
            "job_id": job_id
        }

def run_security_scan(repo_url: str, language: str = None, background: bool = True) -> Dict[str, Any]:
    """
    Run a real CodeQL security scan.
    If background=True (default), returns a job_id immediately.
    """
    if background:
        job_id = str(uuid.uuid4())[:8]
        ASYNC_JOBS[job_id] = {
            "status": "queued",
            "repo_url": repo_url,
            "submitted_at": time.time()
        }
        
        # Start background thread
        thread = threading.Thread(
            target=_run_scan_async,
            args=(job_id, repo_url, language)
        )
        thread.daemon = True
        thread.start()
        
        return {
            "status": "queued",
            "job_id": job_id,
            "message": "Security scan started in background. Use check_scan_status(job_id) to get results.",
            "estimated_time": "2-5 minutes"
        }

    # Synchronous execution logic (moved from original function)
    print(f"🕵️ Starting security scan for {repo_url}...")
    
    if not INTEGRATION_AVAILABLE:
        return {
            "status": "error",
            "error": "Deep integration services (Ingest/CodeQL) not found or failed to load."
        }

    try:
        # 0. Auto-detect language if missing using metadata API
        if not language:
            print("   🔍 Auto-detecting language...")
            try:
                meta = analyze_repository(repo_url, focus_areas=[])
                gh_lang = meta.get('language', 'Python') # Default to Python
                
                # Map GitHub language to CodeQL language
                lang_map = {
                    "Python": "python",
                    "JavaScript": "javascript", 
                    "TypeScript": "javascript",
                    "Go": "go",
                    "Java": "java",
                    "C++": "cpp",
                    "C#": "csharp",
                    "Ruby": "ruby"
                }
                language = lang_map.get(gh_lang, "python")
                print(f"   ✅ Detected: {language} (from {gh_lang})")
            except:
                language = "python"
                print("   ⚠️ Failed to detect, defaulting to python")

        # 1. Ingest Repository
        ingest_service = IngestService()
        ingest_request = IngestRequest(
            source=RepoSource(url=repo_url),
            include_patterns=["*"],
            exclude_patterns=[".git", "node_modules", "dist", "build"]
        )
        print("   📥 Ingesting repository (this may take a moment)...")
        ingest_response = ingest_service.ingest_repository(ingest_request)
        repo_id = ingest_response.repo_id
        
        # 2. Run CodeQL
        codeql_service = CodeQLService()
        if not codeql_service.codeql_available:
            return {
                "status": "error",
                "message": "CodeQL CLI not found on server",
                "repo_id": repo_id
            }
            
        print(f"   🛡️ Running CodeQL scan for {language}...")
        scan_request = CodeQLScanRequest(
            repo_id=repo_id,
            language=language,
            query_suite="security-extended"
        )
        scan_response = codeql_service.analyze_repository(scan_request)
        
        return {
            "status": "success",
            "repo_id": repo_id,
            "language": language,
            "total_findings": scan_response.total_findings,
            "findings": [f.model_dump() for f in scan_response.findings],
            "scan_duration": scan_response.scan_duration_seconds
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }



def execute_tool(tool_name: str, tool_args: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a tool dynamically"""
    if tool_name not in TOOL_EXECUTORS:
        return {"error": f"Tool {tool_name} not found"}
    
    print(f"🔧 Executing {tool_name} with args: {tool_args}")
    func = TOOL_EXECUTORS[tool_name]
    try:
        return func(**tool_args)
    except Exception as e:
        print(f"❌ Tool execution failed: {e}")
        return {"error": str(e)}

# Tool executor mapping

TOOL_EXECUTORS = {
    "search_github_repos": search_github_repos,
    "analyze_repository": analyze_repository,
    "search_npm_packages": search_npm_packages,
    "search_pypi_packages": search_pypi_packages,
    "generate_mvp_files": generate_mvp_files,
    "run_security_scan": run_security_scan,
    "check_scan_status": check_scan_status
}
