"""
HORNET Background Worker
Smart event processing with detection scoring.

This is the production-ready worker that:
1. Consumes events from Redis stream
2. Runs detection agents in parallel to score events
3. Only creates incidents when confidence > threshold
4. Scales horizontally via replicas
"""
import asyncio
import structlog
from uuid import UUID, uuid4
from typing import Dict, Any, List, Optional

from hornet.config import get_settings
from hornet.event_bus import EventBus
from hornet.coordinator import Coordinator, AgentRegistry
from hornet.db import set_tenant_context, clear_tenant_context
from hornet.agents import get_agent
from hornet.agents.base import AgentContext, AgentOutput

logger = structlog.get_logger()
settings = get_settings()


# Detection squad - these agents score every event
DETECTION_SQUAD = [
    "hunter",      # Threat pattern matching
    "sentinel",    # Real-time alert triage
    "behavioral",  # Baseline deviation
    "netwatch",    # Network anomaly
    "endpoint",    # Endpoint telemetry
]

# Minimum confidence to create an incident
DETECTION_THRESHOLD = 0.3


def safe_uuid(value, default=None):
    """Safely convert to UUID, return default if invalid."""
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except (ValueError, TypeError):
        return default or uuid4()


class SmartWorker:
    """
    Production worker that does detection scoring before incident creation.
    
    Flow:
    1. Consume event from stream
    2. Run detection squad in parallel (5 agents)
    3. If max confidence >= threshold → create incident
    4. Otherwise dismiss event
    5. Ack event
    """
    
    def __init__(self):
        self.event_bus: Optional[EventBus] = None
        self.coordinator: Optional[Coordinator] = None
        self.agent_registry: Optional[AgentRegistry] = None
        self._detection_agents: List[tuple] = []
        self._running = False
        self._processed_count = 0
        self._incident_count = 0
        self._dismissed_count = 0
    
    async def initialize(self):
        """Initialize connections and load agents."""
        # Connect to event bus
        self.event_bus = EventBus()
        await self.event_bus.connect()
        
        # Load all agents
        self.agent_registry = AgentRegistry.create_default()
        
        # Initialize coordinator
        self.coordinator = Coordinator(
            event_bus=self.event_bus,
            agent_registry=self.agent_registry,
        )
        
        # Load detection agents
        for agent_name in DETECTION_SQUAD:
            agent = get_agent(agent_name)
            if agent:
                self._detection_agents.append((agent_name, agent))
                logger.info("worker_detection_agent_loaded", agent=agent_name)
            else:
                logger.warning("worker_detection_agent_missing", agent=agent_name)
        
        logger.info("smart_worker_initialized",
                   total_agents=len(self.agent_registry.get_all()),
                   detection_agents=len(self._detection_agents),
                   threshold=DETECTION_THRESHOLD)
    
    async def run(self):
        """Main processing loop."""
        self._running = True
        logger.info("smart_worker_started")
        
        while self._running:
            try:
                events = await self.event_bus.consume_events(count=10, block_ms=5000)
                
                for event_data in events:
                    stream_id = event_data.pop("_stream_id", None)
                    try:
                        await self._process_event(event_data)
                        if stream_id:
                            await self.event_bus.ack_event(stream_id)
                        self._processed_count += 1
                    except Exception as e:
                        logger.error("worker_event_failed",
                                   event_id=event_data.get("id"),
                                   error=str(e))
                
                # Check for timed-out incidents periodically
                await self.coordinator.check_timeouts()
                
            except Exception as e:
                logger.error("worker_loop_error", error=str(e))
                await asyncio.sleep(1)
    
    async def _process_event(self, event_data: Dict[str, Any]):
        """Process a single event with detection scoring."""
        event_id = safe_uuid(event_data.get("id"))
        tenant_id = safe_uuid(event_data.get("tenant_id"))
        event_type = event_data.get("event_type", "unknown")
        
        # Set tenant context for DB operations
        if tenant_id:
            set_tenant_context(str(tenant_id))
        
        try:
            logger.info("worker_processing_event",
                       event_id=str(event_id),
                       event_type=event_type)
            
            # Build context for detection agents
            context = AgentContext(
                incident_id=uuid4(),  # Provisional
                tenant_id=str(tenant_id) if tenant_id else "default",
                state="DETECTION",
                event_data=event_data,
                events=[event_data],
                findings=[],
                entities=self._extract_entities(event_data),
                token_budget=50000,
                tokens_used=0,
            )
            
            # Run detection squad
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
            
            logger.info("worker_detection_complete",
                       event_id=str(event_id),
                       max_confidence=max_confidence,
                       triggering_agent=triggering_agent,
                       findings_count=len(all_findings))
            
            # Create incident if threshold exceeded
            if max_confidence >= DETECTION_THRESHOLD:
                await self._create_incident(
                    event_data, tenant_id, event_id,
                    all_findings, max_confidence, triggering_agent
                )
                self._incident_count += 1
            else:
                logger.debug("worker_event_dismissed",
                           event_id=str(event_id),
                           confidence=max_confidence)
                self._dismissed_count += 1
                
        finally:
            clear_tenant_context()
    
    async def _run_detection_squad(self, context: AgentContext) -> List[tuple]:
        """Run detection agents in parallel."""
        tasks = []
        for agent_name, agent in self._detection_agents:
            tasks.append(self._run_agent_safe(agent_name, agent, context))
        
        results = await asyncio.gather(*tasks)
        return list(zip([name for name, _ in self._detection_agents], results))
    
    async def _run_agent_safe(self, agent_name: str, agent, context: AgentContext) -> Optional[AgentOutput]:
        """Run agent with timeout and error handling."""
        try:
            output = await asyncio.wait_for(
                agent.process(context),
                timeout=10.0
            )
            logger.debug("worker_agent_complete",
                        agent=agent_name,
                        confidence=output.confidence)
            return output
        except asyncio.TimeoutError:
            logger.warning("worker_agent_timeout", agent=agent_name)
            return None
        except Exception as e:
            logger.error("worker_agent_error", agent=agent_name, error=str(e))
            return None
    
    async def _create_incident(self, event_data: Dict[str, Any],
                               tenant_id: UUID, event_id: UUID,
                               findings: List[AgentOutput],
                               confidence: float, triggering_agent: str):
        """Create incident and hand off to coordinator."""
        logger.info("worker_creating_incident",
                   event_id=str(event_id),
                   confidence=confidence,
                   triggering_agent=triggering_agent)
        
        incident_context = await self.coordinator.create_incident(
            tenant_id=tenant_id,
            event_id=event_id,
            event_data=event_data,
            entities=event_data.get("entities", []),
        )
        
        # Inject detection findings
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
        
        logger.info("worker_incident_created",
                   incident_id=str(incident_context.incident_id),
                   state=incident_context.state.value)
    
    def _extract_entities(self, event: Dict[str, Any]) -> Dict[str, set]:
        """Extract entities from event."""
        entities = {}
        
        for entity in event.get("entities", []):
            etype = entity.get("type", "unknown")
            value = entity.get("value", "")
            if etype not in entities:
                entities[etype] = set()
            entities[etype].add(value)
        
        # Extract from common fields
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
        """Get worker statistics."""
        return {
            "processed": self._processed_count,
            "incidents": self._incident_count,
            "dismissed": self._dismissed_count,
            "detection_agents": len(self._detection_agents),
            "threshold": DETECTION_THRESHOLD,
        }


async def main():
    """Entry point for worker process."""
    worker = SmartWorker()
    await worker.initialize()
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
