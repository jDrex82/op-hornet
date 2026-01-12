"""Test HORNET coordinator and FSM."""
import pytest
from uuid import uuid4
from hornet.coordinator import IncidentState, IncidentContext, TransitionGuard

@pytest.fixture
def incident_context():
    return IncidentContext(
        incident_id=uuid4(),
        tenant_id=uuid4(),
    )

def test_initial_state(incident_context):
    assert incident_context.state == IncidentState.IDLE

def test_detection_to_enrichment_guard_no_findings(incident_context):
    incident_context.state = IncidentState.DETECTION
    result, reason = TransitionGuard.detection_to_enrichment(incident_context)
    assert not result  # No findings yet

def test_state_config():
    from hornet.coordinator import STATE_CONFIG
    assert IncidentState.DETECTION in STATE_CONFIG
    assert STATE_CONFIG[IncidentState.DETECTION]["max_duration_ms"] == 15000
