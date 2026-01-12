"""Test HORNET agents."""
import pytest
from uuid import uuid4
from hornet.agents.base import AgentContext
from hornet.agents.detection import HunterAgent, GatekeeperAgent
from hornet.agents.meta import RouterAgent

@pytest.fixture
def sample_context():
    return AgentContext(
        incident_id=uuid4(),
        tenant_id=uuid4(),
        event_id=uuid4(),
        event_data={
            "event_type": "auth.brute_force",
            "source": "test",
            "severity": "MEDIUM",
            "raw_payload": {"source_ip": "192.168.1.100", "user": "admin"},
        },
        entities=[
            {"type": "ip", "value": "192.168.1.100"},
            {"type": "user", "value": "admin"},
        ],
    )

def test_router_stage1_classify():
    router = RouterAgent()
    result = router.stage1_classify("auth.brute_force")
    assert result is not None
    assert result["classification"]["domain"] == "auth"
    assert "gatekeeper" in result["activated_agents"]

def test_router_unknown_event():
    router = RouterAgent()
    result = router.stage1_classify("unknown.event.type")
    assert result is None

def test_hunter_agent_init():
    hunter = HunterAgent()
    assert hunter.name == "hunter"
    assert hunter.max_findings == 3

def test_gatekeeper_agent_init():
    gk = GatekeeperAgent()
    assert gk.name == "gatekeeper"
    assert "haiku" in gk.model
