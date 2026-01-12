"""Test retry queue and DLQ."""
import pytest
from datetime import datetime
from hornet.retry_queue import RetryQueue, RetryItem, RetryStatus


class TestRetryQueue:
    @pytest.fixture
    def queue(self):
        return RetryQueue()
    
    @pytest.mark.asyncio
    async def test_enqueue(self, queue):
        item = await queue.enqueue(
            item_type="webhook",
            payload={"test": "data"},
            target="https://example.com/webhook",
            tenant_id="test-tenant",
        )
        assert item.id is not None
        assert item.status == RetryStatus.PENDING
        assert item.attempt_count == 0
    
    @pytest.mark.asyncio
    async def test_get_pending_items(self, queue):
        await queue.enqueue("webhook", {}, "target", "tenant")
        items = await queue.get_pending_items()
        assert len(items) >= 1
    
    @pytest.mark.asyncio
    async def test_process_moves_to_dlq_after_max_attempts(self, queue):
        async def failing_handler(payload, target, metadata):
            return False
        
        queue.register_handler("test", failing_handler)
        item = await queue.enqueue("test", {}, "target", "tenant", max_attempts=1)
        await queue.process_item(item)
        
        dlq_items = await queue.get_dlq_items()
        assert any(str(i.id) == str(item.id) for i in dlq_items)
    
    @pytest.mark.asyncio
    async def test_replay_dlq_item(self, queue):
        queue._dlq["test-id"] = RetryItem(item_type="test", target="target", tenant_id="tenant")
        success = await queue.replay_dlq_item("test-id")
        assert success is True
        assert "test-id" not in queue._dlq
    
    def test_get_stats(self, queue):
        stats = queue.get_stats()
        assert "pending" in stats
        assert "dlq" in stats
