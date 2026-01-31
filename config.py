from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
import os
from pathlib import Path


class Settings(BaseSettings):
    """Configuration settings for Repo Analyzer API"""
    
    # API Configuration
    API_TITLE: str = "Repo Analyzer API"
    API_VERSION: str = "1.0.0"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    
    # Gemini Configuration
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.0-flash-exp"
    
    # Storage Paths
    WORKSPACE_DIR: str = "./workspace"
    INGEST_DIR: str = "./workspace/ingest"
    OUTPUT_DIR: str = "./workspace/output"
    MEMORY_DIR: str = "./workspace/memory"
    
    # CodeQL Configuration
    CODEQL_PATH: str = Field(
        default="codeql",
        description="Path to CodeQL CLI executable"
    )
    CODEQL_DB_DIR: str = "./workspace/codeql-dbs"
    
    # Orchestrator configuration
    ORCHESTRATOR_SECRET_KEY: str = Field(
        default="dev-secret-key-change-in-production-use-strong-random-key",
        description="Secret key for HMAC signature verification in orchestrator"
    )
    
    # SeaGOAT Configuration
    SEAGOAT_PORT: int = 8765
    
    # Validation Configuration
    MAX_REPO_SIZE_MB: int = 500

    
    # Debug mode
    DEBUG: bool = False
    
    # Logging configuration
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)"
    )
    LOG_FORMAT: str = Field(
        default="json",
        description="Log format (json or text)"
    )
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


# Initialize settings
settings = Settings()


def ensure_directories():
    """Create all required workspace directories"""
    directories = [
        settings.WORKSPACE_DIR,
        settings.INGEST_DIR,
        settings.OUTPUT_DIR,
        settings.MEMORY_DIR,
        settings.CODEQL_DB_DIR,
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)


# Create directories on module import
ensure_directories()
