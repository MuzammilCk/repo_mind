"""
Agent tools for OSS Discovery Marathon Agent
These tools enable Gemini 3 to autonomously discover, analyze, and generate MVPs
"""

# Tool definitions for Gemini Interactions API
AGENT_TOOLS = [
    {
        "type": "function",
        "name": "search_github_repos",
        "description": "Search GitHub for repositories related to a topic or idea. Returns top matching repositories with stars, description, and language.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (e.g., 'task management react', 'AI chatbot python')"
                },
                "language": {
                    "type": "string",
                    "description": "Optional programming language filter (e.g., 'Python', 'JavaScript')"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return (1-10)",
                    "default": 5
                }
            },
            "required": ["query"]
        }
    },
    {
        "type": "function",
        "name": "analyze_repository",
        "description": "Analyze a GitHub repository to extract architecture patterns, key files, dependencies, and tech stack.",
        "parameters": {
            "type": "object",
            "properties": {
                "repo_url": {
                    "type": "string",
                    "description": "Full GitHub repository URL (e.g., 'https://github.com/user/repo')"
                },
                "focus_areas": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional focus areas: ['architecture', 'dependencies', 'file_structure', 'code_patterns']",
                    "default": ["architecture", "dependencies"]
                }
            },
            "required": ["repo_url"]
        }
    },
    {
        "type": "function",
        "name": "search_npm_packages",
        "description": "Search npm registry for JavaScript/TypeScript packages related to a functionality.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Package search query (e.g., 'state management', 'markdown parser')"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results (1-10)",
                    "default": 5
                }
            },
            "required": ["query"]
        }
    },
    {
        "type": "function",
        "name": "search_pypi_packages",
        "description": "Search PyPI for Python packages related to a functionality.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Package search query (e.g., 'web framework', 'data validation')"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results (1-10)",
                    "default": 5
                }
            },
            "required": ["query"]
        }
    },
    {
        "type": "function",
        "name": "generate_mvp_files",
        "description": "Generate MVP code files based on analyzed patterns and user requirements. Creates actual working code.",
        "parameters": {
            "type": "object",
            "properties": {
                "project_name": {
                    "type": "string",
                    "description": "Name of the MVP project"
                },
                "tech_stack": {
                    "type": "object",
                    "description": "Technology stack specification",
                    "properties": {
                        "language": {"type": "string"},
                        "framework": {"type": "string"},
                        "database": {"type": "string"}
                    }
                },
                "features": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of features to implement"
                },
                "architecture_pattern": {
                    "type": "string",
                    "description": "Architecture pattern to use (e.g., 'MVC', 'microservices', 'monolith')"
                }
            },
            "required": ["project_name", "tech_stack", "features"]
        }
    },
    {
        "type": "function",
        "name": "run_security_scan",
        "description": "Run a deep CodeQL security scan on a repository. IMPORTANT: This runs in the background. It returns a 'job_id'. You MUST use 'check_scan_status(job_id)' to check progress.",
        "parameters": {
            "type": "object",
            "properties": {
                "repo_url": {
                    "type": "string",
                    "description": "Full GitHub repository URL to scan"
                },
                "language": {
                    "type": "string",
                    "description": "Programming language to scan (e.g., 'python', 'javascript')"
                },
                "background": {
                    "type": "boolean",
                    "description": "Run in background (default: true). Set to false only for tiny repos.",
                    "default": True
                }
            },
            "required": ["repo_url"]
        }
    },
    {
        "type": "function",
        "name": "check_scan_status",
        "description": "Check the status of a background security scan job.",
        "parameters": {
            "type": "object",
            "properties": {
                "job_id": {
                    "type": "string",
                    "description": "The Job ID returned by run_security_scan"
                }
            },
            "required": ["job_id"]
        }
    },
    {
        "type": "function",
        "name": "run_code_analysis",
        "description": "Run lightweight static analysis tools (radon, pylint) on a local file or directory.",
        "parameters": {
            "type": "object",
            "properties": {
                "target_path": {
                    "type": "string",
                    "description": "Path to file or directory to analyze"
                },
                "tool": {
                    "type": "string",
                    "description": "Tool to run: 'radon' (complexity), 'pylint' (quality), 'tokei' (stats)",
                    "enum": ["radon", "pylint", "tokei"]
                }
            },
            "required": ["target_path", "tool"]
        }
    },
    {
        "type": "google_search"
    }
]
