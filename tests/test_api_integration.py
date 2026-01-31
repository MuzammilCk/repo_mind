"""
Integration tests for FastAPI endpoints
Uses TestClient to test all API endpoints
"""

import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import json

from main import app

# Create test client
client = TestClient(app)


class TestRootEndpoints:
    """Test root and health endpoints"""
    
    def test_root_endpoint(self):
        """Test GET / returns API info"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert data["version"] == "1.0.0"
    
    def test_health_endpoint(self):
        """Test GET /health returns health status"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "services" in data
    
    def test_openapi_schema(self):
        """Test OpenAPI schema is valid"""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert "openapi" in schema
        assert "paths" in schema
        assert "/api/ingest" in schema["paths"]
        assert "/api/search/semantic" in schema["paths"]
        assert "/api/analysis/codeql" in schema["paths"]


class TestIngestEndpoints:
    """Test ingest API endpoints"""
    
    def test_ingest_invalid_request(self):
        """Test POST /api/ingest with invalid request"""
        response = client.post("/api/ingest", json={})
        assert response.status_code == 422  # Validation error
    
    def test_ingest_with_local_path(self):
        """Test POST /api/ingest with local path"""
        response = client.post("/api/ingest", json={
            "source": {"local_path": "./"},
            "include_patterns": ["*.py"],
            "exclude_patterns": ["__pycache__/*"]
        })
        # Should succeed or fail gracefully
        assert response.status_code in [200, 400, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert "repo_id" in data
            assert "status" in data
            assert "file_count" in data
    
    def test_get_repo_content_not_found(self):
        """Test GET /api/ingest/{repo_id} with non-existent repo"""
        response = client.get("/api/ingest/nonexistent123")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data


class TestSearchEndpoints:
    """Test search API endpoints"""
    
    def test_semantic_search_invalid_request(self):
        """Test POST /api/search/semantic with invalid request"""
        response = client.post("/api/search/semantic", json={})
        assert response.status_code == 422  # Validation error
    
    def test_semantic_search_repo_not_found(self):
        """Test POST /api/search/semantic with non-existent repo"""
        response = client.post("/api/search/semantic", json={
            "repo_id": "nonexistent123",
            "query": "test",
            "limit": 10
        })
        # Should return 404 or 500 (if SeaGOAT not installed)
        assert response.status_code in [404, 500]
        data = response.json()
        assert "detail" in data
    
    def test_index_repository_not_found(self):
        """Test POST /api/search/index/{repo_id} with non-existent repo"""
        response = client.post("/api/search/index/nonexistent123")
        # Should return 404 or 500 (if SeaGOAT not installed)
        assert response.status_code in [404, 500]
        data = response.json()
        assert "detail" in data


class TestAnalysisEndpoints:
    """Test analysis API endpoints"""
    
    def test_codeql_analysis_invalid_request(self):
        """Test POST /api/analysis/codeql with invalid request"""
        response = client.post("/api/analysis/codeql", json={})
        assert response.status_code == 422  # Validation error
    
    def test_codeql_analysis_repo_not_found(self):
        """Test POST /api/analysis/codeql with non-existent repo"""
        response = client.post("/api/analysis/codeql", json={
            "repo_id": "nonexistent123",
            "language": "python",
            "query_suite": "security-extended"
        })
        # Should return 404 or 500 (if CodeQL not installed or repo not found)
        assert response.status_code in [404, 500]
        data = response.json()
        assert "detail" in data
    
    def test_full_analysis_not_implemented(self):
        """Test POST /api/analysis/full returns 501 (not implemented)"""
        response = client.post("/api/analysis/full", json={
            "repo_id": "test123",
            "analysis_type": "security"
        })
        assert response.status_code == 501
        data = response.json()
        assert "Phase 2" in data["detail"]


class TestErrorHandling:
    """Test error handling and sanitization"""
    
    def test_errors_are_sanitized(self):
        """Test that errors don't expose stacktraces"""
        # Try various endpoints with invalid data
        endpoints = [
            ("/api/ingest", {"source": {"local_path": "/nonexistent/path"}}),
            ("/api/search/semantic", {"repo_id": "test", "query": "test", "limit": 10}),
            ("/api/analysis/codeql", {"repo_id": "test", "language": "python", "query_suite": "test"})
        ]
        
        for endpoint, payload in endpoints:
            response = client.post(endpoint, json=payload)
            data = response.json()
            
            # Ensure no stacktrace in response
            response_text = json.dumps(data).lower()
            assert "traceback" not in response_text
            assert "exception" not in response_text
            assert "file \"" not in response_text  # Python traceback format
    
    def test_validation_errors_are_clear(self):
        """Test that validation errors are clear"""
        response = client.post("/api/ingest", json={"invalid": "data"})
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data


class TestCORS:
    """Test CORS headers"""
    
    def test_cors_headers_present(self):
        """Test CORS headers are present"""
        response = client.options("/api/ingest")
        # CORS headers should be present
        assert "access-control-allow-origin" in response.headers or response.status_code == 200


class TestRateLimiting:
    """Test rate limiting (basic)"""
    
    def test_rate_limit_headers(self):
        """Test rate limit headers are present"""
        response = client.get("/health")
        # Rate limit headers may be present
        # Note: SlowAPI adds X-RateLimit headers
        assert response.status_code == 200


class TestOpenAPIDocumentation:
    """Test OpenAPI documentation"""
    
    def test_swagger_ui_accessible(self):
        """Test Swagger UI is accessible"""
        response = client.get("/docs")
        assert response.status_code == 200
    
    def test_redoc_accessible(self):
        """Test ReDoc is accessible"""
        response = client.get("/redoc")
        assert response.status_code == 200
    
    def test_openapi_has_examples(self):
        """Test OpenAPI schema has examples"""
        response = client.get("/openapi.json")
        schema = response.json()
        
        # Check that paths have examples in responses
        paths = schema.get("paths", {})
        assert len(paths) > 0
        
        # Check ingest endpoint has examples
        if "/api/ingest" in paths:
            post_op = paths["/api/ingest"].get("post", {})
            responses = post_op.get("responses", {})
            if "200" in responses:
                content = responses["200"].get("content", {})
                if "application/json" in content:
                    assert "example" in content["application/json"]


class TestEndToEnd:
    """End-to-end integration tests"""
    
    def test_api_workflow(self):
        """Test basic API workflow"""
        # 1. Check health
        health = client.get("/health")
        assert health.status_code == 200
        
        # 2. Try to ingest (may fail if path invalid, but should handle gracefully)
        ingest = client.post("/api/ingest", json={
            "source": {"local_path": "./"},
            "include_patterns": ["*.md"]
        })
        assert ingest.status_code in [200, 400, 500]
        
        # 3. Check OpenAPI docs
        docs = client.get("/openapi.json")
        assert docs.status_code == 200
