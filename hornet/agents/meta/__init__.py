"""
HORNET Meta Layer Agents
Agents responsible for swarm orchestration and infrastructure.
"""

from typing import Dict, Any, List, Optional
import json
import re
from hornet.agents.base import BaseAgent, AgentContext, AgentOutput
from hornet.config import EVENT_CLASSIFICATION, get_settings

settings = get_settings()


class RouterAgent(BaseAgent):
    """Event classifier that activates appropriate agents."""
    
    def __init__(self):
        super().__init__("router")
        self.classification_matrix = EVENT_CLASSIFICATION
    
    def get_system_prompt(self) -> str:
        return """You are Router, the event classifier in the HORNET autonomous SOC swarm.

IDENTITY: You decide which agents handle each event. You are the gateway.

GOAL: Classify incoming events and activate the appropriate agent set.

DISPOSITION: Fast and accurate. You optimize for correct classification with minimal latency.

CONSTRAINTS:
- Use rule-based Stage 1 whenever possible (0 tokens)
- Activate maximum 12 agents per event
- Must include relevant specialist agents based on event type

TWO-STAGE CLASSIFICATION:
Stage 1 (Rule-based): Pattern matching on event type, source, metadata
Stage 2 (LLM): Only when Stage 1 confidence < 0.7 or multi-domain

EVENT DOMAINS:
- auth: Authentication and identity events
- network: Network traffic and connection events
- endpoint: Host-based security events
- email: Email security events
- cloud: Cloud infrastructure events
- data: Data protection events

VALID AGENTS (only use these exact names):
  Detection: hunter, sentinel, behavioral, netwatch, endpoint, gatekeeper, dataguard, phisherman, cloudwatch, dns
  Intelligence: intel, correlator
  Analysis: analyst, triage, forensics
  Specialists: sandbox, scanner, redsim, vision, social, change, backup, uptime, api, container, darkweb, physical, supply, surface, tuner, synth, mobile, ot, bot, brand, fraud, identity, vuln, waf, secret, crypto, emailgateway, retro, simulator, complianceaudit, recovery
  Governance: oversight, compliance, legal
  Action: responder, deceiver, playbook

  OUTPUT FORMAT (use ONLY agent names from list above):
  {
    "classification": {"domain": "auth|network|endpoint|email|cloud|data", "sub_type": "string", "confidence": 0.0-1.0},
    "activated_agents": ["hunter", "intel", "etc"],
    "stage_used": 2,
    "reasoning": "Brief explanation"
  }"""
    
    def get_output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["classification", "activated_agents"],
            "properties": {
                "classification": {
                    "type": "object",
                    "required": ["domain", "sub_type", "confidence"],
                    "properties": {
                        "domain": {"type": "string"},
                        "sub_type": {"type": "string"},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1}
                    }
                },
                "activated_agents": {
                    "type": "array",
                    "items": {"type": "string"},
                    "maxItems": 12
                },
                "reasoning": {"type": "string"}
            }
        }
    
    def stage1_classify(self, event_type: str) -> Optional[Dict[str, Any]]:
        """
        Rule-based Stage 1 classification.
        Returns classification if confidence >= 0.7, else None.
        """
        # Direct match in classification matrix
        if event_type in self.classification_matrix:
            agents = self.classification_matrix[event_type]
            domain = event_type.split(".")[0]
            return {
                "classification": {
                    "domain": domain,
                    "sub_type": event_type,
                    "confidence": 0.95
                },
                "activated_agents": agents,
                "stage_used": 1,
                "reasoning": f"Direct match for event type {event_type}"
            }
        
        # Prefix match
        for pattern, agents in self.classification_matrix.items():
            if event_type.startswith(pattern.split(".")[0]):
                domain = pattern.split(".")[0]
                return {
                    "classification": {
                        "domain": domain,
                        "sub_type": event_type,
                        "confidence": 0.7
                    },
                    "activated_agents": agents[:8],  # Reduce for uncertain match
                    "stage_used": 1,
                    "reasoning": f"Prefix match for domain {domain}"
                }
        
        return None
    

    def _add_specialists(self, event_type: str, event_data: dict, agents: list) -> list:
        """Add specialist agents based on event keywords."""
        et_lower = event_type.lower()
        data_str = str(event_data).lower()
        
        specialist_map = {
            # Network threats
            "dns": ["dns", "netwatch"],
            "c2": ["netwatch", "hunter", "intel", "redsim"],
            "beacon": ["netwatch", "hunter", "redsim"],
            "lateral": ["netwatch", "hunter", "correlator"],
            "exfil": ["dataguard", "netwatch", "encryption"],
            "tunnel": ["dns", "netwatch"],
            "scan": ["scanner", "surface", "netwatch"],
            "ddos": ["uptime", "netwatch", "waf"],
            "firewall": ["netwatch", "change"],
            # Endpoint threats
            "malware": ["endpoint", "sandbox", "hunter", "forensics"],
            "ransom": ["endpoint", "backup", "recovery", "forensics"],
            "process": ["endpoint", "hunter", "behavioral"],
            "injection": ["endpoint", "redsim", "forensics"],
            "persistence": ["endpoint", "hunter", "forensics"],
            "script": ["endpoint", "sandbox"],
            "driver": ["endpoint", "change"],
            "memory": ["endpoint", "forensics", "redsim"],
            # Identity/Auth
            "brute": ["gatekeeper", "behavioral", "correlator"],
            "credential": ["gatekeeper", "hunter", "darkweb"],
            "privilege": ["gatekeeper", "compliance", "oversight"],
            "login": ["gatekeeper", "behavioral", "identity"],
            "mfa": ["gatekeeper", "compliance"],
            "password": ["gatekeeper", "identity"],
            "session": ["gatekeeper", "behavioral"],
            "impossible": ["gatekeeper", "behavioral", "fraud"],
            "account": ["gatekeeper", "identity", "compliance"],
            # Cloud/Container
            "container": ["container", "cloudwatch"],
            "k8s": ["container", "cloudwatch"],
            "kubernetes": ["container", "cloudwatch"],
            "pod": ["container"],
            "docker": ["container"],
            "iam": ["cloudwatch", "gatekeeper", "compliance"],
            "cloud": ["cloudwatch", "change"],
            "aws": ["cloudwatch", "secret"],
            "azure": ["cloudwatch", "identity"],
            "gcp": ["cloudwatch"],
            "s3": ["cloudwatch", "dataguard"],
            "storage": ["cloudwatch", "dataguard"],
            "api": ["api", "waf"],
            "serverless": ["cloudwatch", "api"],
            "config": ["change", "compliance"],
            # Email/Phishing
            "phish": ["phisherman", "vision", "social"],
            "email": ["phisherman", "emailgateway"],
            "bec": ["phisherman", "behavioral", "fraud"],
            "spam": ["phisherman", "emailgateway"],
            "attachment": ["phisherman", "sandbox"],
            "link": ["phisherman", "sandbox", "vision"],
            # Data protection
            "data": ["dataguard", "encryption", "compliance"],
            "sensitive": ["dataguard", "compliance"],
            "pii": ["dataguard", "compliance", "legal"],
            "gdpr": ["compliance", "legal", "dataguard"],
            "download": ["dataguard", "behavioral"],
            "encrypt": ["encryption", "crypto", "backup"],
            "secret": ["secret", "dataguard"],
            "key": ["secret", "crypto"],
            "token": ["secret", "api"],
            # Specialized threats
            "supply": ["supply", "scanner", "vuln"],
            "package": ["supply", "scanner"],
            "dependency": ["supply", "vuln"],
            "vuln": ["vuln", "scanner", "surface"],
            "cve": ["vuln", "scanner"],
            "patch": ["vuln", "change"],
            "waf": ["waf", "api"],
            "bot": ["bot", "waf", "behavioral"],
            "fraud": ["fraud", "behavioral", "identity"],
            "insider": ["behavioral", "dataguard", "identity"],
            "anomaly": ["behavioral", "correlator", "tuner"],
            # Mobile/IoT/OT
            "mobile": ["mobile", "endpoint"],
            "android": ["mobile", "sandbox"],
            "ios": ["mobile"],
            "iot": ["ot", "netwatch"],
            "scada": ["ot", "netwatch"],
            "ics": ["ot", "netwatch"],
            # Brand/External
            "brand": ["brand", "darkweb", "social"],
            "typosquat": ["brand", "dns"],
            "impersonat": ["brand", "social", "phisherman"],
            "darkweb": ["darkweb", "intel"],
            "leak": ["darkweb", "dataguard"],
            "breach": ["darkweb", "forensics", "legal"],
            # Simulation/Testing
            "pentest": ["redsim", "simulator"],
            "red": ["redsim", "simulator"],
            "attack": ["redsim", "correlator"],
            "mitre": ["redsim", "correlator"],
            # Compliance/Legal
            "compliance": ["compliance", "complianceaudit", "legal"],
            "audit": ["complianceaudit", "compliance"],
            "regulation": ["compliance", "legal"],
            "hipaa": ["compliance", "legal", "dataguard"],
            "pci": ["compliance", "legal", "encryption"],
            # Recovery/Forensics
            "forensic": ["forensics", "retro"],
            "incident": ["forensics", "correlator"],
            "recover": ["recovery", "backup"],
            "restore": ["recovery", "backup"],
            "retro": ["retro", "correlator"],
            # Physical security
            "physical": ["physical", "sentinel"],
            "badge": ["physical", "identity"],
            "cctv": ["physical"],
            # Triage/Synth/Sentinel
            "triage": ["triage", "analyst"],
            "priority": ["triage"],
            "synth": ["synth", "correlator"],
            "synthetic": ["synth"],
            "sentinel": ["sentinel", "hunter"],
            "watchdog": ["sentinel", "endpoint"],
            "integrity": ["sentinel", "forensics"],
        }
        
        for keyword, specialists in specialist_map.items():
            if keyword in et_lower or keyword in data_str:
                agents.extend(specialists)
        
        if "intel" not in agents:
            agents.append("intel")
        
        return list(dict.fromkeys(agents))[:12]

    async def process(self, context: AgentContext) -> AgentOutput:
        """Classify event and determine agent activation."""
        event_type = context.event_data.get("event_type", "unknown")
        
        # Try Stage 1 first
        stage1_result = self.stage1_classify(event_type)
        if stage1_result and stage1_result["classification"]["confidence"] >= 0.7:
            # Add specialist agents based on keywords
            agents = self._add_specialists(event_type, context.event_data, stage1_result["activated_agents"])
            stage1_result["activated_agents"] = agents
            return AgentOutput(
                agent_name=self.name,
                output_type="ROUTING",
                content=stage1_result,
                confidence=stage1_result["classification"]["confidence"],
                reasoning=stage1_result["reasoning"],
                tokens_used=0,  # No LLM call
            )
        
        # Fall back to Stage 2 (LLM)
        message = self.build_context_message(context)
        message += "\n\nClassify this event and determine which agents should handle it."
        message += f"\nAvailable domains: auth, network, endpoint, email, cloud, data"
        
        response_text, tokens_used, _ = await self.call_llm(
            context, message, max_tokens=1000, temperature=0.1
        )
        output_data = self.parse_json_output(response_text)
        output_data["stage_used"] = 2
        
        return AgentOutput(
            agent_name=self.name,
            output_type="ROUTING",
            content=output_data,
            confidence=output_data.get("classification", {}).get("confidence", 0.5),
            reasoning=output_data.get("reasoning", ""),
            tokens_used=tokens_used,
        )


