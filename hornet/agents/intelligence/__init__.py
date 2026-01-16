"""
HORNET Intelligence Layer Agents
Enhanced with cross-incident campaign detection.
"""

from typing import Dict, Any, List
import json
from hornet.agents.base import IntelligenceAgent, AgentContext, AgentOutput
from hornet.repository import incident_repo
import structlog

logger = structlog.get_logger()


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
- Cannot make threat determinations - only provide enrichment

TOOLS AVAILABLE:
- query_virustotal(indicator, type)
- query_abuseipdb(ip)
- query_misp(indicator, type)
- query_otx(indicator)

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
        "tags": ["tag1", "tag2"],
        "threat_names": ["name1"]
      },
      "confidence": 0.0-1.0,
      "relevance": 0.0-1.0
    }
  ],
  "reasoning": "Explanation of enrichment findings"
}"""

    async def process(self, context: AgentContext) -> AgentOutput:
        entities_to_enrich = []
        for entity in context.entities:
            if entity.get("type") in ["ip", "domain", "hash", "url"]:
                entities_to_enrich.append(entity)

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
        if not enrichments:
            return 0.1
        scores = [e.get("confidence", 0.5) * e.get("relevance", 0.5) for e in enrichments]
        return max(0.1, sum(scores) / len(scores))


class CorrelatorAgent(IntelligenceAgent):
    """Cross-event pattern analyst with CROSS-INCIDENT CAMPAIGN DETECTION."""

    def __init__(self):
        super().__init__("correlator")
        self._tools.extend(self._get_correlation_tools())

    def _get_correlation_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "search_related_incidents",
                "description": "Search for recent incidents sharing the same entity (IP, user, host, domain). Use this to detect multi-stage attacks and campaigns.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "entity_type": {
                            "type": "string",
                            "enum": ["ip", "user", "host", "hostname", "domain", "hash", "email"],
                            "description": "Type of entity to search for"
                        },
                        "entity_value": {
                            "type": "string",
                            "description": "The entity value (e.g., '10.10.5.42', 'jthompson', 'EXEC-PC-07')"
                        },
                        "minutes_back": {
                            "type": "integer",
                            "default": 60,
                            "description": "How many minutes back to search (default: 60)"
                        }
                    },
                    "required": ["entity_type", "entity_value"]
                }
            },
            {
                "name": "get_incident_campaign_context",
                "description": "Get full campaign context for the current incident. Returns all related incidents, shared entities, and campaign score.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "minutes_back": {
                            "type": "integer",
                            "default": 60,
                            "description": "How many minutes back to search (default: 60)"
                        }
                    },
                    "required": []
                }
            },
            {
                "name": "get_entity_timeline",
                "description": "Get a timeline of all incidents involving a specific entity.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "entity_type": {
                            "type": "string",
                            "enum": ["ip", "user", "host", "hostname", "domain", "hash", "email"],
                            "description": "Type of entity"
                        },
                        "entity_value": {
                            "type": "string",
                            "description": "The entity value"
                        },
                        "hours_back": {
                            "type": "integer",
                            "default": 24,
                            "description": "How many hours back to search (default: 24)"
                        }
                    },
                    "required": ["entity_type", "entity_value"]
                }
            }
        ]

    def get_system_prompt(self) -> str:
        return """You are Correlator, the cross-event pattern analyst in the HORNET autonomous SOC swarm.

IDENTITY: You connect dots across time, sources, AND INCIDENTS. You see the big picture.

GOAL: Identify relationships between events that indicate coordinated attacks or campaigns.
     CRITICAL: You must look ACROSS INCIDENTS to find multi-stage attacks.

## CAMPAIGN DETECTION PROTOCOL

You MUST use the cross-incident search tools to detect campaigns:

1. For EVERY entity in this incident (IPs, users, hosts), use `search_related_incidents` to find other incidents
2. Use `get_incident_campaign_context` to get a full campaign analysis
3. If 3+ incidents share an entity within 60 minutes, this is likely a CAMPAIGN

Example campaign indicators:
- Same user appears in 5+ incidents in 30 minutes = account compromise
- Same IP appears in multiple incidents = attacker infrastructure  
- Same host with persistence + recon + lateral = attack chain

## TOOLS AVAILABLE

