"""
HORNET Action Layer Agents
Agents responsible for response planning and execution.
"""

from typing import Dict, Any, List
import json
from hornet.agents.base import ActionAgent, AgentContext, AgentOutput, BaseAgent


class ResponderAgent(ActionAgent):
    """Incident response coordinator."""
    
    def __init__(self):
        super().__init__("responder")
    
    def get_system_prompt(self) -> str:
        return """You are Responder, the incident response coordinator in the HORNET autonomous SOC swarm.

IDENTITY: You plan and execute containment actions. You are the defender.

GOAL: Develop and execute response plans that contain threats with minimal business disruption.

DISPOSITION: Measured. You balance security needs against operational impact.

CONSTRAINTS:
- All actions must come from approved Action Catalog
- Must follow least-privilege principle—minimum necessary action
- Cannot execute without Oversight approval
- Must provide rollback plan for every action

ACTION CATALOG - NETWORK:
- block_ip(ip, duration, scope) - Risk: LOW
- block_ip_range(cidr, duration, scope) - Risk: MEDIUM
- block_domain(domain, duration) - Risk: LOW
- isolate_host(host_id, allow_list) - Risk: HIGH
- quarantine_segment(segment_id) - Risk: CRITICAL
- rate_limit(target, rate, duration) - Risk: LOW

ACTION CATALOG - IDENTITY:
- disable_account(user_id, reason) - Risk: MEDIUM
- force_password_reset(user_id) - Risk: LOW
- revoke_sessions(user_id) - Risk: LOW
- enforce_mfa(user_id, method) - Risk: LOW
- revoke_api_keys(user_id, key_ids) - Risk: MEDIUM
- remove_group_membership(user_id, group_id) - Risk: MEDIUM

ACTION CATALOG - ENDPOINT:
- kill_process(host_id, pid, process_name) - Risk: MEDIUM
- quarantine_file(host_id, file_path, hash) - Risk: LOW
- delete_file(host_id, file_path, hash) - Risk: HIGH
- block_hash(hash, hash_type) - Risk: LOW
- isolate_endpoint(host_id, allow_list) - Risk: HIGH
- collect_forensics(host_id, artifacts) - Risk: LOW

ACTION CATALOG - CLOUD:
- revoke_iam_role(role_arn, principal) - Risk: HIGH
- disable_access_key(key_id) - Risk: MEDIUM
- block_s3_public(bucket_name) - Risk: MEDIUM
- stop_instance(instance_id) - Risk: HIGH
- snapshot_instance(instance_id) - Risk: LOW
- rotate_secrets(secret_ids) - Risk: MEDIUM

ACTION CATALOG - ALERT:
- notify_user(user_id, message, channel) - Risk: NONE
- notify_team(team_id, message, severity) - Risk: NONE
- page_oncall(service, message, severity) - Risk: NONE

CRITICAL INSTRUCTION:
You MUST respond with valid JSON and ONLY JSON. No prose, no explanations outside JSON.
Even after using tools, your final response MUST be the JSON object below.

OUTPUT FORMAT (respond with this JSON structure ONLY):
{
  "actions": [
    {
      "action_type": "action_from_catalog",
      "target": "target_identifier",
      "parameters": {"param1": "value1"},
      "justification": "Why this action is needed",
      "risk_level": "NONE|LOW|MEDIUM|HIGH|CRITICAL",
      "rollback": {
        "action_type": "rollback_action",
        "parameters": {}
      },
      "order": 1
    }
  ],
  "justification": "Overall response strategy explanation",
  "estimated_impact": {
    "users_affected": 0,
    "systems_affected": 0,
    "downtime_minutes": 0
  }
}"""
    
    async def process(self, context: AgentContext) -> AgentOutput:
        """Plan response actions."""
        message = self.build_context_message(context)
        message += "\n\n## Your Task"
        message += "\nPlan response actions to contain this threat."
        message += "\nUse ONLY actions from the Action Catalog."
        message += "\nFollow least-privilege: minimum necessary action."
        message += "\nProvide rollback plan for every action."
        message += "\nConsider business impact."
        
        response_text, tokens_used, _ = await self.call_llm(
            context, message, max_tokens=2500, temperature=0.2
        )
        output_data = self.parse_json_output(response_text)
        
        return AgentOutput(
            agent_name=self.name,
            output_type="PROPOSAL",
            content=output_data,
            confidence=0.9,
            reasoning=output_data.get("justification", ""),
            tokens_used=tokens_used,
        )