class MemoryAgent(BaseAgent):
    """Institutional knowledge keeper."""
    
    def __init__(self):
        super().__init__("memory")
    
    def get_system_prompt(self) -> str:
        return """You are Memory, the institutional knowledge keeper in the HORNET autonomous SOC swarm.

IDENTITY: You store and retrieve historical context. You are the swarm's memory.

GOAL: Provide relevant historical context to other agents through efficient retrieval.

DISPOSITION: Organized. You maintain clean, searchable records.

CONSTRAINTS:
- Enforce tenant isolation on all queries
- Apply retention policies automatically
- Return relevance scores with all results

TOOLS AVAILABLE:
- store_event(event_data) -> event_id
- store_incident(incident_data) -> incident_id
- store_pattern(pattern_data) -> pattern_id
- query_similar(embedding, limit, filters) -> results
- query_entity(entity_type, entity_id, window) -> history
- query_timeline(start, end, filters) -> events

STORAGE TYPES:
- Events: Individual security events
- Incidents: Processed incident records
- Patterns: Learned attack patterns for matching
- Entity histories: Per-entity timelines

OUTPUT FORMAT:
Respond with valid JSON only:
{
  "results": [
    {
      "type": "event|incident|pattern",
      "id": "record_id",
      "data": {},
      "relevance_score": 0.0-1.0,
      "recency_days": 0
    }
  ],
  "query_metadata": {
    "total_results": 0,
    "filters_applied": [],
    "window": "time_range"
  },
  "tool_calls": [
    {"tool": "query_similar", "params": {...}}
  ],
  "reasoning": "Search strategy and findings"
}"""
    
    def get_output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["results"],
            "properties": {
                "results": {"type": "array"},
                "query_metadata": {"type": "object"},
                "reasoning": {"type": "string"}
            }
        }
    
    async def process(self, context: AgentContext) -> AgentOutput:
        """Query memory for relevant historical context."""
        message = self.build_context_message(context)
        message += "\n\nSearch for relevant historical context for this event."
        message += "\nLook for similar events, related incidents, and matching patterns."
        
        response_text, tokens_used, _ = await self.call_llm(context, message, max_tokens=1500)
        output_data = self.parse_json_output(response_text)
        
        return AgentOutput(
            agent_name=self.name,
            output_type="MEMORY",
            content=output_data,
            confidence=0.9,
            reasoning=output_data.get("reasoning", ""),
            tokens_used=tokens_used,
        )


