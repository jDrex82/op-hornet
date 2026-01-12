"""Test metrics collection."""
import pytest
from hornet.metrics import MetricsCollector, INCIDENTS_TOTAL, AGENT_CALLS_TOTAL


@pytest.fixture
def collector():
    return MetricsCollector()


def test_record_incident_closed(collector):
    # Just verify it doesn't throw
    collector.record_incident_closed("tenant1", "HIGH", "RESOLVED", 60.5)


def test_record_agent_call(collector):
    collector.record_agent_call("hunter", "success", 1.5, tokens=500, model="haiku")
