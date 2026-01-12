"""Test WebSocket support."""
import pytest
import asyncio
from hornet.websocket import ConnectionManager, WSMessage


@pytest.fixture
def manager():
    return ConnectionManager()


def test_ws_message_serialization():
    msg = WSMessage(
        event_type="test",
        timestamp="2024-01-01T00:00:00Z",
        data={"key": "value"},
    )
    
    json_str = msg.to_json()
    assert '"event_type": "test"' in json_str
    assert '"key": "value"' in json_str


def test_connection_count_empty(manager):
    counts = manager.get_connection_count()
    assert counts["total"] == 0
    assert counts["incident_subscriptions"] == 0
