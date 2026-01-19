"""
HORNET Event Dispatcher
Consumes events from Redis stream, routes to detection agents, creates incidents.

This is the nervous system - connects Edge Agent logs to the 56-agent swarm.
"""
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
from uuid import uuid4
import structlog

from hornet.config import get_settings
from hornet.event_bus import EventBus
from hornet.agents import get_agent, ALL_AGENTS
from hornet.agents.base import AgentContext, AgentOutput

logger = structlog.get_logger()
settings = get_settings()


# Detection agents that run on every event
DETECTION_SQUAD = [
    "hunter",      # Threat pattern matching
    "sentinel",    # Real-time alert triage
    "behavioral",  # Baseline deviation
    "netwatch",    # Network anomaly
    "endpoint",    # Endpoint telemetry
]

# Minimum confidence to create an incident
DETECTION_THRESHOLD = 0.3


class EventDispatcher:
    """
    Consumes events from Redis stream, runs detection agents, creates incidents.
    
    Flow:
    1. Pull event from hornet:events stream
    2. Run detection squad in parallel
    3. If any agent confidence > threshold → create incident
    4. Coordinator takes over FSM processing
    5. Ack event
    """
    
    # Dispatcher gets its own consumer group - workers use "hornet_workers"
    CONSUMER_GROUP = "hornet_dispatcher"
    
    def __init__(self, event_bus: EventBus, coordinator=None):
        self.event_bus = event_bus
        self.coordinator = coordinator
        self._running = False
        self._processed_count = 0
        self._incident_count = 0
        self._detection_agents = []
        self._redis = None
        self._consumer_name = f"dispatcher_{uuid4().hex[:8]}"
        
    async def initialize(self):
        """Load detection agents and create consumer group."""
        # Create our own consumer group for the dispatcher
        import redis.asyncio as redis
        self._redis = redis.from_url(
            self.event_bus.redis_url,
            encoding="utf-8",
            decode_responses=False,
        )
        
        # Create dispatcher consumer group (separate from workers)
        try:
            await self._redis.xgroup_create(
                self.event_bus.EVENTS_STREAM,
                self.CONSUMER_GROUP,
                id="0",  # Start from beginning
                mkstream=True,
            )
            logger.info("dispatcher_consumer_group_created", group=self.CONSUMER_GROUP)
        except Exception as e:
            if "BUSYGROUP" not in str(e):
                raise
            logger.info("dispatcher_consumer_group_exists", group=self.CONSUMER_GROUP)
        
        # Load detection agents
        for agent_name in DETECTION_SQUAD:
            agent = get_agent(agent_name)
            if agent:
                self._detection_agents.append((agent_name, agent))
                logger.info("dispatcher_agent_loaded", agent=agent_name)
            else:
                logger.warning("dispatcher_agent_missing", agent=agent_name)
        
        logger.info("dispatcher_initialized", 
                   detection_agents=len(self._detection_agents),
                   threshold=DETECTION_THRESHOLD,
                   consumer_group=self.CONSUMER_GROUP)
    
    async def start(self):
        """Start the event consumption loop."""
        if self._running:
            logger.warning("dispatcher_already_running")
            return
            
        self._running = True
        logger.info("dispatcher_started")
        
        while self._running:
            try:
                await self._process_batch()
            except Exception as e:
                logger.error("dispatcher_batch_error", error=str(e))
                await asyncio.sleep(1)  # Back off on error
    
    async def stop(self):
        """Stop the dispatcher gracefully."""
        self._running = False
        if self._redis:
            await self._redis.close()
        logger.info("dispatcher_stopped", 
                   processed=self._processed_count,
                   incidents=self._incident_count)
    
    async def _process_batch(self):
        """Process a batch of events from the stream using dispatcher's consumer group."""
        import json
        
        messages = await self._redis.xreadgroup(
            groupname=self.CONSUMER_GROUP,
            consumername=self._consumer_name,
            streams={self.event_bus.EVENTS_STREAM: ">"},
            count=10,
            block=1000,
        )
        
        if not messages:
            return
        
        for stream_name, stream_messages in messages:
            for message_id, data in stream_messages:
                try:
                    event_data = json.loads(data[b"data"])
                    event_data["_stream_id"] = message_id.decode()
                    
                    await self._process_event(event_data)
                    
                    # Ack with our consumer group
                    await self._redis.xack(
                        self.event_bus.EVENTS_STREAM,
                        self.CONSUMER_GROUP,
                        message_id,
                    )
                    self._processed_count += 1
                except Exception as e:
                    logger.error("dispatcher_event_error", 
                               message_id=message_id.decode() if isinstance(message_id, bytes) else message_id,
                               error=str(e))
    
    async def _process_event(self, event: Dict[str, Any]):
        """Run detection agents on a single event."""
        event_id = event.get("id", str(uuid4()))
        event_type = event.get("event_type", "unknown")
        tenant_id = event.get("tenant_id", "default")
        
        logger.info("dispatcher_processing_event",
                   event_id=event_id,
                   event_type=event_type,
                   source=event.get("source"))
        
        # Build context for agents
        context = AgentContext(
            incident_id=uuid4(),  # Provisional - may not become incident
            tenant_id=tenant_id,
            state="DETECTION",
            event_data=event,
            events=[event],
            findings=[],
            entities=self._extract_entities(event),
            token_budget=50000,  # Detection budget
            tokens_used=0,
        )
        
        # Run detection squad in parallel
        detection_results = await self._run_detection_squad(context)
        
        # Evaluate results
        max_confidence = 0.0
        triggering_agent = None
        all_findings = []
        
        for agent_name, output in detection_results:
            if output is None:
                continue
            all_findings.append(output)
            if output.confidence > max_confidence:
                max_confidence = output.confidence
                triggering_agent = agent_name
        
        logger.info("dispatcher_detection_complete",
                   event_id=event_id,
                   max_confidence=max_confidence,
                   triggering_agent=triggering_agent,
                   findings_count=len(all_findings))
        
        # Create incident if threshold exceeded
        if max_confidence >= DETECTION_THRESHOLD:
            await self._create_incident(event, all_findings, max_confidence, triggering_agent)
        else:
            logger.debug("dispatcher_event_dismissed",
                        event_id=event_id,
                        confidence=max_confidence,
                        threshold=DETECTION_THRESHOLD)
    
    async def _run_detection_squad(self, context: AgentContext) -> List[tuple]:
        """Run all detection agents in parallel."""
        tasks = []
        
        for agent_name, agent in self._detection_agents:
            tasks.append(self._run_agent_safe(agent_name, agent, context))
        
        results = await asyncio.gather(*tasks)
        return list(zip([name for name, _ in self._detection_agents], results))
    
    async def _run_agent_safe(self, agent_name: str, agent, context: AgentContext) -> Optional[AgentOutput]:
        """Run a single agent with error handling."""
        try:
            output = await asyncio.wait_for(
                agent.process(context),
                timeout=10.0  # 10 second timeout per agent
            )
            logger.debug("dispatcher_agent_complete",
                        agent=agent_name,
                        confidence=output.confidence)
            return output
        except asyncio.TimeoutError:
            logger.warning("dispatcher_agent_timeout", agent=agent_name)
            return None
        except Exception as e:
            logger.error("dispatcher_agent_error", agent=agent_name, error=str(e))
            return None
    
    async def _create_incident(self, event: Dict[str, Any], findings: List[AgentOutput],
                               confidence: float, triggering_agent: str):
        """Create an incident and hand off to Coordinator."""
        event_id = event.get("id", str(uuid4()))
        tenant_id = event.get("tenant_id", "default")
        
        logger.info("dispatcher_creating_incident",
                   event_id=event_id,
                   confidence=confidence,
                   triggering_agent=triggering_agent,
                   findings_count=len(findings))
        
        if self.coordinator:
            # Use Coordinator to create and process incident
            incident_context = await self.coordinator.create_incident(
                tenant_id=tenant_id,
                event_id=event_id,
                event_data=event,
                entities=event.get("entities", []),
            )
            
            # Inject detection findings so enrichment doesn't redo work
            for finding in findings:
                incident_context.findings.append(finding)
            
            incident_context.confidence = confidence
            incident_context.add_timeline_event(
                "detection_triggered",
                agent=triggering_agent,
                details={
                    "confidence": confidence,
                    "detection_agents": len(findings),
                }
            )
            
            self._incident_count += 1
            
            logger.info("dispatcher_incident_created",
                       incident_id=str(incident_context.incident_id),
                       state=incident_context.state.value)
            
            # Publish real-time update
            await self.event_bus.publish_realtime("incident_created", {
                "incident_id": str(incident_context.incident_id),
                "event_type": event.get("event_type"),
                "confidence": confidence,
                "triggering_agent": triggering_agent,
            })
        else:
            logger.warning("dispatcher_no_coordinator", event_id=event_id)
    
    def _extract_entities(self, event: Dict[str, Any]) -> Dict[str, set]:
        """Extract entities from event for agent context."""
        entities = {}
        
        for entity in event.get("entities", []):
            etype = entity.get("type", "unknown")
            value = entity.get("value", "")
            if etype not in entities:
                entities[etype] = set()
            entities[etype].add(value)
        
        # Also extract from common fields
        if "source_ip" in event:
            entities.setdefault("ip", set()).add(event["source_ip"])
        if "dest_ip" in event:
            entities.setdefault("ip", set()).add(event["dest_ip"])
        if "user" in event:
            entities.setdefault("user", set()).add(event["user"])
        if "hostname" in event:
            entities.setdefault("hostname", set()).add(event["hostname"])
        
        return entities
    
    @property
    def stats(self) -> Dict[str, Any]:
        """Get dispatcher statistics."""
        return {
            "running": self._running,
            "processed_events": self._processed_count,
            "incidents_created": self._incident_count,
            "detection_agents": len(self._detection_agents),
            "threshold": DETECTION_THRESHOLD,
            "consumer_group": self.CONSUMER_GROUP,
        }


# Singleton instance
_dispatcher: Optional[EventDispatcher] = None


async def get_dispatcher(event_bus: EventBus = None, coordinator=None) -> EventDispatcher:
    """Get or create the dispatcher singleton."""
    global _dispatcher
    
    if _dispatcher is None:
        if event_bus is None:
            raise ValueError("event_bus required for first initialization")
        _dispatcher = EventDispatcher(event_bus, coordinator)
        await _dispatcher.initialize()
    
    return _dispatcher


async def start_dispatcher(event_bus: EventBus, coordinator=None):
    """Start the dispatcher as a background task."""
    dispatcher = await get_dispatcher(event_bus, coordinator)
    asyncio.create_task(dispatcher.start())
    logger.info("dispatcher_background_started")
    return dispatcher
