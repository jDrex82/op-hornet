"""
HORNET Coordinator
FSM-based incident coordination with agent orchestration.
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from datetime import datetime
from uuid import UUID
import asyncio
from typing import Dict, Any, List, Optional, Set
from uuid import UUID, uuid4
from enum import Enum
import asyncio
import structlog

from hornet.repository import incident_repo
from hornet.config import get_settings
from hornet.agents import ALL_AGENTS, get_agent
from hornet.agents.base import AgentContext, AgentOutput

logger = structlog.get_logger()
settings = get_settings()


class FSMState(str, Enum):
    IDLE = "IDLE"
    DETECTION = "DETECTION"
    ENRICHMENT = "ENRICHMENT"
    ANALYSIS = "ANALYSIS"
    PROPOSAL = "PROPOSAL"
    OVERSIGHT = "OVERSIGHT"
    EXECUTION = "EXECUTION"
    ESCALATED = "ESCALATED"
    CLOSED = "CLOSED"
    ERROR = "ERROR"


STATE_TIMEOUTS = {
    FSMState.DETECTION: 15,
    FSMState.ENRICHMENT: 10,
    FSMState.ANALYSIS: 30,
    FSMState.PROPOSAL: 20,
    FSMState.OVERSIGHT: 30,
    FSMState.EXECUTION: 60,
    FSMState.ESCALATED: 1800,
}


VALID_TRANSITIONS = {
    FSMState.IDLE: {FSMState.DETECTION},
    FSMState.DETECTION: {FSMState.ENRICHMENT, FSMState.CLOSED, FSMState.ESCALATED},
    FSMState.ENRICHMENT: {FSMState.ANALYSIS, FSMState.ESCALATED},
    FSMState.ANALYSIS: {FSMState.PROPOSAL, FSMState.CLOSED, FSMState.ESCALATED},
    FSMState.PROPOSAL: {FSMState.OVERSIGHT, FSMState.CLOSED, FSMState.ESCALATED},
    FSMState.OVERSIGHT: {FSMState.EXECUTION, FSMState.CLOSED, FSMState.ESCALATED},
    FSMState.EXECUTION: {FSMState.CLOSED, FSMState.ERROR, FSMState.ESCALATED},
    FSMState.ESCALATED: {FSMState.CLOSED, FSMState.ANALYSIS},
    FSMState.ERROR: {FSMState.CLOSED},
}


@dataclass
class IncidentContext:
    incident_id: UUID = field(default_factory=uuid4)
    tenant_id: str = ""
    state: FSMState = FSMState.IDLE
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    severity: str = None
    confidence: float = 0.0
    events: List[Dict[str, Any]] = field(default_factory=list)
    findings: List[AgentOutput] = field(default_factory=list)
    entities: Dict[str, Set[str]] = field(default_factory=dict)
    mitre_techniques: Set[str] = field(default_factory=set)
    tokens_used: int = 0
    token_budget: int = 50000
    activated_agents: Set[str] = field(default_factory=set)
    verdict: Dict[str, Any] = None
    proposal: Dict[str, Any] = None
    timeline: List[Dict[str, Any]] = field(default_factory=list)
    escalation_reason: str = None
    playbook_id: str = None
    
    def add_timeline_event(self, event: str, agent: str = None, details: Dict = None):
        self.timeline.append({
            "timestamp": datetime.utcnow().isoformat(),
            "event": event,
            "agent": agent,
            "details": details or {},
            "state": self.state.value,
        })
        self.updated_at = datetime.utcnow()


class AgentRegistry:
    def __init__(self):
        self._agents: Dict[str, Any] = {}
    
    def register(self, name: str, agent):
        self._agents[name] = agent
    
    def get(self, name: str):
        return self._agents.get(name)
    
    def get_all(self) -> Dict[str, Any]:
        return self._agents.copy()
    
    def get_by_layer(self, layer: str) -> List[Any]:
        # Would filter by agent layer
        return list(self._agents.values())
    
    @classmethod
    def create_default(cls) -> "AgentRegistry":
        registry = cls()
        for name, agent_class in ALL_AGENTS.items():
            try:
                registry.register(name, agent_class())
            except Exception as e:
                logger.warning("agent_init_failed", agent=name, error=str(e))
        logger.info("agent_registry_created", count=len(registry._agents))
        return registry


class Coordinator:
    def __init__(self, event_bus=None, agent_registry: AgentRegistry = None):
        self._incidents: Dict[UUID, IncidentContext] = {}
        self.event_bus = event_bus
        self.agent_registry = agent_registry or AgentRegistry.create_default()
        self._active_incidents: Dict[UUID, IncidentContext] = {}
    
    def _create_context(self, event: Dict[str, Any], tenant_id: str = "default") -> IncidentContext:
        context = IncidentContext(tenant_id=tenant_id, state=FSMState.DETECTION)
        context.events.append(event)
        context.severity = event.get("severity")
        for entity in event.get("entities", []):
            etype = entity.get("type", "unknown")
            if etype not in context.entities:
                context.entities[etype] = set()
            context.entities[etype].add(entity.get("value", ""))
        context.add_timeline_event("incident_created", details={"event_type": event.get("event_type")})
        self._active_incidents[context.incident_id] = context
        return context
    
    def _can_transition(self, context: IncidentContext, new_state: FSMState) -> bool:
        valid = VALID_TRANSITIONS.get(context.state, set())
        return new_state in valid
    
    def _transition_state(self, context: IncidentContext, new_state: FSMState):
        if not self._can_transition(context, new_state):
            logger.warning("invalid_transition", current=context.state.value, target=new_state.value)
            return False
        old_state = context.state
        context.state = new_state
        context.add_timeline_event("state_transition", details={"from": old_state.value, "to": new_state.value})
        logger.info("state_transition", incident=str(context.incident_id), from_state=old_state.value, to_state=new_state.value)
        # Persist state change
        try:
            import asyncio
            asyncio.create_task(incident_repo.update_incident(
                incident_id=context.incident_id,
                state=new_state.value,
                confidence=context.confidence,
                tokens_used=context.tokens_used,
                summary=context.verdict.get("summary") if context.verdict else None,
            ))
        except Exception as e:
            logger.error("state_persist_failed", error=str(e))
        return True
    
    def _check_token_budget(self, context: IncidentContext) -> str:
        pct = context.tokens_used / context.token_budget
        if pct >= 0.95:
            return "CRITICAL"
        if pct >= 0.90:
            return "FORCE_TRANSITION"
        if pct >= 0.80:
            return "WARNING"
        return "OK"
    
    async def process_incident(self, context: IncidentContext):
        try:
            while context.state not in {FSMState.CLOSED, FSMState.ERROR, FSMState.ESCALATED}:
                budget_status = self._check_token_budget(context)
                if budget_status == "CRITICAL":
                    self._transition_state(context, FSMState.CLOSED)
                    context.add_timeline_event("budget_exhausted")
                    break
                
                if context.state == FSMState.DETECTION:
                    await self._run_detection(context)
                elif context.state == FSMState.ENRICHMENT:
                    await self._run_enrichment(context)
                elif context.state == FSMState.ANALYSIS:
                    await self._run_analysis(context)
                elif context.state == FSMState.PROPOSAL:
                    await self._run_proposal(context)
                elif context.state == FSMState.OVERSIGHT:
                    await self._run_oversight(context)
                elif context.state == FSMState.EXECUTION:
                    await self._run_execution(context)
                    break
        except Exception as e:
            logger.error("incident_processing_error", incident=str(context.incident_id), error=str(e))
            self._transition_state(context, FSMState.ERROR)
    
    async def _run_detection(self, context: IncidentContext):
        router = self.agent_registry.get("router")
        if router:
            agent_context = AgentContext(incident_id=context.incident_id, tenant_id=context.tenant_id, state=context.state, event_data=context.events[0] if context.events else {}, events=context.events, findings=context.findings, entities=context.entities, token_budget=context.token_budget, tokens_used=context.tokens_used)
            output = await router.process(agent_context)
            context.tokens_used += output.tokens_used
            context.activated_agents.update(output.content.get("activated_agents", []))
            context.confidence = output.confidence
            context.add_timeline_event("router_activated", agent="router", details={"agents": list(context.activated_agents)})
        logger.info("detection_complete", confidence=context.confidence, threshold=settings.THRESHOLD_DISMISS, activated_agents=list(context.activated_agents))
        if context.confidence < settings.THRESHOLD_DISMISS:
            self._transition_state(context, FSMState.CLOSED)
        else:
            self._transition_state(context, FSMState.ENRICHMENT)
    
    async def _run_enrichment(self, context: IncidentContext):
        intel = self.agent_registry.get("intel")
        if intel:
            agent_context = AgentContext(incident_id=context.incident_id, tenant_id=context.tenant_id, state=context.state, event_data=context.events[0] if context.events else {}, events=context.events, findings=context.findings, entities=context.entities, token_budget=context.token_budget, tokens_used=context.tokens_used)
            output = await intel.process(agent_context)
            context.tokens_used += output.tokens_used
            context.findings.append(output)
            context.add_timeline_event("intel_enrichment", agent="intel")
        self._transition_state(context, FSMState.ANALYSIS)
    
    async def _run_analysis(self, context: IncidentContext):
        analyst = self.agent_registry.get("analyst")
        if analyst:
            agent_context = AgentContext(incident_id=context.incident_id, tenant_id=context.tenant_id, state=context.state, event_data=context.events[0] if context.events else {}, events=context.events, findings=context.findings, entities=context.entities, token_budget=context.token_budget, tokens_used=context.tokens_used)
            output = await analyst.process(agent_context)
            context.tokens_used += output.tokens_used
            context.findings.append(output)
            context.verdict = output.content
            context.confidence = output.confidence
            context.add_timeline_event("analyst_verdict", agent="analyst", details={"verdict": output.content.get("verdict")})
        if context.confidence < settings.THRESHOLD_INVESTIGATE:
            self._transition_state(context, FSMState.CLOSED)
        else:
            self._transition_state(context, FSMState.PROPOSAL)
    
    async def _run_proposal(self, context: IncidentContext):
        responder = self.agent_registry.get("responder")
        if responder:
            agent_context = AgentContext(incident_id=context.incident_id, tenant_id=context.tenant_id, state=context.state, event_data=context.events[0] if context.events else {}, events=context.events, findings=context.findings, entities=context.entities, token_budget=context.token_budget, tokens_used=context.tokens_used)
            output = await responder.process(agent_context)
            context.tokens_used += output.tokens_used
            context.proposal = output.content
            context.add_timeline_event("proposal_generated", agent="responder")
        self._transition_state(context, FSMState.OVERSIGHT)
    
    async def _run_oversight(self, context: IncidentContext):
        oversight = self.agent_registry.get("oversight")
        if oversight:
            agent_context = AgentContext(incident_id=context.incident_id, tenant_id=context.tenant_id, state=context.state, event_data=context.events[0] if context.events else {}, events=context.events, findings=context.findings, entities=context.entities, token_budget=context.token_budget, tokens_used=context.tokens_used)
            output = await oversight.process(agent_context)
            context.tokens_used += output.tokens_used
            decision = output.content.get("decision", "APPROVE")
            if decision == "VETO":
                context.escalation_reason = output.content.get("veto_reason", "Governance veto")
                self._transition_state(context, FSMState.ESCALATED)
            elif decision == "ESCALATE":
                context.escalation_reason = output.content.get("escalation_reason", "Requires human review")
                self._transition_state(context, FSMState.ESCALATED)
            else:
                self._transition_state(context, FSMState.EXECUTION)
    
    async def _run_execution(self, context: IncidentContext):
        context.add_timeline_event("execution_started")
        # Would execute actions here
        context.add_timeline_event("execution_completed")
        self._transition_state(context, FSMState.CLOSED)
    
    def get_incident(self, incident_id: UUID) -> Optional[IncidentContext]:
        return self._active_incidents.get(incident_id)
    
    def list_incidents(self, tenant_id: str = None) -> List[IncidentContext]:
        incidents = list(self._active_incidents.values())
        if tenant_id:
            incidents = [i for i in incidents if i.tenant_id == tenant_id]
        return incidents


# Embedding integration

    async def check_timeouts(self):
        """Check for timed-out incidents and handle them."""
        now = datetime.utcnow()
        for incident_id, context in list(self._incidents.items()):
            # Check if incident has been running too long
            if hasattr(context, 'created_at'):
                elapsed = (now - context.created_at).total_seconds()
                if elapsed > 300 and context.state not in (FSMState.CLOSED, FSMState.ERROR):  # 5 minute timeout
                    logger.warning("incident_timeout", incident_id=str(incident_id), elapsed=elapsed)
                    context.state = FSMState.CLOSED
                    context.add_timeline_event("Incident timed out", agent="coordinator")

    async def create_incident(self, tenant_id, event_id, event_data: Dict, entities: List = None):
        """Create a new incident from an event."""
        context = self._create_context(event_data, str(tenant_id))
        context.event_id = event_id
        context.entities = entities or []
        self._incidents[context.incident_id] = context
        logger.info("incident_created", incident_id=str(context.incident_id), event_type=event_data.get("event_type"))
        # Persist to database
        try:
            await incident_repo.create_incident(
                incident_id=context.incident_id,
                tenant_id=tenant_id if isinstance(tenant_id, UUID) else UUID(str(tenant_id)) if tenant_id else uuid4(),
                event_id=event_id if isinstance(event_id, UUID) else UUID(str(event_id)) if event_id else uuid4(),
                event_data=event_data,
                severity=event_data.get("severity", "MEDIUM"),
            )
        except Exception as e:
            logger.error("incident_persist_failed", error=str(e))
        # Start processing in background
        asyncio.create_task(self.process_incident(context))
        return context

async def enrich_with_embeddings(context: IncidentContext):
    """Enrich incident with embedding-based similarity search."""
    from hornet.embedding import embedding_pipeline, similarity_search
    
    # Generate embedding for incident
    incident_text = f"Event: {context.events[0].get('event_type', '')} "
    incident_text += f"Entities: {context.entities} "
    incident_text += f"Severity: {context.severity}"
    
    embedding = await embedding_pipeline.generate_embedding(incident_text)
    
    # Search for similar patterns
    similar = await similarity_search.search_patterns(
        embedding=embedding,
        tenant_id=context.tenant_id,
        top_k=5,
    )
    
    # Add to context
    context.add_timeline_event(
        "embedding_enrichment",
        details={
            "similar_patterns": len(similar),
            "top_match_score": similar[0]["score"] if similar else 0,
        }
    )
    
    return similar


# Add to Coordinator class
Coordinator.enrich_with_embeddings = staticmethod(enrich_with_embeddings)







