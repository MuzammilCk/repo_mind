"""
Integration tests for API router flows
Tests complete workflows using FastAPI TestClient
"""

import pytest
from fastapi.testclient import TestClient

from main import app
from utils.metrics import metrics_collector


client = TestClient(app)


class TestHealthAndMetrics:
    """Test health and metrics endpoints"""
    
    def test_health_endpoint(self):
        """Test health endpoint returns correct structure"""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "status" in data
        assert data["status"] == "healthy"
        assert "version" in data
        assert "debug_mode" in data
        assert "uptime_seconds" in data
        assert "services" in data
        
        # Verify services
        services = data["services"]
        assert "ingest" in services
        assert "search" in services
        assert "codeql" in services
        assert "orchestrator" in services
    
    def test_metrics_endpoint(self):
        """Test metrics endpoint returns statistics"""
        response = client.get("/metrics")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "metrics" in data
        assert "timestamp" in data
        
        metrics = data["metrics"]
        assert "total_requests" in metrics
        assert "uptime_seconds" in metrics
        assert "requests_per_second" in metrics
        assert "avg_duration_ms" in metrics
        assert "by_endpoint" in metrics
        assert "by_status" in metrics
        assert "by_method" in metrics
    
    def test_root_endpoint(self):
        """Test root endpoint returns API info"""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "name" in data
        assert "version" in data
        assert "docs" in data
        assert "health" in data
        assert "metrics" in data


class TestRequestIDTracking:
    """Test request ID tracking across requests"""
    
    def test_request_id_in_headers(self):
        """Test request ID is returned in response headers"""
        response = client.get("/health")
        
        assert "X-Request-ID" in response.headers
        request_id = response.headers["X-Request-ID"]
        assert request_id.startswith("req_")
        assert len(request_id) == 16  # req_ + 12 hex chars
    
    def test_unique_request_ids(self):
        """Test each request gets unique ID"""
        response1 = client.get("/health")
        response2 = client.get("/health")
        
        id1 = response1.headers["X-Request-ID"]
        id2 = response2.headers["X-Request-ID"]
        
        assert id1 != id2


class TestOrchestratorFlow:
    """Test complete orchestrator workflow"""
    
    def test_create_plan(self):
        """Test creating an analysis plan"""
        response = client.post("/api/orchestrate/plan", json={
            "repo_id": "test123",
            "analysis_type": "security"
        })
        
        assert response.status_code == 200
        plan = response.json()
        
        # Verify plan structure
        assert "plan_id" in plan
        assert plan["status"] == "pending_approval"
        assert plan["approval_required"] is True
        assert "actions" in plan
        assert len(plan["actions"]) > 0
        assert plan["executed_at"] is None
    
    def test_get_plan(self):
        """Test retrieving a created plan"""
        # Create plan first
        create_response = client.post("/api/orchestrate/plan", json={
            "repo_id": "test456",
            "analysis_type": "full"
        })
        plan_id = create_response.json()["plan_id"]
        
        # Get plan
        get_response = client.get(f"/api/orchestrate/plan/{plan_id}")
        
        assert get_response.status_code == 200
        plan = get_response.json()
        assert plan["plan_id"] == plan_id
    
    def test_get_nonexistent_plan(self):
        """Test getting non-existent plan returns 404"""
        response = client.get("/api/orchestrate/plan/nonexistent_plan")
        
        assert response.status_code == 404
    
    def test_execute_plan_invalid_signature(self):
        """Test executing plan with invalid signature fails"""
        # Create plan
        create_response = client.post("/api/orchestrate/plan", json={
            "repo_id": "test789",
            "analysis_type": "security"
        })
        plan_id = create_response.json()["plan_id"]
        
        # Try to execute with invalid signature
        exec_response = client.post("/api/orchestrate/execute", json={
            "plan_id": plan_id,
            "approved_by": "test@example.com",
            "approval_signature": "invalid_signature"
        })
        
        assert exec_response.status_code == 403
        assert "signature" in exec_response.json()["detail"].lower()
    
    def test_execute_plan_valid_signature(self):
        """Test executing plan with valid signature succeeds"""
        from services.orchestrator import OrchestratorService
        
        # Create plan
        create_response = client.post("/api/orchestrate/plan", json={
            "repo_id": "test_exec",
            "analysis_type": "security"
        })
        plan = create_response.json()
        plan_id = plan["plan_id"]
        
        # Generate valid signature
        service = OrchestratorService()
        approved_by = "test@example.com"
        signature = service.generate_signature(plan, approved_by)
        
        # Execute plan
        exec_response = client.post("/api/orchestrate/execute", json={
            "plan_id": plan_id,
            "approved_by": approved_by,
            "approval_signature": signature
        })
        
        assert exec_response.status_code == 200
        result = exec_response.json()
        assert result["status"] == "completed"
        assert result["executed_at"] is not None
    
    def test_create_plan_with_custom_instructions(self):
        """Test creating plan with custom instructions"""
        response = client.post("/api/orchestrate/plan", json={
            "repo_id": "test_custom",
            "analysis_type": "full",
            "custom_instructions": "Find authentication vulnerabilities"
        })
        
        assert response.status_code == 200
        plan = response.json()
        
        # Should include semantic search action
        actions = plan["actions"]
        action_types = [a["action"] for a in actions]
        assert "semantic_search" in action_types


