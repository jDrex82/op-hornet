"""Full pipeline integration tests."""
import pytest
from uuid import uuid4
from datetime import datetime

from hornet.coordinator import Coordinator, AgentRegistry, IncidentContext, FSMState
from hornet.playbooks import match_playbook, get_playbook, PLAYBOOKS
from hornet.mitre import get_technique, get_techniques_for_agent, get_coverage_score


class TestFullPipeline:
    """Test complete incident processing pipeline."""
    
    @pytest.fixture
    def coordinator(self):
        registry = AgentRegistry.create_default()
        return Coordinator(event_bus=None, agent_registry=registry)
    
    def test_create_context_from_event(self, coordinator):
        event = {
            "event_type": "auth.brute_force",
            "source": "test",
            "source_type": "test",
            "severity": "HIGH",
            "entities": [
                {"type": "ip", "value": "192.168.1.100"},
                {"type": "user", "value": "admin"},
            ],
            "raw_payload": {"failed_attempts": 50},
        }
        
        context = coordinator._create_context(event, "test-tenant")
        
        assert context.incident_id is not None
        assert context.tenant_id == "test-tenant"
        assert context.state == FSMState.DETECTION
        assert "ip" in context.entities
        assert "192.168.1.100" in context.entities["ip"]
    
    def test_state_transition(self, coordinator):
        context = IncidentContext(
            incident_id=uuid4(),
            tenant_id="test",
            state=FSMState.DETECTION,
        )
        
        # Valid transition
        result = coordinator._transition_state(context, FSMState.ENRICHMENT)
        assert result is True
        assert context.state == FSMState.ENRICHMENT
        
        # Invalid transition
        result = coordinator._transition_state(context, FSMState.EXECUTION)
        assert result is False
        assert context.state == FSMState.ENRICHMENT
    
    def test_token_budget_check(self, coordinator):
        context = IncidentContext(incident_id=uuid4(), tenant_id="test")
        
        context.tokens_used = 0
        assert coordinator._check_token_budget(context) == "OK"
        
        context.tokens_used = 40000  # 80%
        assert coordinator._check_token_budget(context) == "WARNING"
        
        context.tokens_used = 45000  # 90%
        assert coordinator._check_token_budget(context) == "FORCE_TRANSITION"
        
        context.tokens_used = 48000  # 96%
        assert coordinator._check_token_budget(context) == "CRITICAL"


class TestPlaybookMatching:
    """Test playbook selection."""
    
    def test_match_brute_force(self):
        matches = match_playbook("auth.brute_force")
        assert len(matches) > 0
        assert any(p.id == "PB-AUTH-001" for p in matches)
    
    def test_match_ransomware(self):
        matches = match_playbook("endpoint.ransomware")
        assert len(matches) > 0
        assert any(p.id == "PB-MALWARE-001" for p in matches)
    
    def test_match_phishing(self):
        matches = match_playbook("email.phishing")
        assert len(matches) > 0
    
    def test_no_match(self):
        matches = match_playbook("unknown.event.type")
        assert len(matches) == 0
    
    def test_get_specific_playbook(self):
        pb = get_playbook("PB-AUTH-001")
        assert pb is not None
        assert pb.name == "Brute Force Response"
    
    def test_playbook_count(self):
        assert len(PLAYBOOKS) >= 15  # Should have at least 15 playbooks


class TestMITREMappings:
    """Test MITRE ATT&CK integration."""
    
    def test_get_technique(self):
        tech = get_technique("T1566")
        assert tech is not None
        assert tech.name == "Phishing"
        assert "phisherman" in tech.detecting_agents
    
    def test_get_techniques_for_agent(self):
        techniques = get_techniques_for_agent("hunter")
        assert len(techniques) > 0
        assert any(t.id.startswith("T10") for t in techniques)
    
    def test_coverage_score(self):
        # Single agent
        score = get_coverage_score(["hunter"])
        assert 0 < score < 1
        
        # Multiple agents
        score_multi = get_coverage_score(["hunter", "endpoint", "gatekeeper", "netwatch"])
        assert score_multi > score


class TestAgentRegistry:
    """Test agent registry functionality."""
    
    @pytest.fixture
    def registry(self):
        return AgentRegistry.create_default()
    
    def test_registry_has_agents(self, registry):
        agents = registry.get_all()
        assert len(agents) >= 40  # Should have many agents
    
    def test_get_specific_agent(self, registry):
        router = registry.get("router")
        assert router is not None
        
        hunter = registry.get("hunter")
        assert hunter is not None
        
        oversight = registry.get("oversight")
        assert oversight is not None
    
    def test_get_nonexistent_agent(self, registry):
        agent = registry.get("nonexistent_agent")
        assert agent is None
    
    def test_all_agents_have_prompts(self, registry):
        for name, agent in registry.get_all().items():
            prompt = agent.get_system_prompt()
            assert prompt is not None
            assert len(prompt) > 50  # Should have meaningful prompt


class TestIncidentTimeline:
    """Test incident timeline tracking."""
    
    def test_add_timeline_event(self):
        context = IncidentContext(incident_id=uuid4(), tenant_id="test")
        
        context.add_timeline_event("test_event", agent="test_agent", details={"key": "value"})
        
        assert len(context.timeline) == 1
        assert context.timeline[0]["event"] == "test_event"
        assert context.timeline[0]["agent"] == "test_agent"
        assert context.timeline[0]["details"]["key"] == "value"
    
    def test_timeline_tracks_state(self):
        context = IncidentContext(incident_id=uuid4(), tenant_id="test", state=FSMState.DETECTION)
        context.add_timeline_event("detection_started")
        
        assert context.timeline[0]["state"] == "DETECTION"
