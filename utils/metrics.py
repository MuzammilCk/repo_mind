"""
Metrics Collection
Simple in-memory metrics for request tracking
"""

from typing import Dict
from datetime import datetime
import threading


class MetricsCollector:
    """
    Thread-safe in-memory metrics collector
    """
    
    def __init__(self):
        self._lock = threading.Lock()
        self.request_count = 0
        self.request_by_endpoint: Dict[str, int] = {}
        self.request_by_status: Dict[int, int] = {}
        self.request_by_method: Dict[str, int] = {}
        self.total_duration_ms = 0.0
        self.start_time = datetime.utcnow()
    
    def record_request(
        self,
        method: str,
        endpoint: str,
        status_code: int,
        duration_ms: float
    ):
        """
        Record a completed request
        """
        with self._lock:
            self.request_count += 1
            
            # Track by endpoint
            self.request_by_endpoint[endpoint] = self.request_by_endpoint.get(endpoint, 0) + 1
            
            # Track by status code
            self.request_by_status[status_code] = self.request_by_status.get(status_code, 0) + 1
            
            # Track by method
            self.request_by_method[method] = self.request_by_method.get(method, 0) + 1
            
            # Track duration
            self.total_duration_ms += duration_ms
    
    def get_metrics(self) -> Dict:
        """
        Get current metrics snapshot
        """
        with self._lock:
            uptime_seconds = (datetime.utcnow() - self.start_time).total_seconds()
            
            return {
                "total_requests": self.request_count,
                "uptime_seconds": round(uptime_seconds, 2),
                "requests_per_second": round(self.request_count / max(uptime_seconds, 1), 2),
                "avg_duration_ms": round(
                    self.total_duration_ms / max(self.request_count, 1),
                    2
                ),
                "by_endpoint": dict(self.request_by_endpoint),
                "by_status": {str(k): v for k, v in self.request_by_status.items()},
                "by_method": dict(self.request_by_method)
            }
    
    def reset(self):
        """
        Reset all metrics (useful for testing)
        """
        with self._lock:
            self.request_count = 0
            self.request_by_endpoint.clear()
            self.request_by_status.clear()
            self.request_by_method.clear()
            self.total_duration_ms = 0.0
            self.start_time = datetime.utcnow()


# Global metrics collector instance
metrics_collector = MetricsCollector()
