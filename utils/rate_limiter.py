"""
Rate limiter for external tool executions
Contract: All side effects must be rate-limited and timeboxed
"""

import time
from typing import Dict, Optional
from threading import Lock
from datetime import datetime, timedelta

from utils.logger import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """
    Rate limiter for external tool calls
    
    Contract: Prevent runaway tool execution
    """
    
    def __init__(
        self,
        max_calls_per_minute: int = 10,
        max_calls_per_hour: int = 100
    ):
        self.max_calls_per_minute = max_calls_per_minute
        self.max_calls_per_hour = max_calls_per_hour
        
        self.call_history: Dict[str, list[datetime]] = {}
        self.lock = Lock()
    
    def check_rate_limit(self, tool_name: str) -> bool:
        """
        Check if tool call is within rate limits
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            True if within limits, False otherwise
        """
        with self.lock:
            now = datetime.utcnow()
            
            # Initialize history for tool
            if tool_name not in self.call_history:
                self.call_history[tool_name] = []
            
            # Clean old entries
            minute_ago = now - timedelta(minutes=1)
            hour_ago = now - timedelta(hours=1)
            
            self.call_history[tool_name] = [
                ts for ts in self.call_history[tool_name]
                if ts > hour_ago
            ]
            
            # Count recent calls
            calls_last_minute = sum(
                1 for ts in self.call_history[tool_name]
                if ts > minute_ago
            )
            calls_last_hour = len(self.call_history[tool_name])
            
            # Check limits
            if calls_last_minute >= self.max_calls_per_minute:
                logger.warning(f"Rate limit exceeded for {tool_name}: {calls_last_minute}/min")
                return False
            
            if calls_last_hour >= self.max_calls_per_hour:
                logger.warning(f"Rate limit exceeded for {tool_name}: {calls_last_hour}/hour")
                return False
            
            # Record this call
            self.call_history[tool_name].append(now)
            return True
    
    def wait_if_needed(self, tool_name: str, timeout: float = 60.0) -> bool:
        """
        Wait until rate limit allows call
        
        Args:
            tool_name: Name of the tool
            timeout: Maximum wait time in seconds
            
        Returns:
            True if call allowed, False if timeout
        """
        start_time = time.time()
        
        while not self.check_rate_limit(tool_name):
            if time.time() - start_time > timeout:
                logger.error(f"Rate limit timeout for {tool_name}")
                return False
            
            time.sleep(1.0)
        
        return True
    
    def reset(self, tool_name: Optional[str] = None) -> None:
        """
        Reset rate limit history
        
        Args:
            tool_name: Tool to reset, or None for all tools
        """
        with self.lock:
            if tool_name:
                self.call_history[tool_name] = []
            else:
                self.call_history = {}
