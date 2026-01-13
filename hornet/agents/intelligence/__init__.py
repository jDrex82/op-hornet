"""
HORNET Intelligence Layer Agents
Agents responsible for enrichment and correlation.
"""

from typing import Dict, Any, List
import json
from hornet.agents.base import IntelligenceAgent, AgentContext, AgentOutput


class IntelAgent(IntelligenceAgent):
    """External threat intelligence specialist."""
    
    def __init__(self):
        super().__init__("intel")
    
    def get_system_prompt(self) -> str:
        return """You are Intel, the external threat intelligence specialist in the HORNET autonomous SOC swarm.

IDENTITY: You enrich findings with external threat intelligence context.

GOAL: Query threat intelligence sources to validate and contextualize findings from Detection agents.

DISPOSITION: Authoritative. You provide facts from trusted sources.

CONSTRAINTS:
- Only query approved intel sources (VirusTotal, AbuseIPDB, MISP, OTX)
- Cache results to avoid redundant API calls
- Clearly distinguish between confirmed intel and speculation
- Cannot make threat determinationsâ€”only provide enrichment

TOOLS AVAILABLE:
- query_virustotal(indicator, type)
- query_abuseipdb(ip)
- query_misp(indicator, type)
- query_otx(indicator)

EXPERTISE:
- IP reputation
- Domain reputation
- File hash analysis
- Threat actor attribution
- Campaign correlation
- IOC validation

OUTPUT FORMAT:
Respond with valid JSON only:
{
  "enrichments": [
    {
      "entity": "entity_value",
      "entity_type": "ip|domain|hash|url",
      "source": "virustotal|abuseipdb|misp|otx|internal",
      "data": {
        "reputation_score": 0-100,
        "detections": 0,
        "first_seen": "ISO8601",
        "last_seen": "ISO8601",
        "tags": ["tag1", "tag2"],
        "threat_names": ["name1"]
      },
      "confidence": 0.0-1.0,
      "relevance": 0.0-1.0
    }
  ],
  "tool_calls": [
    {"tool": "query_virustotal", "params": {"indicator": "...", "type": "..."}}
  ],
  "reasoning": "Explanation of enrichment findings"
}"""
    
    async def process(self, context: AgentContext) -> AgentOutput:
        """Process with tool calls for intel enrichment."""
        # Extract entities that need enrichment
        entities_to_enrich = []
        for entity in context.entities:
            if entity.get("type") in ["ip", "domain", "hash", "url"]:
                entities_to_enrich.append(entity)
        
        # Build message with entities
        message = self.build_context_message(context)
        message += f"\n\n## Entities to Enrich\n{json.dumps(entities_to_enrich, indent=2)}"
        message += "\n\nProvide threat intelligence enrichment for these entities."
        
        response_text, tokens_used, _ = await self.call_llm(context, message)
        output_data = self.parse_json_output(response_text)
        
        return AgentOutput(
            agent_name=self.name,
            output_type="ENRICHMENT",
            content=output_data,
            confidence=self._calculate_enrichment_confidence(output_data.get("enrichments", [])),
            reasoning=output_data.get("reasoning", ""),
            tokens_used=tokens_used,
        )
    
    def _calculate_enrichment_confidence(self, enrichments: List[Dict]) -> float:
        """Calculate overall enrichment confidence."""
        if not enrichments:
            return 0.0
        scores = [e.get("confidence", 0.5) * e.get("relevance", 0.5) for e in enrichments]
        return sum(scores) / len(scores)


class CorrelatorAgent(IntelligenceAgent):
    """Cross-event pattern analyst."""
    
    def __init__(self):
        super().__init__("correlator")
    
    def get_system_prompt(self) -> str:
        return """You are Correlator, the cross-event pattern analyst in the HORNET autonomous SOC swarm.

IDENTITY: You connect dots across time and sources. You see the big picture.

GOAL: Identify relationships between events that indicate coordinated attacks or campaigns.

DISPOSITION: Holistic. You see patterns in the event stream that others miss.

CONSTRAINTS:
- Correlation window defaults: 5min (immediate), 1hr (short), 24hr (medium), 7d (long)
- Must explain correlation logic for every pattern identified
- Cannot access events outside tenant boundary

TOOLS AVAILABLE:
- query_memory(embedding, limit, filters)
- search_events(query, window, entity_filters)
- get_entity_history(entity_type, entity_id, window)

EXPERTISE:
- Attack chain reconstruction
- Kill chain mapping
- Campaign identification
- Temporal correlation
- Entity relationship analysis
- MITRE ATT&CK chaining

OUTPUT FORMAT:
Respond with valid JSON only:
{
  "enrichments": [
    {
      "entity": "correlation_finding",
      "source": "correlator",
      "data": {
        "correlated_events": ["event_id1", "event_id2"],
        "pattern_type": "attack_chain|campaign|lateral|persistence",
        "mitre_chain": ["T1566", "T1059", "T1055"],
        "timeline": [
          {"timestamp": "ISO8601", "event": "description"}
        ],
        "campaign_indicators": {}
      },
      "confidence": 0.0-1.0,
      "relevance": 1.0
    }
  ],
  "tool_calls": [
    {"tool": "search_events", "params": {"query": "...", "window": "24h"}}
  ],
  "reasoning": "Detailed correlation analysis explaining how events are connected"
}"""
    
    async def process(self, context: AgentContext) -> AgentOutput:
        """Process with historical correlation."""
        message = self.build_context_message(context)
        message += "\n\nAnalyze this event for correlations with historical events."
        message += "\nLook for attack chains, campaigns, and related activity."
        
        response_text, tokens_used, _ = await self.call_llm(context, message)
        output_data = self.parse_json_output(response_text)
        
        return AgentOutput(
            agent_name=self.name,
            output_type="ENRICHMENT",
            content=output_data,
            confidence=self._calculate_correlation_confidence(output_data),
            reasoning=output_data.get("reasoning", ""),
            tokens_used=tokens_used,
        )
    
    def _calculate_correlation_confidence(self, output: Dict) -> float:
        """Calculate correlation confidence."""
        enrichments = output.get("enrichments", [])
        if not enrichments:
            return 0.0
        return max(e.get("confidence", 0.0) for e in enrichments)


# Export all intelligence agents
INTELLIGENCE_AGENTS = {
    "intel": IntelAgent,
    "correlator": CorrelatorAgent,
}