class HealthAgent(BaseAgent):
    """Swarm health monitor."""
    
    def __init__(self):
        super().__init__("health")
    
    def get_system_prompt(self) -> str:
        return """You are Health, the swarm monitor in the HORNET autonomous SOC swarm.

IDENTITY: You detect problems with the swarm itself. You are the meta-monitor.

GOAL: Monitor agent health, coverage gaps, and system issues. Alert on degradation.

DISPOSITION: Vigilant. You watch for problems before they cause failures.

CONSTRAINTS:
- Cannot modify agent behaviorâ€”only report
- Must alert humans on critical health issues
- Track token usage and budget burn rate

MONITORING AREAS:
- Agent response times
- Agent error rates
- Coverage gaps (unmonitored event types)
- Token budget consumption
- Integration health
- Queue depth
- Deadlock detection

HEALTH THRESHOLDS:
- Agent error rate > 10%: WARNING
- Agent timeout > 3: DEGRADED
- Coverage gap detected: WARNING
- Budget > 80%: WARNING
- Budget > 95%: CRITICAL
- Integration unhealthy > 3 checks: CRITICAL

OUTPUT FORMAT:
Respond with valid JSON only:
{
  "health_status": {
    "overall": "HEALTHY|WARNING|DEGRADED|CRITICAL",
    "agents": {
      "agent_name": {
        "status": "HEALTHY|WARNING|ERROR",
        "last_response_ms": 0,
        "error_rate": 0.0,
        "issues": []
      }
    },
    "coverage_gaps": ["unmonitored_event_types"],
    "budget_status": {
      "used": 0,
      "total": 50000,
      "percentage": 0.0,
      "burn_rate_per_minute": 0
    },
    "integrations": {
      "integration_name": "HEALTHY|DEGRADED|UNHEALTHY"
    }
  },
  "alerts": [
    {"severity": "WARNING|CRITICAL", "message": "alert_description"}
  ],
  "reasoning": "Health assessment summary"
}"""
    
    def get_output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["health_status"],
            "properties": {
                "health_status": {"type": "object"},
                "alerts": {"type": "array"},
                "reasoning": {"type": "string"}
            }
        }
    
    async def process(self, context: AgentContext) -> AgentOutput:
        """Assess swarm health."""
        message = self.build_context_message(context)
        message += "\n\nAssess the health of the swarm based on available metrics."
        
        response_text, tokens_used, _ = await self.call_llm(context, message, max_tokens=1500)
        output_data = self.parse_json_output(response_text)
        
        return AgentOutput(
            agent_name=self.name,
            output_type="HEALTH",
            content=output_data,
            confidence=0.95,
            reasoning=output_data.get("reasoning", ""),
            tokens_used=tokens_used,
        )


# Export all meta agents
META_AGENTS = {
    "router": RouterAgent,
    "memory": MemoryAgent,
    "health": HealthAgent,
}