class TestErrorHandling:
    """Test error handling across endpoints"""
    
    def test_invalid_json_request(self):
        """Test invalid JSON returns 422"""
        response = client.post(
            "/api/orchestrate/plan",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422
    
    def test_missing_required_fields(self):
        """Test missing required fields returns 422"""
        response = client.post("/api/orchestrate/plan", json={
            "analysis_type": "security"
            # Missing repo_id
        })
        
        assert response.status_code == 422
    
    def test_404_not_found(self):
        """Test non-existent endpoint returns 404"""
        response = client.get("/api/nonexistent")
        
        assert response.status_code == 404


class TestMetricsTracking:
    """Test metrics are tracked correctly"""
    
    def test_metrics_track_requests(self, reset_metrics):
        """Test metrics collector tracks API requests"""
        # Make several requests
        client.get("/health")
        client.get("/metrics")
        client.get("/")
        
        # Check metrics
        response = client.get("/metrics")
        metrics = response.json()["metrics"]
        
        # Should have tracked at least 4 requests (including the metrics call itself)
        assert metrics["total_requests"] >= 4
    
    def test_metrics_track_endpoints(self, reset_metrics):
        """Test metrics track individual endpoints"""
        client.get("/health")
        client.get("/health")
        client.get("/metrics")
        
        response = client.get("/metrics")
        metrics = response.json()["metrics"]
        
        # Health should be called at least twice
        assert metrics["by_endpoint"].get("/health", 0) >= 2
    
    def test_metrics_track_status_codes(self, reset_metrics):
        """Test metrics track status codes"""
        client.get("/health")  # 200
        client.get("/api/nonexistent")  # 404
        
        response = client.get("/metrics")
        metrics = response.json()["metrics"]
        
        assert "200" in metrics["by_status"]
        assert "404" in metrics["by_status"]


class TestOpenAPISchema:
    """Test OpenAPI schema generation"""
    
    def test_openapi_json_available(self):
        """Test OpenAPI JSON is available"""
        response = client.get("/openapi.json")
        
        assert response.status_code == 200
        schema = response.json()
        
        assert "openapi" in schema
        assert "info" in schema
        assert "paths" in schema
    
    def test_docs_page_available(self):
        """Test Swagger docs page is available"""
        response = client.get("/docs")
        
        assert response.status_code == 200
    
    def test_metrics_in_schema(self):
        """Test /metrics endpoint is in OpenAPI schema"""
        response = client.get("/openapi.json")
        schema = response.json()
        
        assert "/metrics" in schema["paths"]
        assert "/health" in schema["paths"]
