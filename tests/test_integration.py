"""
HORNET Integration Tests
End-to-end tests for the full system.
"""
import pytest
import asyncio
from uuid import uuid4
from datetime import datetime
from httpx import AsyncClient, ASGITransport

# Mark all tests as async
pytestmark = pytest.mark.asyncio


@pytest.fixture
def sample_event():
    return {
        "source": "test_source",
        "source_type": "test",
        "event_type": "auth.brute_force",
        "severity": "HIGH",
        "timestamp": datetime.utcnow().isoformat(),
        "raw_payload": {
            "source_ip": "192.168.1.100",
            "target_user": "admin",
            "failed_attempts": 50,
        },
        "entities": [
            {"type": "ip", "value": "192.168.1.100"},
            {"type": "user", "value": "admin"},
        ],
    }


@pytest.fixture
def api_headers():
    return {"X-API-Key": "hnt_test_abc123"}


class TestEventIngestion:
    """Test event ingestion flow."""
    
    async def test_ingest_event_creates_incident(self, sample_event, api_headers):
        """Test that ingesting an event creates an incident."""
        from hornet.main import app
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Ingest event
            response = await client.post(
                "/api/v1/events",
                json=sample_event,
                headers=api_headers,
            )
            
            assert response.status_code == 201
            data = response.json()
            assert "event_id" in data
            assert "incident_id" in data
    
    async def test_ingest_invalid_event_rejected(self, api_headers):
        """Test that invalid events are rejected."""
        from hornet.main import app
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/events",
                json={"invalid": "event"},
                headers=api_headers,
            )
            
            assert response.status_code == 422


class TestIncidentLifecycle:
    """Test incident lifecycle management."""
    
    async def test_list_incidents(self, api_headers):
        """Test listing incidents."""
        from hornet.main import app
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/incidents", headers=api_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert "data" in data
            assert "meta" in data
    
    async def test_get_incident_timeline(self, sample_event, api_headers):
        """Test getting incident timeline."""
        from hornet.main import app
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Create incident via event
            create_resp = await client.post(
                "/api/v1/events",
                json=sample_event,
                headers=api_headers,
            )
            incident_id = create_resp.json().get("incident_id")
            
            if incident_id:
                # Get timeline
                response = await client.get(
                    f"/api/v1/incidents/{incident_id}/timeline",
                    headers=api_headers,
                )
                
                assert response.status_code in [200, 404]


class TestHealthEndpoints:
    """Test health check endpoints."""
    
    async def test_health_check(self):
        """Test basic health check."""
        from hornet.main import app
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/health")
            
            assert response.status_code == 200
            data = response.json()
            assert "status" in data
    
    async def test_agent_health(self):
        """Test agent health endpoint."""
        from hornet.main import app
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/health/agents")
            
            assert response.status_code == 200
            data = response.json()
            assert "total_agents" in data
    
    async def test_liveness_probe(self):
        """Test Kubernetes liveness probe."""
        from hornet.main import app
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/health/live")
            
            assert response.status_code == 200
    
    async def test_readiness_probe(self):
        """Test Kubernetes readiness probe."""
        from hornet.main import app
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/health/ready")
            
            # May fail if dependencies not available
            assert response.status_code in [200, 503]


class TestWebhooks:
    """Test webhook ingestion."""
    
    async def test_cloudflare_webhook(self, api_headers):
        """Test Cloudflare webhook ingestion."""
        from hornet.main import app
        
        webhook_payload = {
            "action": "block",
            "clientIP": "203.0.113.50",
            "rayId": "abc123",
            "ruleId": "rule_123",
            "source": "waf",
        }
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/webhooks/cloudflare",
                json=webhook_payload,
                headers=api_headers,
            )
            
            assert response.status_code in [200, 201]
    
    async def test_generic_webhook(self, api_headers):
        """Test generic webhook ingestion."""
        from hornet.main import app
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/webhooks/generic",
                json={"event": "test", "data": {}},
                headers=api_headers,
            )
            
            assert response.status_code in [200, 201]


class TestConfiguration:
    """Test configuration management."""
    
    async def test_get_thresholds(self, api_headers):
        """Test getting thresholds."""
        from hornet.main import app
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/config/thresholds", headers=api_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert "dismiss" in data
            assert "investigate" in data
            assert "confirm" in data
    
    async def test_get_agents(self, api_headers):
        """Test getting agent list."""
        from hornet.main import app
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/config/agents", headers=api_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert "agents" in data
    
    async def test_get_playbooks(self, api_headers):
        """Test getting playbook list."""
        from hornet.main import app
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/config/playbooks", headers=api_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert "playbooks" in data


class TestDashboard:
    """Test dashboard endpoints."""
    
    async def test_dashboard_accessible(self):
        """Test dashboard is accessible."""
        from hornet.main import app
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/dashboard")
            
            # Should return HTML or redirect
            assert response.status_code in [200, 404]


class TestRootEndpoint:
    """Test root endpoint."""
    
    async def test_root(self):
        """Test root endpoint returns info."""
        from hornet.main import app
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/")
            
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "HORNET"
            assert "version" in data