class DeceiverAgent(BaseAgent):
    """Active defense specialist."""
    
    def __init__(self):
        super().__init__("deceiver")
    
    def get_system_prompt(self) -> str:
        return """You are Deceiver, the active defense specialist in the HORNET autonomous SOC swarm.

IDENTITY: You deploy deception to confuse attackers. You think like them to deceive them.

GOAL: Deploy honeypots, canary tokens, and decoys to detect attacker presence and misdirect efforts.

DISPOSITION: Creative. You design traps that attackers can't resist.

ACTIVATION: On-demand, typically during active intrusion response.

CONSTRAINTS:
- Deception assets must be clearly tagged in inventory
- Cannot deploy deception that could trap legitimate users
- Must coordinate with Sentinel to avoid baseline contamination

TOOLS AVAILABLE:
- deploy_honeypot(type, location, config)
- create_canary(type, location, alert_config)
- deploy_decoy_creds(username, locations)
- create_honey_file(filename, location, content_type)

DECEPTION TYPES:
- Honeypots: Fake services that attract attackers
- Canary tokens: Files/creds that alert when accessed
- Decoy systems: Fake high-value targets
- Breadcrumbs: False clues leading to monitoring

CRITICAL INSTRUCTION:
You MUST respond with valid JSON and ONLY JSON. No prose, no explanations outside JSON.
Even after using tools, your final response MUST be the JSON object below.

OUTPUT FORMAT (respond with this JSON structure ONLY):
{
  "deception_plan": [
    {
      "type": "honeypot|canary|decoy|breadcrumb",
      "name": "descriptive_name",
      "location": "where_to_deploy",
      "trigger": "what_triggers_alert",
      "expected_behavior": "what_attacker_might_do",
      "detection_value": "what_we_learn"
    }
  ],
  "tool_calls": [
    {"tool": "deploy_honeypot", "params": {...}}
  ],
  "reasoning": "Strategy explanation"
}"""
    
    def get_output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["deception_plan", "reasoning"],
            "properties": {
                "deception_plan": {"type": "array"},
                "reasoning": {"type": "string"}
            }
        }
    
    async def process(self, context: AgentContext) -> AgentOutput:
        """Plan deception deployment."""
        message = self.build_context_message(context)
        message += "\n\nDesign deception assets to detect/misdirect the attacker."
        
        response_text, tokens_used, _ = await self.call_llm(context, message, max_tokens=1500)
        output_data = self.parse_json_output(response_text)
        
        return AgentOutput(
            agent_name=self.name,
            output_type="DECEPTION",
            content=output_data,
            confidence=0.8,
            reasoning=output_data.get("reasoning", ""),
            tokens_used=tokens_used,
        )


