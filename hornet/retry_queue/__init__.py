"""
HORNET Retry Queue and Dead Letter Queue
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from uuid import UUID, uuid4
from enum import Enum
import asyncio
import json
import structlog

logger = structlog.get_logger()


class RetryStatus(str, Enum):
    PENDING = "PENDING"
    RETRYING = "RETRYING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    DEAD_LETTERED = "DEAD_LETTERED"


@dataclass
class RetryItem:
    id: UUID = field(default_factory=uuid4)
    item_type: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    target: str = ""
    tenant_id: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_attempt: Optional[datetime] = None
    next_attempt: Optional[datetime] = None
    attempt_count: int = 0
    max_attempts: int = 5
    status: RetryStatus = RetryStatus.PENDING
    error_history: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class RetryQueue:
    BACKOFF_SECONDS = [0, 30, 120, 600, 3600]  # 0s, 30s, 2m, 10m, 1h
    
    def __init__(self, redis_client=None):
        self.redis = redis_client
        self._local_queue: Dict[str, RetryItem] = {}
        self._dlq: Dict[str, RetryItem] = {}
        self._handlers: Dict[str, Callable] = {}
        self._running = False
    
    def register_handler(self, item_type: str, handler: Callable):
        self._handlers[item_type] = handler
    
    async def enqueue(self, item_type: str, payload: Dict, target: str, tenant_id: str, max_attempts: int = 5, metadata: Dict = None) -> RetryItem:
        item = RetryItem(item_type=item_type, payload=payload, target=target, tenant_id=tenant_id, max_attempts=max_attempts, next_attempt=datetime.utcnow(), metadata=metadata or {})
        self._local_queue[str(item.id)] = item
        logger.info("retry_item_enqueued", item_id=str(item.id), item_type=item_type)
        return item
    
    async def process_item(self, item: RetryItem) -> bool:
        handler = self._handlers.get(item.item_type)
        if not handler:
            return False
        item.attempt_count += 1
        item.last_attempt = datetime.utcnow()
        item.status = RetryStatus.RETRYING
        try:
            result = await handler(item.payload, item.target, item.metadata)
            if result:
                item.status = RetryStatus.SUCCEEDED
                self._local_queue.pop(str(item.id), None)
                return True
            raise Exception("Handler returned False")
        except Exception as e:
            item.error_history.append({"attempt": item.attempt_count, "error": str(e), "timestamp": datetime.utcnow().isoformat()})
            if item.attempt_count >= item.max_attempts:
                item.status = RetryStatus.DEAD_LETTERED
                self._local_queue.pop(str(item.id), None)
                self._dlq[str(item.id)] = item
                logger.warning("retry_item_dead_lettered", item_id=str(item.id))
            else:
                backoff = self.BACKOFF_SECONDS[min(item.attempt_count, len(self.BACKOFF_SECONDS) - 1)]
                item.next_attempt = datetime.utcnow() + timedelta(seconds=backoff)
                item.status = RetryStatus.PENDING
            return False
    
    async def get_pending_items(self) -> List[RetryItem]:
        now = datetime.utcnow()
        return [i for i in self._local_queue.values() if i.status == RetryStatus.PENDING and i.next_attempt and i.next_attempt <= now]
    
    async def get_dlq_items(self, tenant_id: str = None) -> List[RetryItem]:
        items = list(self._dlq.values())
        return [i for i in items if not tenant_id or i.tenant_id == tenant_id]
    
    async def replay_dlq_item(self, item_id: str) -> bool:
        item = self._dlq.pop(item_id, None)
        if not item:
            return False
        item.status = RetryStatus.PENDING
        item.attempt_count = 0
        item.next_attempt = datetime.utcnow()
        item.error_history = []
        self._local_queue[str(item.id)] = item
        return True
    
    async def start_processor(self, interval_seconds: int = 10):
        self._running = True
        while self._running:
            try:
                for item in await self.get_pending_items():
                    await self.process_item(item)
            except Exception as e:
                logger.error("retry_processor_error", error=str(e))
            await asyncio.sleep(interval_seconds)
    
    def stop_processor(self):
        self._running = False
    
    def get_stats(self) -> Dict[str, Any]:
        return {"pending": len(self._local_queue), "dlq": len(self._dlq)}


retry_queue = RetryQueue()


async def webhook_retry_handler(payload: Dict, target: str, metadata: Dict) -> bool:
    import httpx
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(target, json=payload, headers=metadata.get("headers", {}))
            return resp.status_code < 400
    except:
        return False


retry_queue.register_handler("webhook", webhook_retry_handler)