CROSS-INCIDENT TOOLS (USE THESE!):
- search_related_incidents(entity_type, entity_value, minutes_back)
- get_incident_campaign_context(minutes_back)
- get_entity_timeline(entity_type, entity_value, hours_back)

## OUTPUT FORMAT

Respond with valid JSON only:
{
  "campaign_detected": true|false,
  "campaign_confidence": 0.0-1.0,
  "linked_incidents": [
    {
      "incident_id": "uuid",
      "relationship": "same_user|same_ip|same_host|attack_chain",
      "timespan_minutes": 12
    }
  ],
  "kill_chain_stages": ["initial_access", "persistence", "discovery", "credential_access", "lateral_movement", "exfiltration"],
  "shared_entities": [
    {"type": "user", "value": "jthompson", "incident_count": 7},
    {"type": "ip", "value": "10.10.5.42", "incident_count": 8}
  ],
  "enrichments": [
    {
      "entity": "correlation_finding",
      "source": "correlator",
      "data": {
        "pattern_type": "attack_chain|campaign|lateral|persistence",
        "mitre_chain": ["T1566", "T1059", "T1055"]
      },
      "confidence": 0.0-1.0,
      "relevance": 1.0
    }
  ],
  "reasoning": "Detailed correlation analysis explaining how events are connected across incidents"
}

