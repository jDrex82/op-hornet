"""Test action executor."""
import pytest
from uuid import uuid4
from datetime import datetime
from hornet.executor import ActionExecutor, ActionRequest, ExecutionStatus


@pytest.fixture
def executor():
    return ActionExecutor()


def test_executor_unknown_action(executor):
    import asyncio
    
    request = ActionRequest(
        action_id="test-1",
        incident_id=uuid4(),
        action_type="unknown_action",
        target="test",
        parameters={},
        risk_level="LOW",
        justification="Test",
        rollback_plan={},
        approved_by="test",
        approved_at=datetime.utcnow(),
    )
    
    result = asyncio.get_event_loop().run_until_complete(executor.execute_action(request))
    
    assert result.status == ExecutionStatus.FAILED
    assert "Unknown action type" in result.error_message


def test_executor_notification_action(executor):
    import asyncio
    
    request = ActionRequest(
        action_id="test-2",
        incident_id=uuid4(),
        action_type="notify_team",
        target="security",
        parameters={"message": "Test"},
        risk_level="NONE",
        justification="Test notification",
        rollback_plan={},
        approved_by="test",
        approved_at=datetime.utcnow(),
    )
    
    result = asyncio.get_event_loop().run_until_complete(executor.execute_action(request))
    
    assert result.status == ExecutionStatus.COMPLETED
    assert result.connector_used == "notification"
