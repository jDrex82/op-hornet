"""
HORNET Queue System
Retry queue with dead letter queue (DLQ) for webhook deliveries.
"""
import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from uuid import UUID, uuid4
from enum import Enum
import structlog

logger = structlog.get_logger()


class JobStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    DEAD = "DEAD"


@dataclass
class RetryJob:
    id: UUID = field(default_factory=uuid4)
    job_type: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    target_url: str = ""
    tenant_id: str = ""
    attempts: int = 0
    max_attempts: int = 5
    status: JobStatus = JobStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    scheduled_at: datetime = field(default_factory=datetime.utcnow)
    last_attempt_at: Optional[datetime] = None
    last_error: Optional[str] = None
    error_history: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id), "job_type": self.job_type, "payload": self.payload,
            "target_url": self.target_url, "tenant_id": self.tenant_id,
            "attempts": self.attempts, "max_attempts": self.max_attempts,
            "status": self.status.value, "created_at": self.created_at.isoformat(),
            "scheduled_at": self.scheduled_at.isoformat(), "last_error": self.last_error,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RetryJob":
        return cls(
            id=UUID(data["id"]), job_type=data["job_type"], payload=data["payload"],
            target_url=data["target_url"], tenant_id=data["tenant_id"],
            attempts=data["attempts"], max_attempts=data["max_attempts"],
            status=JobStatus(data["status"]), created_at=datetime.fromisoformat(data["created_at"]),
            scheduled_at=datetime.fromisoformat(data["scheduled_at"]), last_error=data.get("last_error"),
        )


class RetryQueue:
    RETRY_DELAYS = [1, 5, 30, 120, 600]
    QUEUE_KEY = "hornet:retry_queue"
    DLQ_KEY = "hornet:dlq"

    def __init__(self, redis_client=None):
        self.redis = redis_client
        self._handlers: Dict[str, Callable] = {}
        self._running = False

    def register_handler(self, job_type: str, handler: Callable):
        self._handlers[job_type] = handler

    async def enqueue(self, job: RetryJob) -> str:
        if self.redis:
            score = job.scheduled_at.timestamp()
            await self.redis.zadd(self.QUEUE_KEY, {json.dumps(job.to_dict()): score})
        return str(job.id)

    async def schedule_retry(self, job: RetryJob, error: str):
        job.attempts += 1
        job.last_attempt_at = datetime.utcnow()
        job.last_error = error
        job.error_history.append({"attempt": job.attempts, "error": error, "timestamp": datetime.utcnow().isoformat()})
        
        if job.attempts >= job.max_attempts:
            job.status = JobStatus.DEAD
            if self.redis:
                await self.redis.lpush(self.DLQ_KEY, json.dumps(job.to_dict()))
            logger.warning("job_moved_to_dlq", job_id=str(job.id))
            return
        
        delay = self.RETRY_DELAYS[min(job.attempts - 1, len(self.RETRY_DELAYS) - 1)]
        job.scheduled_at = datetime.utcnow() + timedelta(seconds=delay)
        job.status = JobStatus.PENDING
        await self.enqueue(job)

    async def get_dlq_jobs(self, limit: int = 100) -> List[RetryJob]:
        if not self.redis:
            return []
        items = await self.redis.lrange(self.DLQ_KEY, 0, limit - 1)
        return [RetryJob.from_dict(json.loads(item)) for item in items]

    async def retry_dlq_job(self, job_id: str) -> bool:
        for job in await self.get_dlq_jobs(1000):
            if str(job.id) == job_id:
                job.attempts = 0
                job.status = JobStatus.PENDING
                job.scheduled_at = datetime.utcnow()
                await self.enqueue(job)
                await self.redis.lrem(self.DLQ_KEY, 1, json.dumps(job.to_dict()))
                return True
        return False

    async def process_jobs(self):
        self._running = True
        while self._running:
            try:
                if not self.redis:
                    await asyncio.sleep(1)
                    continue
                now = datetime.utcnow().timestamp()
                jobs = await self.redis.zrangebyscore(self.QUEUE_KEY, "-inf", now, start=0, num=10)
                for job_data in jobs:
                    await self.redis.zrem(self.QUEUE_KEY, job_data)
                    job = RetryJob.from_dict(json.loads(job_data))
                    handler = self._handlers.get(job.job_type)
                    if not handler:
                        continue
                    try:
                        await handler(job)
                        logger.info("job_completed", job_id=str(job.id))
                    except Exception as e:
                        await self.schedule_retry(job, str(e))
                if not jobs:
                    await asyncio.sleep(1)
            except Exception as e:
                logger.error("retry_queue_error", error=str(e))
                await asyncio.sleep(5)

    async def stop(self):
        self._running = False

    async def get_stats(self) -> Dict[str, Any]:
        if not self.redis:
            return {"pending": 0, "dlq": 0}
        return {"pending": await self.redis.zcard(self.QUEUE_KEY), "dlq": await self.redis.llen(self.DLQ_KEY)}


class WebhookDelivery:
    def __init__(self, queue: RetryQueue):
        self.queue = queue
        queue.register_handler("webhook", self._deliver)

    async def send(self, url: str, payload: Dict, tenant_id: str, secret: str = None) -> str:
        import hmac, hashlib
        job = RetryJob(job_type="webhook", target_url=url, payload=payload, tenant_id=tenant_id)
        if secret:
            sig = hmac.new(secret.encode(), json.dumps(payload, sort_keys=True).encode(), hashlib.sha256).hexdigest()
            job.payload["_signature"] = f"sha256={sig}"
        return await self.queue.enqueue(job)

    async def _deliver(self, job: RetryJob):
        import httpx
        headers = {"Content-Type": "application/json", "X-Hornet-Delivery": str(job.id)}
        if "_signature" in job.payload:
            headers["X-Hornet-Signature"] = job.payload.pop("_signature")
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(job.target_url, json=job.payload, headers=headers)
            resp.raise_for_status()


retry_queue = RetryQueue()
webhook_delivery = WebhookDelivery(retry_queue)
