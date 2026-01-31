"""
Centralized Logging Configuration
Structured JSON logging with request IDs and secret filtering
"""

import logging
import json
import sys
from typing import Any, Dict, Optional
from datetime import datetime
from contextvars import ContextVar

from config import settings

# Context variable for request ID
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)

# Sensitive keys that should never be logged
SENSITIVE_KEYS = [
    "api_key",
    "apikey",
    "token",
    "password",
    "secret",
    "authorization",
    "gemini_api_key",
    "orchestrator_secret_key",
    "x-api-key"
]


def filter_secrets(data: Any) -> Any:
    """
    Recursively filter sensitive data from logs
    
    Replaces values of sensitive keys with ***REDACTED***
    """
    if isinstance(data, dict):
        filtered = {}
        for key, value in data.items():
            # Check if key contains sensitive pattern
            if any(pattern in key.lower() for pattern in SENSITIVE_KEYS):
                filtered[key] = "***REDACTED***"
            elif isinstance(value, (dict, list)):
                filtered[key] = filter_secrets(value)
            else:
                filtered[key] = value
        return filtered
    elif isinstance(data, list):
        return [filter_secrets(item) for item in data]
    else:
        return data


class StructuredFormatter(logging.Formatter):
    """
    Custom formatter for structured JSON logging
    """
    
    def format(self, record: logging.LogRecord) -> str:
        # Build structured log entry
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "module": record.name,
            "message": record.getMessage()
        }
        
        # Add request ID if available
        request_id = request_id_var.get()
        if request_id:
            log_entry["request_id"] = request_id
        
        # Add extra fields if present
        if hasattr(record, 'extra') and record.extra:
            log_entry["extra"] = filter_secrets(record.extra)
        
        # Add exception info if present
        if record.exc_info and settings.DEBUG:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Return JSON string
        if settings.LOG_FORMAT == "json":
            return json.dumps(log_entry)
        else:
            # Text format for human readability
            text = f"[{log_entry['timestamp']}] {log_entry['level']} - {log_entry['module']}"
            if request_id:
                text += f" [{request_id}]"
            text += f" - {log_entry['message']}"
            if 'extra' in log_entry:
                text += f" | {json.dumps(log_entry['extra'])}"
            return text


def setup_logging():
    """
    Configure centralized logging
    """
    # Determine log level
    log_level = logging.DEBUG if settings.DEBUG else getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    
    # Create handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredFormatter())
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    
    # Reduce noise from third-party libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name
    """
    return logging.getLogger(name)


def set_request_id(request_id: str):
    """
    Set request ID in context for current request
    """
    request_id_var.set(request_id)


def clear_request_id():
    """
    Clear request ID from context
    """
    request_id_var.set(None)


# Custom LoggerAdapter for adding extra fields
class StructuredLogger(logging.LoggerAdapter):
    """
    Logger adapter that adds extra fields to all log messages
    """
    
    def process(self, msg, kwargs):
        # Add extra field if not present
        if 'extra' not in kwargs:
            kwargs['extra'] = {}
        
        # Merge with adapter's extra
        if self.extra:
            kwargs['extra'].update(self.extra)
        
        # Create a custom record attribute for extra fields
        if 'extra' in kwargs:
            # Store in a way that our formatter can access
            original_extra = kwargs.get('extra', {})
            kwargs['extra'] = {'extra': filter_secrets(original_extra)}
        
        return msg, kwargs


# Initialize logging on module import
setup_logging()
