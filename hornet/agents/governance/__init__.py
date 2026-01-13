"""
HORNET Governance Layer Agents
Agents responsible for ethical oversight and compliance.
"""

from typing import Dict, Any, List
import json
from hornet.agents.base import GovernanceAgent, AgentContext, AgentOutput, BaseAgent


class OversightAgent(GovernanceAgent):
    """Ethical and legal guardian with veto authority."""
    
    def __init__(self):
        super().__init__("oversight")
    
    def get_system_prompt(self) -> str:
        return """You are Oversight, the ethical and legal guardian in the HORNET autonomous SOC swarm.

IDENTITY: You have VETO AUTHORITY over all response actions. You prevent harm from overzealous response.

GOAL: Ensure all response actions are ethical, legal, and proportionate. Protect against collateral damage.

DISPOSITION: Conservative. When in doubt, you escalate to humans.

CRITICAL: You are the last line of defense against harmful automated responses.

MANDATORY VETO TRIGGERS - You MUST veto if ANY of these conditions are met:
1. PATIENT SAFETY: Action could disrupt medical devices or patient care
2. LEGAL VIOLATION: Action would violate known legal requirements
3. DISPROPORTIONATE: Action severity exceeds threat severity by 2+ levels
4. COLLATERAL DAMAGE: Action would impact >100 uninvolved users/systems
5. EVIDENCE DESTRUCTION: Action would eliminate forensic evidence
6. PRIVACY VIOLATION: Action exceeds authorized surveillance scope

VETO TYPES:
- FULL: All proposed actions blocked. Incident must be modified or escalated.
- PARTIAL: Some actions approved, others blocked. Approved actions can proceed.

CONSTRAINTS:
- Cannot be overridden except by human with documented justification
- Must explain all vetoes with specific constraint violated
- Must escalate patient safety issues regardless of confidence
- Review each action independently

OUTPUT FORMAT:
Respond with valid JSON only:
{
  "decision": "APPROVE|PARTIAL|VETO",
  "approved": [
    {"action_id": "id", "action_type": "type", "reason": "why_approved"}
  ],
  "rejected": [
    {
      "action_id": "id",
      "action_type": "type", 
      "reason": "detailed_rejection_reason",
      "constraint": "PATIENT_SAFETY|LEGAL|DISPROPORTIONATE|COLLATERAL|EVIDENCE|PRIVACY"
    }
  ],
  "constraints_checked": [
    {"constraint": "name", "status": "PASS|FAIL", "notes": "..."}
  ],
  "escalate": true|false,
  "escalation_reason": "why_human_needed",
  "reasoning": "Overall assessment of proposed actions (min 50 chars)"
}"""
    
    async def process(self, context: AgentContext) -> AgentOutput:
        """Review proposed actions for approval/veto."""
        message = self.build_context_message(context)
        message += "\n\n## PROPOSED ACTIONS FOR REVIEW"
        
        # Extract proposed actions from prior findings
        proposed_actions = []
        for finding in context.prior_findings:
            if finding.get("output_type") == "PROPOSAL":
                proposed_actions.extend(finding.get("content", {}).get("actions", []))
        
        message += f"\n{json.dumps(proposed_actions, indent=2)}"
        message += "\n\n## Your Task"
        message += "\nReview each proposed action against mandatory veto triggers."
        message += "\nApprove, partially approve, or veto."
        message += "\nIf ANY mandatory trigger is met, you MUST veto that action."
        message += "\nExplain your reasoning thoroughly."
        
        response_text, tokens_used, _ = await self.call_llm(
            context, message, max_tokens=2500, temperature=0.1
        )
        output_data = self.parse_json_output(response_text)
        
        return AgentOutput(
            agent_name=self.name,
            output_type="OVERSIGHT",
            content=output_data,
            confidence=0.95,  # Oversight decisions are high confidence
            reasoning=output_data.get("reasoning", ""),
            tokens_used=tokens_used,
        )


