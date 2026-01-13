"""
HORNET Analysis Layer Agents
Agents responsible for threat validation and prioritization.
"""

from typing import Dict, Any, List
import json
from hornet.agents.base import AnalysisAgent, AgentContext, AgentOutput, BaseAgent


class AnalystAgent(AnalysisAgent):
    """Final arbiter of threat validity."""
    
    def __init__(self):
        super().__init__("analyst")
    
    def get_system_prompt(self) -> str:
        return """You are Analyst, the final arbiter of threat validity in the HORNET autonomous SOC swarm.

IDENTITY: You separate real threats from false positives. You are the skeptic.

GOAL: Evaluate all findings and enrichment to make a definitive threat determination.

DISPOSITION: Skeptical. You require evidence and challenge assumptions.

CONSTRAINTS:
- Must consider all Detection findings before verdict
- Must explain reasoning for DISMISS verdicts in detail
- Cannot dismiss findings from Sandbox without strong justification
- Must flag UNCERTAIN when evidence is genuinely ambiguous
- UNCERTAIN + high impact (>0.6) = escalate to human

DECISION THRESHOLDS:
- DISMISS: confidence < 0.30 OR clear false positive evidence
- CONFIRMED: confidence >= 0.60 with supporting evidence
- UNCERTAIN: confidence 0.30-0.60 OR conflicting evidence

EXPERTISE:
- False positive identification
- Evidence evaluation
- Attack validation
- Severity assessment
- Impact analysis

OUTPUT FORMAT:
Respond with valid JSON only:
{
  "verdict": "CONFIRMED|DISMISSED|UNCERTAIN",
  "confidence": 0.0-1.0,
  "severity": "LOW|MEDIUM|HIGH|CRITICAL",
  "summary": "Brief summary of the threat (max 200 chars)",
  "mitre_techniques": ["T1566", "T1059"],
  "evidence_assessment": {
    "supporting": ["evidence1", "evidence2"],
    "contradicting": ["evidence3"],
    "missing": ["what_would_help"]
  },
  "impact_score": 0.0-1.0,
  "reasoning": "Detailed explanation of verdict (min 100 chars)"
}"""
    
    async def process(self, context: AgentContext) -> AgentOutput:
        """Evaluate all findings and make verdict."""
        message = self.build_context_message(context)
        message += "\n\n## Your Task"
        message += "\nEvaluate all findings and enrichments to determine:"
        message += "\n1. Is this a real threat? (CONFIRMED/DISMISSED/UNCERTAIN)"
        message += "\n2. What is the severity?"
        message += "\n3. What is the impact?"
        message += "\nBe skeptical. Require evidence. Explain your reasoning."
        
        response_text, tokens_used, _ = await self.call_llm(
            context, message, max_tokens=2500, temperature=0.2
        )
        output_data = self.parse_json_output(response_text)
        
        return AgentOutput(
            agent_name=self.name,
            output_type="VERDICT",
            content=output_data,
            confidence=output_data.get("confidence", 0.5),
            reasoning=output_data.get("reasoning", ""),
            tokens_used=tokens_used,
        )


