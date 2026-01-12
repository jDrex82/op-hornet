"""
HORNET Agents
All 54 agents for the autonomous SOC swarm.
"""
from hornet.agents.base import BaseAgent, DetectionAgent, AgentContext, AgentOutput

# Detection agents
from hornet.agents.detection import (
    HunterAgent, SentinelAgent, BehavioralAgent, NetWatchAgent,
    EndpointAgent, GatekeeperAgent, DataGuardAgent, PhishermanAgent,
    CloudWatchAgent, DNSAgent, DETECTION_AGENTS,
)

# Intelligence agents
from hornet.agents.intelligence import IntelAgent, CorrelatorAgent, INTELLIGENCE_AGENTS

# Analysis agents
from hornet.agents.analysis import AnalystAgent, TriageAgent, ForensicsAgent, ANALYSIS_AGENTS

# Action agents
from hornet.agents.action import ResponderAgent, DeceiverAgent, RecoveryAgent, PlaybookAgent, ACTION_AGENTS

# Governance agents
from hornet.agents.governance import OversightAgent, ComplianceAgent, LegalAgent, GOVERNANCE_AGENTS

# Meta agents
from hornet.agents.meta import RouterAgent, MemoryAgent, HealthAgent, META_AGENTS

# Specialist agents
from hornet.agents.specialists import SPECIALIST_AGENTS
from hornet.agents.specialists.full_agents import FULL_SPECIALIST_AGENTS


# Combine all agents
ALL_AGENTS = {}
ALL_AGENTS.update(DETECTION_AGENTS)
ALL_AGENTS.update(INTELLIGENCE_AGENTS)
ALL_AGENTS.update(ANALYSIS_AGENTS)
ALL_AGENTS.update(ACTION_AGENTS)
ALL_AGENTS.update(GOVERNANCE_AGENTS)
ALL_AGENTS.update(META_AGENTS)
ALL_AGENTS.update(SPECIALIST_AGENTS)
ALL_AGENTS.update(FULL_SPECIALIST_AGENTS)  # Override with full implementations


# Agent count by layer
AGENT_COUNTS = {
    "detection": len(DETECTION_AGENTS),
    "intelligence": len(INTELLIGENCE_AGENTS),
    "analysis": len(ANALYSIS_AGENTS),
    "action": len(ACTION_AGENTS),
    "governance": len(GOVERNANCE_AGENTS),
    "meta": len(META_AGENTS),
    "specialists": len(SPECIALIST_AGENTS) + len(FULL_SPECIALIST_AGENTS),
    "total": len(ALL_AGENTS),
}


def get_agent(name: str) -> BaseAgent:
    """Get an agent by name."""
    agent_class = ALL_AGENTS.get(name)
    if agent_class:
        return agent_class()
    return None


def list_agents() -> list:
    """List all available agents."""
    return list(ALL_AGENTS.keys())


__all__ = [
    "BaseAgent",
    "DetectionAgent",
    "AgentContext",
    "AgentOutput",
    "ALL_AGENTS",
    "AGENT_COUNTS",
    "get_agent",
    "list_agents",
]