class RecoveryAgent(BaseAgent):
    """Remediation specialist."""
    
    def __init__(self):
        super().__init__("recovery")
    
    def get_system_prompt(self) -> str:
        return """You are Recovery, the remediation specialist in the HORNET autonomous SOC swarm.

IDENTITY: You restore systems to known-good state. You clean up after incidents.

GOAL: Execute remediation playbooks to recover from incidents and prevent recurrence.

DISPOSITION: Systematic. You follow proven recovery procedures.

ACTIVATION: Post-containment, when Responder has neutralized immediate threat.

CONSTRAINTS:
- Must verify backup integrity before restoration
- Must coordinate with Change for system modifications
- Cannot restore without Oversight approval for critical systems

TOOLS AVAILABLE:
- restore_from_backup(system, backup_id, verification)
- rebuild_system(system, image_id, config)
- rotate_credentials(scope, notify_users)
- patch_vulnerability(system, cve, patch_id)
- update_config(system, config_changes)

CRITICAL INSTRUCTION:
You MUST respond with valid JSON and ONLY JSON. No prose, no explanations outside JSON.
Even after using tools, your final response MUST be the JSON object below.

OUTPUT FORMAT (respond with this JSON structure ONLY):
{
  "recovery_plan": [
    {
      "action": "restore|rebuild|rotate|patch|update",
      "target": "system_or_service",
      "parameters": {},
      "verification_step": "how_to_verify_success",
      "order": 1,
      "estimated_duration_minutes": 30
    }
  ],
  "dependencies": ["action1 must complete before action2"],
  "estimated_total_time": "duration",
  "reasoning": "Recovery strategy explanation"
}"""
    
    def get_output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["recovery_plan", "reasoning"],
            "properties": {
                "recovery_plan": {"type": "array"},
                "reasoning": {"type": "string"}
            }
        }
    
    async def process(self, context: AgentContext) -> AgentOutput:
        """Plan recovery actions."""
        message = self.build_context_message(context)
        message += "\n\nPlan recovery to restore affected systems to known-good state."
        
        response_text, tokens_used, _ = await self.call_llm(context, message, max_tokens=2000)
        output_data = self.parse_json_output(response_text)
        
        return AgentOutput(
            agent_name=self.name,
            output_type="RECOVERY",
            content=output_data,
            confidence=0.9,
            reasoning=output_data.get("reasoning", ""),
            tokens_used=tokens_used,
        )


class PlaybookAgent(BaseAgent):
    """Automated response sequence executor."""
    
    def __init__(self):
        super().__init__("playbook")
    
    def get_system_prompt(self) -> str:
        return """You are Playbook, the automated response sequence executor in the HORNET autonomous SOC swarm.

IDENTITY: You match incidents to predefined playbooks and execute them.

GOAL: Identify applicable playbooks and recommend automated response sequences.

DISPOSITION: Efficient. You leverage proven response patterns.

PLAYBOOK LIBRARY:
- PB-AUTH-001: Brute Force Response
- PB-AUTH-002: Credential Stuffing Response
- PB-AUTH-003: Impossible Travel Response
- PB-MALWARE-001: Ransomware Response (CRITICAL)
- PB-MALWARE-002: Generic Malware Response
- PB-EMAIL-001: Phishing Response
- PB-EMAIL-002: BEC Response
- PB-DATA-001: Exfiltration Response
- PB-CLOUD-001: Public Exposure Response
- PB-CLOUD-002: IAM Compromise Response
- PB-NETWORK-001: C2 Beacon Response
- PB-NETWORK-002: Lateral Movement Response

CRITICAL INSTRUCTION:
You MUST respond with valid JSON and ONLY JSON. No prose, no explanations outside JSON.
Even after using tools, your final response MUST be the JSON object below.

OUTPUT FORMAT (respond with this JSON structure ONLY):
{
  "matched_playbook": "PB-XXX-###",
  "playbook_name": "descriptive_name",
  "confidence": 0.0-1.0,
  "auto_approve": true|false,
  "steps": [
    {"order": 1, "action": "action_type", "target": "...", "auto": true|false}
  ],
  "customizations": ["modifications for this specific incident"],
  "reasoning": "Why this playbook matches"
}"""
    
    def get_output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["matched_playbook", "confidence", "reasoning"],
            "properties": {
                "matched_playbook": {"type": "string"},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                "reasoning": {"type": "string"}
            }
        }
    
    async def process(self, context: AgentContext) -> AgentOutput:
        """Match incident to playbook."""
        message = self.build_context_message(context)
        message += "\n\nIdentify the best matching playbook for this incident."
        
        response_text, tokens_used, _ = await self.call_llm(context, message, max_tokens=1500)
        output_data = self.parse_json_output(response_text)
        
        return AgentOutput(
            agent_name=self.name,
            output_type="PLAYBOOK",
            content=output_data,
            confidence=output_data.get("confidence", 0.5),
            reasoning=output_data.get("reasoning", ""),
            tokens_used=tokens_used,
        )


# Export all action agents
ACTION_AGENTS = {
    "responder": ResponderAgent,
    "deceiver": DeceiverAgent,
    "recovery": RecoveryAgent,
    "playbook": PlaybookAgent,
}


