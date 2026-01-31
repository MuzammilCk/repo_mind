"""
Unit tests for Logger and Metrics utilities
Tests structured logging and metrics collection
"""

import pytest
from unittest.mock import patch, Mock
import json

from utils.logger import filter_secrets, get_logger, set_request_id, clear_request_id
from utils.metrics import MetricsCollector


class TestSecretFiltering:
    """Test suite for secret filtering"""
    
    def test_filter_api_key(self):
        """Test filtering of API keys"""
        data = {
            "repo_id": "test123",
            "api_key": "secret_key_123",
            "normal_field": "visible"
        }
        
        filtered = filter_secrets(data)
        
        assert filtered["repo_id"] == "test123"
        assert filtered["api_key"] == "***REDACTED***"
        assert filtered["normal_field"] == "visible"
    
    def test_filter_nested_secrets(self):
        """Test filtering of nested secrets"""
        data = {
            "config": {
                "gemini_api_key": "secret123",
                "database_url": "postgres://localhost"
            },
            "user": "test_user"
        }
        
        filtered = filter_secrets(data)
        
        assert filtered["config"]["gemini_api_key"] == "***REDACTED***"
        assert filtered["config"]["database_url"] == "postgres://localhost"
        assert filtered["user"] == "test_user"
    
    def test_filter_list_of_dicts(self):
        """Test filtering secrets in list of dictionaries"""
        data = {
            "items": [
                {"name": "item1", "token": "secret1"},
                {"name": "item2", "password": "secret2"}
            ]
        }
        
        filtered = filter_secrets(data)
        
        assert filtered["items"][0]["token"] == "***REDACTED***"
        assert filtered["items"][1]["password"] == "***REDACTED***"
        assert filtered["items"][0]["name"] == "item1"
    
    def test_filter_various_secret_patterns(self):
        """Test filtering of various secret key patterns"""
        data = {
            "API_KEY": "secret1",
            "apikey": "secret2",
            "token": "secret3",
            "password": "secret4",
            "secret": "secret5",
            "authorization": "Bearer token",
            "orchestrator_secret_key": "secret6"
        }
        
        filtered = filter_secrets(data)
        
        # All should be redacted
        for key in data.keys():
            assert filtered[key] == "***REDACTED***"


class TestLogger:
    """Test suite for logger functionality"""
    
    def test_get_logger(self):
        """Test getting a logger instance"""
        logger = get_logger("test_module")
        
        assert logger is not None
        assert logger.name == "test_module"
    
    def test_request_id_context(self):
        """Test request ID context management"""
        from utils.logger import request_id_var
        
        # Initially no request ID
        assert request_id_var.get() is None
        
        # Set request ID
        set_request_id("req_test123")
        assert request_id_var.get() == "req_test123"
        
        # Clear request ID
        clear_request_id()
        assert request_id_var.get() is None


class TestMetricsCollector:
    """Test suite for metrics collection"""
    
    def test_record_request(self, reset_metrics):
        """Test recording a request"""
        collector = reset_metrics
        
        collector.record_request(
            method="GET",
            endpoint="/health",
            status_code=200,
            duration_ms=45.5
        )
        
        metrics = collector.get_metrics()
        
        assert metrics["total_requests"] == 1
        assert metrics["by_endpoint"]["/health"] == 1
        assert metrics["by_status"]["200"] == 1
        assert metrics["by_method"]["GET"] == 1
        assert metrics["avg_duration_ms"] == 45.5
    
    def test_record_multiple_requests(self, reset_metrics):
        """Test recording multiple requests"""
        collector = reset_metrics
        
        collector.record_request("GET", "/health", 200, 10.0)
        collector.record_request("POST", "/api/ingest", 201, 20.0)
        collector.record_request("GET", "/health", 200, 30.0)
        
        metrics = collector.get_metrics()
        
        assert metrics["total_requests"] == 3
        assert metrics["by_endpoint"]["/health"] == 2
        assert metrics["by_endpoint"]["/api/ingest"] == 1
        assert metrics["by_method"]["GET"] == 2
        assert metrics["by_method"]["POST"] == 1
        assert metrics["avg_duration_ms"] == 20.0  # (10+20+30)/3
    
    def test_metrics_by_status_code(self, reset_metrics):
        """Test metrics grouped by status code"""
        collector = reset_metrics
        
        collector.record_request("GET", "/api/test", 200, 10.0)
        collector.record_request("GET", "/api/test", 200, 10.0)
        collector.record_request("GET", "/api/test", 404, 10.0)
        collector.record_request("POST", "/api/test", 500, 10.0)
        
        metrics = collector.get_metrics()
        
        assert metrics["by_status"]["200"] == 2
        assert metrics["by_status"]["404"] == 1
        assert metrics["by_status"]["500"] == 1
    
    def test_reset_metrics(self, reset_metrics):
        """Test resetting metrics"""
        collector = reset_metrics
        
        collector.record_request("GET", "/test", 200, 10.0)
        assert collector.get_metrics()["total_requests"] == 1
        
        collector.reset()
        assert collector.get_metrics()["total_requests"] == 0
    
    def test_requests_per_second(self, reset_metrics):
        """Test requests per second calculation"""
        collector = reset_metrics
        
        # Record some requests
        for _ in range(10):
            collector.record_request("GET", "/test", 200, 10.0)
        
        metrics = collector.get_metrics()
        
        # Should have non-zero RPS
        assert metrics["requests_per_second"] > 0
    
    def test_thread_safety(self, reset_metrics):
        """Test thread-safe metrics collection"""
        import threading
        collector = reset_metrics
        
        def record_requests():
            for _ in range(100):
                collector.record_request("GET", "/test", 200, 10.0)
        
        # Create multiple threads
        threads = [threading.Thread(target=record_requests) for _ in range(5)]
        
        # Start all threads
        for t in threads:
            t.start()
        
        # Wait for completion
        for t in threads:
            t.join()
        
        # Should have recorded all 500 requests
        metrics = collector.get_metrics()
        assert metrics["total_requests"] == 500
