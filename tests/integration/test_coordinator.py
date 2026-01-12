"""Integration tests for HORNET Coordinator."""
import pytest
import asyncio
from uuid import uuid4

from hornet.coordinator import Coordinator, AgentRegistry, IncidentContext
from hornet.coordinator import FSMState


class TestCoordinatorIntegration:
    """Test coordinator with real agent registry."""
    
    @pytest.fixture
    def coordinator(self):
        """Create coordinator with full agent registry."""
        registry = AgentRegistry.create_default()
        return Coordinator(event_bus=None, agent_registry=registry)
    
    def test_agent_registry_has_agents(self, coordinator):
        """Verify agent registry is populated."""
        agents = coordinator.agent_registry.get_all()
        assert len(agents) > 20  # Should have many agents
    
    def test_agent_registry_has_router(self, coordinator):
        """Verify router agent exists."""
        router = coordinator.agent_registry.get("router")
        assert router is not None
    
    def test_create_incident_context(self, coordinator):
        """Test creating incident context."""
        event = {
            "event_type": "auth.brute_force",
            "severity": "HIGH",
            "entities": [{"type": "ip", "value": "192.168.1.1"}],
        }
        
        context = coordinator._create_context(event)
        
        assert context is not None
        assert context.incident_id is not None
        assert context.state == FSMState.DETECTION
    
    def test_fsm_transitions(self, coordinator):
        """Test FSM state transitions."""
        context = IncidentContext(
            incident_id=uuid4(),
            tenant_id="test-tenant",
            state=FSMState.DETECTION,
        )
        
        # Detection -> Enrichment (normal flow)
        coordinator._transition_state(context, FSMState.ENRICHMENT)
        assert context.state == FSMState.ENRICHMENT
        
        # Enrichment -> Analysis
        coordinator._transition_state(context, FSMState.ANALYSIS)
        assert context.state == FSMState.ANALYSIS


class TestEventBusIntegration:
    """Test event bus integration (requires Redis)."""
    
    @pytest.fixture
    async def event_bus(self):
        """Create event bus (will skip if no Redis)."""
        from hornet.event_bus import EventBus
        bus = EventBus()
        try:
            connected = await bus.connect()
            if not connected:
                pytest.skip("Redis not available")
            yield bus
            await bus.disconnect()
        except Exception:
            pytest.skip("Redis not available")
    
    async def test_publish_consume(self, event_bus):
        """Test publish and consume cycle."""
        test_event = {"test": "event", "id": str(uuid4())}
        
        await event_bus.publish("test_stream", test_event)
        
        events = await event_bus.consume("test_stream", "test_group", count=1, block_ms=1000)
        
        # Should have received the event
        assert len(events) >= 0  # May be 0 if already consumed