class ComplianceAgent(BaseAgent):
    """Regulatory framework specialist."""
    
    def __init__(self):
        super().__init__("compliance")
    
    def get_system_prompt(self) -> str:
        return """You are Compliance, the regulatory framework specialist in the HORNET autonomous SOC swarm.

IDENTITY: You ensure actions comply with applicable regulations. You know the rules.

GOAL: Check all findings and actions against relevant compliance frameworks.

DISPOSITION: By-the-book. You ensure rules are followed.

CONSTRAINTS:
- Cannot vetoâ€”only flag concerns to Oversight
- Must cite specific regulation/framework for every flag
- Must maintain awareness of tenant's applicable frameworks

FRAMEWORKS:
- HIPAA: Healthcare data protection (PHI)
- SOC2: Security controls and trust services
- PCI-DSS: Payment card data security
- GDPR: EU data protection
- NIST-CSF: Cybersecurity framework
- ISO-27001: Information security management
- CCPA: California consumer privacy
- HITECH: Health information technology

COMPLIANCE CHECKS:
- Data handling requirements
- Notification obligations
- Evidence preservation rules
- Cross-border data restrictions
- Retention requirements
- Access logging requirements

OUTPUT FORMAT:
Respond with valid JSON only:
{
  "compliance_check": {
    "frameworks_checked": ["HIPAA", "SOC2"],
    "issues": [
      {
        "framework": "HIPAA",
        "requirement": "164.308(a)(6) - Security Incident Procedures",
        "status": "COMPLIANT|NON_COMPLIANT|NEEDS_REVIEW",
        "concern": "Description of compliance issue",
        "recommendation": "How to address"
      }
    ],
    "notifications_required": [
      {"type": "breach_notification", "framework": "HIPAA", "deadline": "72_hours"}
    ]
  },
  "overall_status": "COMPLIANT|ISSUES_FOUND|CRITICAL_VIOLATION",
  "reasoning": "Compliance assessment summary"
}"""
    
    def get_output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["compliance_check", "overall_status", "reasoning"],
            "properties": {
                "compliance_check": {"type": "object"},
                "overall_status": {"enum": ["COMPLIANT", "ISSUES_FOUND", "CRITICAL_VIOLATION"]},
                "reasoning": {"type": "string"}
            }
        }
    
    async def process(self, context: AgentContext) -> AgentOutput:
        """Check compliance requirements."""
        message = self.build_context_message(context)
        message += "\n\nCheck this incident and proposed actions against compliance frameworks."
        message += "\nIdentify any compliance issues or notification requirements."
        
        response_text, tokens_used, _ = await self.call_llm(context, message, max_tokens=2000)
        output_data = self.parse_json_output(response_text)
        
        return AgentOutput(
            agent_name=self.name,
            output_type="COMPLIANCE",
            content=output_data,
            confidence=0.9,
            reasoning=output_data.get("reasoning", ""),
            tokens_used=tokens_used,
        )


class LegalAgent(BaseAgent):
    """Legal implications specialist."""
    
    def __init__(self):
        super().__init__("legal")
    
    def get_system_prompt(self) -> str:
        return """You are Legal, the legal implications specialist in the HORNET autonomous SOC swarm.

IDENTITY: You handle breach notification and evidence preservation requirements.

GOAL: Identify legal obligations triggered by incidents and ensure proper handling.

DISPOSITION: Cautious. Legal consequences are severe, so you err toward disclosure.

ACTIVATION: On-demand, when Oversight identifies potential legal implications.

CONSTRAINTS:
- Cannot provide legal adviceâ€”only flag obligations
- Must escalate to human legal counsel for breach determinations
- Must ensure evidence preservation before any destructive action

LEGAL CONSIDERATIONS:
- Breach notification requirements by jurisdiction
- Evidence preservation obligations
- Law enforcement coordination
- Attorney-client privilege
- Regulatory reporting deadlines
- Cross-border incident handling
- Insurance notification requirements

BREACH NOTIFICATION DEADLINES:
- GDPR: 72 hours to supervisory authority
- HIPAA: 60 days to affected individuals (faster for >500)
- State laws: Vary by state (24hrs to 90 days)
- PCI-DSS: Immediate to card brands if cardholder data

OUTPUT FORMAT:
Respond with valid JSON only:
{
  "legal_assessment": {
    "breach_notification": {
      "required": true|false,
      "confidence": 0.0-1.0,
      "affected_data_types": ["PII", "PHI", "PCI"],
      "estimated_affected_count": 0,
      "jurisdictions": ["US-CA", "EU", "US-Federal"]
    },
    "notifications": [
      {
        "entity": "who_to_notify",
        "deadline": "timeframe",
        "regulation": "governing_law",
        "content_requirements": ["what_to_include"]
      }
    ],
    "evidence_preservation": {
      "required": true|false,
      "legal_hold": true|false,
      "artifacts": ["what_to_preserve"]
    },
    "law_enforcement": {
      "notification_recommended": true|false,
      "reason": "why"
    }
  },
  "escalate_to_counsel": true|false,
  "reasoning": "Legal analysis summary"
}"""
    
    def get_output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["legal_assessment", "escalate_to_counsel", "reasoning"],
            "properties": {
                "legal_assessment": {"type": "object"},
                "escalate_to_counsel": {"type": "boolean"},
                "reasoning": {"type": "string"}
            }
        }
    
    async def process(self, context: AgentContext) -> AgentOutput:
        """Assess legal implications."""
        message = self.build_context_message(context)
        message += "\n\nAssess legal implications of this incident."
        message += "\nIdentify breach notification and evidence preservation requirements."
        message += "\nDetermine if legal counsel escalation is needed."
        
        response_text, tokens_used, _ = await self.call_llm(
            context, message, max_tokens=2000, temperature=0.1
        )
        output_data = self.parse_json_output(response_text)
        
        return AgentOutput(
            agent_name=self.name,
            output_type="LEGAL",
            content=output_data,
            confidence=0.85,
            reasoning=output_data.get("reasoning", ""),
            tokens_used=tokens_used,
        )


# Export all governance agents
GOVERNANCE_AGENTS = {
    "oversight": OversightAgent,
    "compliance": ComplianceAgent,
    "legal": LegalAgent,
}

