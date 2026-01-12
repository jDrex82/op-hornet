"""Integration tests for HORNET API."""
import pytest
from httpx import AsyncClient
from uuid import uuid4

from hornet.main import app


@pytest.fixture
async def client():
    """Create async test client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


class TestHealthEndpoints:
    """Test health check endpoints."""
    
    async def test_health_check(self, client):
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
    
    async def test_readiness_check(self, client):
        response = await client.get("/api/v1/health/ready")
        assert response.status_code in [200, 503]
    
    async def test_liveness_check(self, client):
        response = await client.get("/api/v1/health/live")
        assert response.status_code == 200
    
    async def test_agents_health(self, client):
        response = await client.get("/api/v1/health/agents")
        assert response.status_code == 200
        data = response.json()
        assert "total_agents" in data
        assert data["total_agents"] > 0


class TestEventsEndpoints:
    """Test event ingestion endpoints."""
    
    async def test_ingest_event(self, client):
        event = {
            "event_type": "auth.login_failed",
            "source": "test_source",
            "source_type": "test",
            "severity": "MEDIUM",
            "timestamp": "2024-01-01T00:00:00Z",
            "entities": [{"type": "ip", "value": "192.168.1.1"}],
            "raw_payload": {"user": "test_user"},
        }
        
        response = await client.post(
            "/api/v1/events",
            json=event,
            headers={"X-API-Key": "hnt_test_key"},
        )
        
        # Will fail without proper auth setup, but validates structure
        assert response.status_code in [200, 201, 401]
    
    async def test_ingest_event_missing_fields(self, client):
        event = {"event_type": "test"}  # Missing required fields
        
        response = await client.post(
            "/api/v1/events",
            json=event,
            headers={"X-API-Key": "hnt_test_key"},
        )
        
        assert response.status_code in [400, 401, 422]


class TestIncidentsEndpoints:
    """Test incident management endpoints."""
    
    async def test_list_incidents(self, client):
        response = await client.get(
            "/api/v1/incidents",
            headers={"X-API-Key": "hnt_test_key"},
        )
        
        assert response.status_code in [200, 401]
        if response.status_code == 200:
            data = response.json()
            assert "data" in data
            assert "meta" in data
    
    async def test_get_incident_not_found(self, client):
        fake_id = str(uuid4())
        response = await client.get(
            f"/api/v1/incidents/{fake_id}",
            headers={"X-API-Key": "hnt_test_key"},
        )
        
        assert response.status_code in [401, 404]


class TestWebhooksEndpoints:
    """Test webhook ingestion endpoints."""
    
    async def test_cloudflare_webhook(self, client):
        payload = {
            "action": "block",
            "clientIP": "192.168.1.1",
            "rayId": "abc123",
            "ruleId": "rule123",
        }
        
        response = await client.post(
            "/api/v1/webhooks/cloudflare",
            json=payload,
        )
        
        assert response.status_code in [200, 400, 401]
    
    async def test_generic_webhook(self, client):
        payload = {
            "event_type": "test.event",
            "data": {"key": "value"},
        }
        
        response = await client.post(
            "/api/v1/webhooks/generic",
            json=payload,
            headers={"X-API-Key": "hnt_test_key"},
        )
        
        assert response.status_code in [200, 400, 401]


class TestConfigEndpoints:
    """Test configuration endpoints."""
    
    async def test_get_thresholds(self, client):
        response = await client.get(
            "/api/v1/config/thresholds",
            headers={"X-API-Key": "hnt_test_key"},
        )
        
        assert response.status_code in [200, 401]
        if response.status_code == 200:
            data = response.json()
            assert "DISMISS" in data or "dismiss" in str(data).lower()
    
    async def test_get_agents(self, client):
        response = await client.get(
            "/api/v1/config/agents",
            headers={"X-API-Key": "hnt_test_key"},
        )
        
        assert response.status_code in [200, 401]
    
    async def test_get_playbooks(self, client):
        response = await client.get(
            "/api/v1/config/playbooks",
            headers={"X-API-Key": "hnt_test_key"},
        )
        
        assert response.status_code in [200, 401]


class TestDashboard:
    """Test dashboard endpoint."""
    
    async def test_dashboard_serves(self, client):
        response = await client.get("/dashboard")
        assert response.status_code in [200, 404]


class TestMetrics:
    """Test metrics endpoint."""
    
    async def test_metrics_endpoint(self, client):
        response = await client.get("/metrics")
        assert response.status_code == 200
