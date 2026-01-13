"""
HORNET Event Bus
Redis Streams-based event routing and messaging.
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, Any, List, Optional, AsyncIterator
from uuid import UUID, uuid4
import json
import asyncio
import structlog

import redis.asyncio as redis

from hornet.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


@dataclass
class SwarmMessage:
    """Base message structure for inter-agent communication."""
    id: str
    timestamp: str
    event_id: str
    incident_id: str
    source: str
    target: Optional[str]
    message_type: str
    payload: Dict[str, Any]
    tenant_id: str
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SwarmMessage":
        return cls(**data)
    
    def serialize(self) -> Dict[str, str]:
        """Serialize for Redis stream."""
        return {
            "data": json.dumps(self.to_dict())
        }
    
    @classmethod
    def deserialize(cls, data: Dict[bytes, bytes]) -> "SwarmMessage":
        """Deserialize from Redis stream."""
        json_data = json.loads(data[b"data"].decode())
        return cls.from_dict(json_data)


class EventBus:
    """
    Redis Streams-based event bus for HORNET swarm communication.
    
    Provides:
    - Event ingestion stream
    - Per-incident message streams
    - Agent-specific subscription patterns
    - Message persistence for replay
    """
    
    # Stream names
    EVENTS_STREAM = "hornet:events"
    INCIDENTS_STREAM = "hornet:incidents"
    MESSAGES_STREAM_PREFIX = "hornet:incident:"
    AGENT_STREAM_PREFIX = "hornet:agent:"
    
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or settings.REDIS_URL
        self._redis: Optional[redis.Redis] = None
        self._consumer_group = "hornet_workers"
        self._consumer_name = f"worker_{uuid4().hex[:8]}"
    
    async def connect(self):
        """Establish Redis connection."""
        self._redis = redis.from_url(
            self.redis_url,
            encoding="utf-8",
            decode_responses=False,
        )
        
        # Create consumer groups if they don't exist
        try:
            await self._redis.xgroup_create(
                self.EVENTS_STREAM,
                self._consumer_group,
                id="0",
                mkstream=True,
            )
        except redis.ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise
        
        logger.info("event_bus_connected", redis_url=self.redis_url)
    
    async def disconnect(self):
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
    
    async def publish_event(self, event_data: Dict[str, Any]) -> str:
        """
        Publish a new security event to the events stream.
        Returns the stream message ID.
        """
        message_id = await self._redis.xadd(
            self.EVENTS_STREAM,
            {"data": json.dumps(event_data)},
        )
        
        logger.debug(
            "event_published",
            stream=self.EVENTS_STREAM,
            message_id=message_id,
            event_type=event_data.get("event_type"),
        )
        
        return message_id.decode() if isinstance(message_id, bytes) else message_id
    
    async def consume_events(self, count: int = 10, block_ms: int = 1000) -> List[Dict[str, Any]]:
        """
        Consume events from the events stream.
        Uses consumer groups for distributed processing.
        """
        messages = await self._redis.xreadgroup(
            groupname=self._consumer_group,
            consumername=self._consumer_name,
            streams={self.EVENTS_STREAM: ">"},
            count=count,
            block=block_ms,
        )
        
        events = []
        for stream_name, stream_messages in messages:
            for message_id, data in stream_messages:
                event_data = json.loads(data[b"data"])
                event_data["_stream_id"] = message_id.decode()
                events.append(event_data)
        
        return events
    
    async def ack_event(self, message_id: str):
        """Acknowledge event processing completion."""
        await self._redis.xack(
            self.EVENTS_STREAM,
            self._consumer_group,
            message_id,
        )
    
    async def publish_message(self, message: SwarmMessage):
        """Publish a swarm message to incident-specific stream."""
        stream_name = f"{self.MESSAGES_STREAM_PREFIX}{message.incident_id}"
        
        await self._redis.xadd(
            stream_name,
            message.serialize(),
            maxlen=1000,  # Keep last 1000 messages per incident
        )
        
        # Also publish to agent-specific stream if targeted
        if message.target:
            agent_stream = f"{self.AGENT_STREAM_PREFIX}{message.target}"
            await self._redis.xadd(
                agent_stream,
                message.serialize(),
                maxlen=100,
            )
    
    async def get_incident_messages(
        self,
        incident_id: str,
        since_id: str = "0",
        count: int = 100,
    ) -> List[SwarmMessage]:
        """Get messages for a specific incident."""
        stream_name = f"{self.MESSAGES_STREAM_PREFIX}{incident_id}"
        
        messages = await self._redis.xrange(
            stream_name,
            min=since_id,
            max="+",
            count=count,
        )
        
        return [
            SwarmMessage.deserialize(data)
            for _, data in messages
        ]
    
    async def subscribe_agent(self, agent_name: str) -> AsyncIterator[SwarmMessage]:
        """Subscribe to messages for a specific agent."""
        stream_name = f"{self.AGENT_STREAM_PREFIX}{agent_name}"
        last_id = "0"
        
        while True:
            messages = await self._redis.xread(
                {stream_name: last_id},
                count=10,
                block=1000,
            )
            
            for _, stream_messages in messages:
                for message_id, data in stream_messages:
                    last_id = message_id.decode()
                    yield SwarmMessage.deserialize(data)
    
    async def set_incident_state(self, incident_id: str, state: str):
        """Store incident state in Redis for quick access."""
        key = f"hornet:incident_state:{incident_id}"
        await self._redis.hset(key, mapping={
            "state": state,
            "updated_at": datetime.utcnow().isoformat(),
        })
        await self._redis.expire(key, 86400)  # 24 hour TTL
    
    async def get_incident_state(self, incident_id: str) -> Optional[Dict[str, str]]:
        """Get incident state from Redis."""
        key = f"hornet:incident_state:{incident_id}"
        data = await self._redis.hgetall(key)
        if data:
            return {k.decode(): v.decode() for k, v in data.items()}
        return None
    
    async def increment_token_usage(self, incident_id: str, tokens: int) -> int:
        """Atomically increment token usage for an incident."""
        key = f"hornet:incident_tokens:{incident_id}"
        return await self._redis.incrby(key, tokens)
    
    async def get_token_usage(self, incident_id: str) -> int:
        """Get current token usage for an incident."""
        key = f"hornet:incident_tokens:{incident_id}"
        value = await self._redis.get(key)
        return int(value) if value else 0
    
    async def acquire_lock(self, resource: str, ttl_seconds: int = 30) -> bool:
        """Acquire a distributed lock."""
        key = f"hornet:lock:{resource}"
        return await self._redis.set(
            key,
            self._consumer_name,
            nx=True,
            ex=ttl_seconds,
        )
    
    async def release_lock(self, resource: str):
        """Release a distributed lock."""
        key = f"hornet:lock:{resource}"
        current = await self._redis.get(key)
        if current and current.decode() == self._consumer_name:
            await self._redis.delete(key)
    
    async def get_queue_depth(self) -> int:
        """Get number of pending events in the stream."""
        info = await self._redis.xinfo_stream(self.EVENTS_STREAM)
        return info.get(b"length", 0)
    
    async def get_pending_count(self) -> int:
        """Get number of events pending acknowledgment."""
        info = await self._redis.xpending(
            self.EVENTS_STREAM,
            self._consumer_group,
        )
        return info[0] if info else 0



    # Pub/Sub channel for real-time dashboard updates
    REALTIME_CHANNEL = "hornet:realtime"

    async def publish_realtime(self, event_type: str, data: Dict[str, Any]):
        """Publish real-time update for dashboard WebSockets."""
        message = json.dumps({
            "type": event_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        })
        await self._redis.publish(self.REALTIME_CHANNEL, message)
        logger.debug("realtime_published", event_type=event_type)

    async def subscribe_realtime(self):
        """Subscribe to real-time updates channel."""
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(self.REALTIME_CHANNEL)
        return pubsub

class RateLimiter:
    """Token bucket rate limiter using Redis."""
    
    def __init__(self, redis_client: redis.Redis):
        self._redis = redis_client
    
    async def acquire(
        self,
        key: str,
        rate: float,
        capacity: int,
        tokens: int = 1,
    ) -> bool:
        """
        Attempt to acquire tokens from the bucket.
        
        Args:
            key: Unique identifier for the rate limit
            rate: Tokens per second refill rate
            capacity: Maximum bucket capacity
            tokens: Number of tokens to acquire
        
        Returns:
            True if tokens acquired, False if rate limited
        """
        now = asyncio.get_event_loop().time()
        bucket_key = f"hornet:ratelimit:{key}"
        
        # Lua script for atomic token bucket
        script = """
        local key = KEYS[1]
        local rate = tonumber(ARGV[1])
        local capacity = tonumber(ARGV[2])
        local now = tonumber(ARGV[3])
        local requested = tonumber(ARGV[4])
        
        local data = redis.call('HMGET', key, 'tokens', 'last_update')
        local tokens = tonumber(data[1]) or capacity
        local last_update = tonumber(data[2]) or now
        
        local elapsed = now - last_update
        tokens = math.min(capacity, tokens + elapsed * rate)
        
        if tokens >= requested then
            tokens = tokens - requested
            redis.call('HMSET', key, 'tokens', tokens, 'last_update', now)
            redis.call('EXPIRE', key, 3600)
            return 1
        else
            return 0
        end
        """
        
        result = await self._redis.eval(
            script,
            1,
            bucket_key,
            rate,
            capacity,
            now,
            tokens,
        )
        
        return bool(result)