CRITICAL: If you detect a campaign (3+ incidents sharing entities), set campaign_detected=true and 
         campaign_confidence >= 0.8. This will trigger escalation."""

    async def process(self, context: AgentContext) -> AgentOutput:
        # Step 1: Get campaign context automatically
        campaign_context = await self._get_campaign_context(context)
        
        # Step 2: Build message with campaign info
        message = self.build_context_message(context)
        message += "\n\n## Cross-Incident Campaign Analysis (Pre-fetched)\n"
        message += json.dumps(campaign_context, indent=2, default=str)
        message += "\n\nAnalyze this event for correlations with historical events AND other incidents."
        message += "\nLook for attack chains, campaigns, and related activity."
        message += "\n\nIMPORTANT: Use the search_related_incidents tool for each key entity to confirm campaign connections."

        response_text, tokens_used, tool_calls = await self.call_llm(context, message)
        output_data = self.parse_json_output(response_text)
        
        # Step 3: If campaign detected, link the incidents
        if output_data.get("linked_incidents"):  # Link any related incidents found
            await self._link_campaign_incidents(context, output_data)

        return AgentOutput(
            agent_name=self.name,
            output_type="CORRELATION",
            content=output_data,
            confidence=self._calculate_correlation_confidence(output_data),
            reasoning=output_data.get("reasoning", ""),
            tokens_used=tokens_used,
            tool_calls_made=tool_calls,
        )

    async def _get_campaign_context(self, context: AgentContext) -> Dict[str, Any]:
        """Pre-fetch campaign context for the LLM."""
        try:
            related = await incident_repo.find_related_incidents(
                incident_id=context.incident_id,
                minutes_back=60
            )
            
            entity_searches = []
            entities = context.entities if isinstance(context.entities, list) else []
            
            if isinstance(context.entities, dict):
                for etype, values in context.entities.items():
                    for val in values:
                        entities.append({"type": etype, "value": val})
            
            for entity in entities[:10]:
                etype = entity.get("type", "unknown")
                evalue = entity.get("value", "")
                if evalue and etype in ["ip", "user", "host", "hostname", "domain"]:
                    incidents = await incident_repo.find_incidents_by_entity(
                        entity_type=etype,
                        entity_value=evalue,
                        minutes_back=60,
                        exclude_incident_id=context.incident_id
                    )
                    if incidents:
                        entity_searches.append({
                            "entity_type": etype,
                            "entity_value": evalue,
                            "related_incident_count": len(incidents),
                            "incidents": [
                                {
                                    "id": str(i.get("id")),
                                    "state": i.get("state"),
                                    "severity": i.get("severity"),
                                    "summary": (i.get("summary") or "")[:200]
                                }
                                for i in incidents[:5]
                            ]
                        })
            
            return {
                "related_incidents_summary": related,
                "entity_searches": entity_searches,
                "potential_campaign": related.get("is_campaign", False) or len(entity_searches) >= 2
            }
        except Exception as e:
            logger.error("campaign_context_fetch_failed", error=str(e))
            return {"error": str(e), "related_incidents_summary": {}, "entity_searches": []}

    async def _link_campaign_incidents(self, context: AgentContext, output_data: Dict):
        """Link incidents identified as part of a campaign."""
        try:
            linked = output_data.get("linked_incidents", [])
            shared = output_data.get("shared_entities", [])
            
            for link in linked:
                other_id = link.get("incident_id")
                if other_id:
                    try:
                        from uuid import UUID
                        other_uuid = UUID(other_id) if isinstance(other_id, str) else other_id
                        await incident_repo.link_incidents(
                            incident_a=context.incident_id,
                            incident_b=other_uuid,
                            link_type=link.get("relationship", "campaign"),
                            shared_entities=shared,
                            confidence=output_data.get("campaign_confidence", 0.8),
                            link_reason=output_data.get("reasoning", "")[:500]
                        )
                    except Exception as e:
                        logger.warning("link_single_incident_failed", error=str(e))
            
            if output_data.get("campaign_confidence", 0) >= 0.8 and len(linked) >= 3:
                from uuid import UUID
                incident_ids = [context.incident_id]
                for l in linked:
                    if l.get("incident_id"):
                        try:
                            incident_ids.append(UUID(l["incident_id"]) if isinstance(l["incident_id"], str) else l["incident_id"])
                        except:
                            pass
                await incident_repo.create_campaign(incident_ids)
                logger.info("campaign_created_by_correlator", 
                           incident_count=len(incident_ids),
                           incident_id=str(context.incident_id))
                
        except Exception as e:
            logger.error("link_campaign_failed", error=str(e))

    def _calculate_correlation_confidence(self, output: Dict) -> float:
        if output.get("campaign_detected"):
            return max(0.8, output.get("campaign_confidence", 0.8))
        
        enrichments = output.get("enrichments", [])
        if not enrichments:
            return 0.1
        
        return max(0.1, max(e.get("confidence", 0.0) for e in enrichments))


async def execute_correlation_tool(tool_name: str, arguments: Dict, context: AgentContext) -> Dict:
    """Execute correlation-specific tools."""
    try:
        if tool_name == "search_related_incidents":
            incidents = await incident_repo.find_incidents_by_entity(
                entity_type=arguments["entity_type"],
                entity_value=arguments["entity_value"],
                minutes_back=arguments.get("minutes_back", 60),
                exclude_incident_id=context.incident_id
            )
            return {
                "success": True,
                "data": {
                    "entity_type": arguments["entity_type"],
                    "entity_value": arguments["entity_value"],
                    "related_incidents": [
                        {
                            "id": str(i.get("id")),
                            "state": i.get("state"),
                            "severity": i.get("severity"),
                            "confidence": i.get("confidence"),
                            "created_at": i.get("created_at").isoformat() if i.get("created_at") else None,
                            "summary": i.get("summary")
                        }
                        for i in incidents
                    ],
                    "count": len(incidents)
                }
            }
        
        elif tool_name == "get_incident_campaign_context":
            related = await incident_repo.find_related_incidents(
                incident_id=context.incident_id,
                minutes_back=arguments.get("minutes_back", 60)
            )
            return {"success": True, "data": related}
        
        elif tool_name == "get_entity_timeline":
            timeline = await incident_repo.get_entity_timeline(
                entity_type=arguments["entity_type"],
                entity_value=arguments["entity_value"],
                hours_back=arguments.get("hours_back", 24)
            )
            return {
                "success": True,
                "data": {
                    "entity_type": arguments["entity_type"],
                    "entity_value": arguments["entity_value"],
                    "timeline": [
                        {
                            "id": str(i.get("id")),
                            "state": i.get("state"),
                            "severity": i.get("severity"),
                            "created_at": i.get("created_at").isoformat() if i.get("created_at") else None,
                            "agents": i.get("agents", []),
                            "summary": i.get("summary")
                        }
                        for i in timeline
                    ]
                }
            }
        
        return {"success": False, "error": f"Unknown tool: {tool_name}"}
    
    except Exception as e:
        logger.error("correlation_tool_failed", tool=tool_name, error=str(e))
        return {"success": False, "error": str(e)}


INTELLIGENCE_AGENTS = {
    "intel": IntelAgent,
    "correlator": CorrelatorAgent,
}