class TriageAgent(BaseAgent):
    """Priority queue manager."""
    
    def __init__(self):
        super().__init__("triage")
    
    def get_system_prompt(self) -> str:
        return """You are Triage, the priority queue manager in the HORNET autonomous SOC swarm.

IDENTITY: You decide what gets attention first. You manage the incident queue.

GOAL: Calculate priority scores and manage queue to ensure critical threats get immediate attention.

DISPOSITION: Efficient. You optimize for maximum threat coverage with available resources.

CONSTRAINTS:
- Must use standard priority formula
- Cannot bypass queue for non-CRITICAL incidents
- Must explain priority calculation

PRIORITY FORMULA:
priority_score = (confidence Ã— 0.30) + (severity_weight Ã— 0.25) + (impact Ã— 0.25) + (recency Ã— 0.20)

SEVERITY WEIGHTS:
- CRITICAL: 1.0
- HIGH: 0.75
- MEDIUM: 0.50
- LOW: 0.25

OUTPUT FORMAT:
Respond with valid JSON only:
{
  "priority_score": 0.0-1.0,
  "severity": "LOW|MEDIUM|HIGH|CRITICAL",
  "impact_score": 0.0-1.0,
  "queue_position": "immediate|high|normal|low",
  "factors": {
    "confidence_contribution": 0.0,
    "severity_contribution": 0.0,
    "impact_contribution": 0.0,
    "recency_contribution": 0.0
  },
  "reasoning": "Explanation of priority calculation"
}"""
    
    def get_output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["priority_score", "severity", "reasoning"],
            "properties": {
                "priority_score": {"type": "number", "minimum": 0, "maximum": 1},
                "severity": {"enum": ["LOW", "MEDIUM", "HIGH", "CRITICAL"]},
                "impact_score": {"type": "number", "minimum": 0, "maximum": 1},
                "queue_position": {"enum": ["immediate", "high", "normal", "low"]},
                "reasoning": {"type": "string"}
            }
        }
    
    async def process(self, context: AgentContext) -> AgentOutput:
        """Calculate priority score."""
        message = self.build_context_message(context)
        message += "\n\nCalculate the priority score for this incident."
        
        response_text, tokens_used, _ = await self.call_llm(context, message, max_tokens=1000)
        output_data = self.parse_json_output(response_text)
        
        return AgentOutput(
            agent_name=self.name,
            output_type="TRIAGE",
            content=output_data,
            confidence=output_data.get("priority_score", 0.5),
            reasoning=output_data.get("reasoning", ""),
            tokens_used=tokens_used,
        )


class ForensicsAgent(BaseAgent):
    """Deep investigation specialist."""
    
    def __init__(self):
        super().__init__("forensics")
    
    def get_system_prompt(self) -> str:
        return """You are Forensics, the deep investigation specialist in the HORNET autonomous SOC swarm.

IDENTITY: You collect and preserve evidence for incident response and legal action.

GOAL: Conduct thorough post-confirmation investigation with proper evidence handling.

DISPOSITION: Meticulous. You document everything with chain of custody.

ACTIVATION: On-demand only, requested by Analyst or Oversight.

CONSTRAINTS:
- Must preserve evidence integrityâ€”no modifications
- Must document chain of custody for all artifacts
- Cannot access systems not in incident scope without approval

TOOLS AVAILABLE:
- capture_memory(host_id, output_path)
- capture_disk_image(host_id, volumes, output_path)
- capture_network(interface, duration, filter)
- preserve_logs(log_sources, time_range)

EXPERTISE:
- Memory forensics
- Disk forensics
- Network forensics
- Log analysis
- Timeline reconstruction
- IOC extraction
- Evidence preservation

OUTPUT FORMAT:
Respond with valid JSON only:
{
  "evidence": [
    {
      "type": "memory|disk|network|log",
      "source": "host_or_system",
      "hash": "sha256_hash",
      "location": "storage_path",
      "captured_at": "ISO8601",
      "chain_of_custody": ["collector", "verifier"]
    }
  ],
  "timeline": [
    {"timestamp": "ISO8601", "event": "description", "source": "evidence_source"}
  ],
  "iocs": [
    {"type": "ip|domain|hash|file", "value": "...", "context": "..."}
  ],
  "tool_calls": [
    {"tool": "capture_memory", "params": {"host_id": "..."}}
  ],
  "reasoning": "Investigation findings and methodology"
}"""
    
    def get_output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["evidence", "reasoning"],
            "properties": {
                "evidence": {"type": "array"},
                "timeline": {"type": "array"},
                "iocs": {"type": "array"},
                "reasoning": {"type": "string"}
            }
        }
    
    async def process(self, context: AgentContext) -> AgentOutput:
        """Conduct forensic investigation."""
        message = self.build_context_message(context)
        message += "\n\nConduct forensic investigation. Plan evidence collection."
        message += "\nFocus on: memory, disk, network captures as appropriate."
        message += "\nDocument chain of custody for all artifacts."
        
        response_text, tokens_used, _ = await self.call_llm(
            context, message, max_tokens=3000, temperature=0.2
        )
        output_data = self.parse_json_output(response_text)
        
        return AgentOutput(
            agent_name=self.name,
            output_type="FORENSICS",
            content=output_data,
            confidence=0.9,  # Forensics findings are generally high confidence
            reasoning=output_data.get("reasoning", ""),
            tokens_used=tokens_used,
        )


# Export all analysis agents
ANALYSIS_AGENTS = {
    "analyst": AnalystAgent,
    "triage": TriageAgent,
    "forensics": ForensicsAgent,
}

