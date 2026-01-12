"""
HORNET Background Worker
Process events from the queue.
"""
import asyncio
import structlog
from hornet.config import get_settings
from hornet.event_bus import EventBus
from hornet.coordinator import Coordinator, AgentRegistry

logger = structlog.get_logger()
settings = get_settings()


async def process_events():
    """Main event processing loop."""
    event_bus = EventBus()
    await event_bus.connect()
    
    agent_registry = AgentRegistry.create_default()
    coordinator = Coordinator(event_bus, agent_registry)
    
    logger.info("worker_started", agents=len(agent_registry.get_all()))
    
    while True:
        try:
            events = await event_bus.consume_events(count=10, block_ms=5000)
            
            for event_data in events:
                stream_id = event_data.pop("_stream_id", None)
                
                try:
                    from uuid import UUID, uuid4
                    await coordinator.create_incident(
                        tenant_id=UUID(event_data.get("tenant_id", str(uuid4()))),
                        event_id=UUID(event_data.get("id", str(uuid4()))),
                        event_data=event_data,
                        entities=event_data.get("entities", []),
                    )
                    
                    if stream_id:
                        await event_bus.ack_event(stream_id)
                        
                except Exception as e:
                    logger.error("event_processing_failed", event_id=event_data.get("id"), error=str(e))
            
            # Check for timeouts
            await coordinator.check_timeouts()
            
        except Exception as e:
            logger.error("worker_error", error=str(e))
            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(process_events())
