"""
HORNET Playbook Library
Predefined response sequences for common incident types.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum

class PlaybookPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

@dataclass
class PlaybookStep:
    order: int
    action_type: str
    target_template: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    condition: Optional[str] = None
    auto_approve: bool = False

@dataclass
class Playbook:
    id: str
    name: str
    description: str
    triggers: List[str]
    priority: PlaybookPriority
    steps: List[PlaybookStep]
    auto_approve_all: bool = False
    requires_oversight: bool = True

PLAYBOOKS: Dict[str, Playbook] = {
    "PB-AUTH-001": Playbook(
        id="PB-AUTH-001", name="Brute Force Response",
        description="Block source IP and secure targeted account",
        triggers=["auth.brute_force", "auth.login_failure"],
        priority=PlaybookPriority.MEDIUM, auto_approve_all=True, requires_oversight=False,
        steps=[
            PlaybookStep(1, "block_ip", "{source_ip}", {"duration": "24h"}, auto_approve=True),
            PlaybookStep(2, "force_password_reset", "{target_user}", condition="is_privileged"),
            PlaybookStep(3, "revoke_sessions", "{target_user}", condition="is_privileged", auto_approve=True),
            PlaybookStep(4, "notify_user", "{target_user}", {"message": "Brute force attempt detected"}, auto_approve=True),
        ],
    ),
    "PB-MALWARE-001": Playbook(
        id="PB-MALWARE-001", name="Ransomware Response",
        description="CRITICAL: Isolate and contain ransomware spread",
        triggers=["endpoint.ransomware_behavior", "endpoint.mass_encryption"],
        priority=PlaybookPriority.CRITICAL, auto_approve_all=False, requires_oversight=True,
        steps=[
            PlaybookStep(1, "isolate_endpoint", "{affected_host}", {"allow_list": ["soc_ip"]}, auto_approve=True),
            PlaybookStep(2, "quarantine_segment", "{network_segment}", condition="spread_detected"),
            PlaybookStep(3, "page_oncall", "incident_commander", {"severity": "CRITICAL"}, auto_approve=True),
            PlaybookStep(4, "snapshot_instance", "{affected_host}", {}, auto_approve=True),
        ],
    ),
    "PB-EMAIL-001": Playbook(
        id="PB-EMAIL-001", name="Phishing Response",
        description="Quarantine phishing email and protect users",
        triggers=["email.phishing_detected"],
        priority=PlaybookPriority.MEDIUM, auto_approve_all=True,
        steps=[
            PlaybookStep(1, "quarantine_email", "{message_id}", {}, auto_approve=True),
            PlaybookStep(2, "block_sender", "{sender_email}", {}, auto_approve=True),
            PlaybookStep(3, "block_domain", "{sender_domain}", condition="domain_suspicious", auto_approve=True),
        ],
    ),
    "PB-DATA-001": Playbook(
        id="PB-DATA-001", name="Exfiltration Response",
        description="Stop active data exfiltration",
        triggers=["data.exfiltration_attempt", "network.data_exfil"],
        priority=PlaybookPriority.CRITICAL, auto_approve_all=False, requires_oversight=True,
        steps=[
            PlaybookStep(1, "block_ip", "{destination_ip}", {"duration": "permanent"}, condition="in_progress", auto_approve=True),
            PlaybookStep(2, "isolate_endpoint", "{source_host}", {}, condition="in_progress", auto_approve=True),
            PlaybookStep(3, "disable_account", "{source_user}", {"reason": "Data exfiltration"}),
            PlaybookStep(4, "page_oncall", "security_manager", {"severity": "CRITICAL"}, auto_approve=True),
        ],
    ),
    "PB-NETWORK-001": Playbook(
        id="PB-NETWORK-001", name="C2 Beacon Response",
        description="Block command and control communication",
        triggers=["network.c2_beacon"],
        priority=PlaybookPriority.HIGH,
        steps=[
            PlaybookStep(1, "block_domain", "{c2_domain}", {}, auto_approve=True),
            PlaybookStep(2, "block_ip", "{c2_ip}", {"duration": "permanent"}, auto_approve=True),
            PlaybookStep(3, "isolate_endpoint", "{infected_host}", {}, auto_approve=True),
        ],
    ),
}

def get_playbook(playbook_id: str) -> Optional[Playbook]:
    return PLAYBOOKS.get(playbook_id)

def match_playbook(event_type: str) -> List[Playbook]:
    matches = [p for p in PLAYBOOKS.values() if event_type in p.triggers]
    return sorted(matches, key=lambda p: p.priority.value, reverse=True)


# Additional playbooks
ADDITIONAL_PLAYBOOKS = {
    "PB-AUTH-003": Playbook(
        id="PB-AUTH-003", name="Impossible Travel Response",
        description="Secure account with suspicious location activity",
        triggers=["auth.impossible_travel"],
        priority=PlaybookPriority.HIGH,
        steps=[
            PlaybookStep(1, "revoke_sessions", "{target_user}", auto_approve=True),
            PlaybookStep(2, "enforce_mfa", "{target_user}", {"method": "push"}, auto_approve=True),
            PlaybookStep(3, "notify_user", "{target_user}", {"message": "Unusual login location"}),
            PlaybookStep(4, "page_oncall", "security", {"severity": "HIGH"}),
        ],
    ),
    "PB-AUTH-004": Playbook(
        id="PB-AUTH-004", name="MFA Bypass Response",
        description="Respond to MFA bypass attempts",
        triggers=["auth.mfa_bypass"],
        priority=PlaybookPriority.HIGH,
        steps=[
            PlaybookStep(1, "disable_account", "{target_user}", {"reason": "MFA bypass attempt"}),
            PlaybookStep(2, "revoke_sessions", "{target_user}", auto_approve=True),
            PlaybookStep(3, "page_oncall", "security", {"severity": "HIGH"}),
        ],
    ),
    "PB-MALWARE-002": Playbook(
        id="PB-MALWARE-002", name="Generic Malware Response",
        description="Quarantine malware and clean endpoint",
        triggers=["endpoint.malware_detected"],
        priority=PlaybookPriority.MEDIUM, auto_approve_all=True,
        steps=[
            PlaybookStep(1, "quarantine_file", "{malware_path}", {"hash": "{file_hash}"}, auto_approve=True),
            PlaybookStep(2, "kill_process", "{affected_host}", {"pid": "{malware_pid}"}, auto_approve=True),
            PlaybookStep(3, "block_hash", "{file_hash}", {}, auto_approve=True),
            PlaybookStep(4, "notify_user", "{affected_user}", {"message": "Malware removed"}),
        ],
    ),
    "PB-EMAIL-002": Playbook(
        id="PB-EMAIL-002", name="BEC Response",
        description="Business Email Compromise response",
        triggers=["email.bec_attempt"],
        priority=PlaybookPriority.HIGH,
        steps=[
            PlaybookStep(1, "quarantine_email", "{message_id}", auto_approve=True),
            PlaybookStep(2, "notify_user", "{recipient}", {"message": "BEC attempt blocked"}),
            PlaybookStep(3, "notify_team", "finance", {"severity": "HIGH"}),
            PlaybookStep(4, "page_oncall", "security", {"severity": "HIGH"}),
        ],
    ),
    "PB-CLOUD-003": Playbook(
        id="PB-CLOUD-003", name="Container Escape Response",
        description="Respond to container escape attempt",
        triggers=["cloud.container_escape"],
        priority=PlaybookPriority.CRITICAL,
        steps=[
            PlaybookStep(1, "isolate_endpoint", "{container_host}", auto_approve=True),
            PlaybookStep(2, "stop_instance", "{container_id}", auto_approve=True),
            PlaybookStep(3, "page_oncall", "platform", {"severity": "CRITICAL"}),
            PlaybookStep(4, "collect_forensics", "{container_host}", {"artifacts": ["memory", "logs"]}),
        ],
    ),
    "PB-NETWORK-003": Playbook(
        id="PB-NETWORK-003", name="DDoS Response",
        description="Mitigate DDoS attack",
        triggers=["network.ddos"],
        priority=PlaybookPriority.CRITICAL, auto_approve_all=True,
        steps=[
            PlaybookStep(1, "rate_limit", "{target_service}", {"rate": "emergency"}, auto_approve=True),
            PlaybookStep(2, "block_ip_range", "{attack_sources}", {"duration": "4h"}, auto_approve=True),
            PlaybookStep(3, "page_oncall", "noc", {"severity": "CRITICAL"}),
            PlaybookStep(4, "notify_team", "status_page", {"message": "Mitigating attack"}),
        ],
    ),
    "PB-NETWORK-004": Playbook(
        id="PB-NETWORK-004", name="DNS Tunnel Response",
        description="Block DNS tunneling",
        triggers=["network.dns_tunnel"],
        priority=PlaybookPriority.HIGH,
        steps=[
            PlaybookStep(1, "block_domain", "{tunnel_domain}", auto_approve=True),
            PlaybookStep(2, "isolate_endpoint", "{source_host}", auto_approve=True),
            PlaybookStep(3, "collect_forensics", "{source_host}", {"artifacts": ["dns_logs", "memory"]}),
        ],
    ),
    "PB-INSIDER-001": Playbook(
        id="PB-INSIDER-001", name="Insider Threat Response",
        description="Respond to insider threat indicators",
        triggers=["data.insider_threat", "behavioral.insider_threat"],
        priority=PlaybookPriority.HIGH, requires_oversight=True,
        steps=[
            PlaybookStep(1, "preserve_logs", "{user_id}", {"days": 90}, auto_approve=True),
            PlaybookStep(2, "notify_team", "hr_security", {"severity": "HIGH"}),
            PlaybookStep(3, "page_oncall", "security_manager", {"severity": "HIGH"}),
        ],
    ),
    "PB-SUPPLY-001": Playbook(
        id="PB-SUPPLY-001", name="Third-Party Breach Response",
        description="Respond to vendor/supply chain breach",
        triggers=["supply.vendor_breach", "supply.third_party_compromise"],
        priority=PlaybookPriority.HIGH,
        steps=[
            PlaybookStep(1, "revoke_api_keys", "{vendor_keys}", auto_approve=True),
            PlaybookStep(2, "rotate_secrets", "{vendor_secrets}", auto_approve=True),
            PlaybookStep(3, "block_ip_range", "{vendor_ips}", {"duration": "24h"}),
            PlaybookStep(4, "page_oncall", "vendor_management", {"severity": "HIGH"}),
        ],
    ),
    "PB-API-001": Playbook(
        id="PB-API-001", name="API Abuse Response",
        description="Mitigate API abuse",
        triggers=["cloud.api_abuse", "api.abuse"],
        priority=PlaybookPriority.MEDIUM, auto_approve_all=True,
        steps=[
            PlaybookStep(1, "rate_limit", "{api_endpoint}", {"rate": "strict"}, auto_approve=True),
            PlaybookStep(2, "revoke_api_keys", "{abusing_keys}", auto_approve=True),
            PlaybookStep(3, "notify_team", "api_ops", {"severity": "MEDIUM"}),
        ],
    ),
    "PB-PHYSICAL-001": Playbook(
        id="PB-PHYSICAL-001", name="Physical Intrusion Response",
        description="Respond to physical-cyber attack chain",
        triggers=["physical.intrusion", "physical.tailgating"],
        priority=PlaybookPriority.HIGH,
        steps=[
            PlaybookStep(1, "disable_account", "{badge_holder}", {"reason": "Physical security event"}),
            PlaybookStep(2, "notify_team", "physical_security", {"severity": "HIGH"}),
            PlaybookStep(3, "page_oncall", "facility_security", {"severity": "HIGH"}),
        ],
    ),
    "PB-CRYPTO-001": Playbook(
        id="PB-CRYPTO-001", name="Cryptominer Response",
        description="Remove cryptomining malware",
        triggers=["endpoint.cryptominer"],
        priority=PlaybookPriority.MEDIUM, auto_approve_all=True,
        steps=[
            PlaybookStep(1, "kill_process", "{miner_process}", auto_approve=True),
            PlaybookStep(2, "quarantine_file", "{miner_path}", auto_approve=True),
            PlaybookStep(3, "block_domain", "{pool_domain}", auto_approve=True),
            PlaybookStep(4, "notify_user", "{affected_user}", {"message": "Cryptominer removed"}),
        ],
    ),
}

# Merge additional playbooks
PLAYBOOKS.update(ADDITIONAL_PLAYBOOKS)


# Additional playbooks
PLAYBOOKS["PB-CLOUD-004"] = Playbook(
    id="PB-CLOUD-004",
    name="Suspicious IAM Activity",
    description="Respond to suspicious IAM/RBAC changes",
    triggers=["cloud.iam_escalation", "cloud.role_assumption", "cloud.policy_change"],
    priority=PlaybookPriority.HIGH,
    requires_oversight=True,
    steps=[
        PlaybookStep(1, "audit", "Gather IAM change history", {"time_range": "24h"}),
        PlaybookStep(2, "identity", "Review affected identities", {}),
        PlaybookStep(3, "rollback", "Revert unauthorized changes", {}, auto_approve=False),
    ],
)

PLAYBOOKS["PB-NETWORK-005"] = Playbook(
    id="PB-NETWORK-005",
    name="Suspicious Outbound Traffic",
    description="Investigate unusual outbound connections",
    triggers=["network.unusual_destination", "network.high_volume", "network.suspicious_port"],
    priority=PlaybookPriority.MEDIUM,
    steps=[
        PlaybookStep(1, "netflow", "Capture traffic sample", {"duration": "5m"}),
        PlaybookStep(2, "reputation", "Check destination reputation", {}),
        PlaybookStep(3, "block_ip", "Block suspicious destination", {}, auto_approve=False),
    ],
)

PLAYBOOKS["PB-ENDPOINT-001"] = Playbook(
    id="PB-ENDPOINT-001",
    name="Suspicious Process Execution",
    description="Respond to suspicious process activity",
    triggers=["endpoint.lolbin", "endpoint.unusual_parent", "endpoint.script_execution"],
    priority=PlaybookPriority.HIGH,
    steps=[
        PlaybookStep(1, "collect_forensics", "Gather process artifacts", {"include_memory": True}),
        PlaybookStep(2, "sandbox_hash", "Submit to sandbox", {}),
        PlaybookStep(3, "kill_process", "Terminate process", {}, auto_approve=False),
        PlaybookStep(4, "isolate_host", "Network isolate host", {}, auto_approve=False),
    ],
)

PLAYBOOKS["PB-IDENTITY-001"] = Playbook(
    id="PB-IDENTITY-001",
    name="Compromised Account",
    description="Respond to suspected account compromise",
    triggers=["auth.password_spray_success", "auth.credential_leak", "auth.session_hijack"],
    priority=PlaybookPriority.CRITICAL,
    requires_oversight=True,
    steps=[
        PlaybookStep(1, "revoke_sessions", "Terminate all sessions", {"scope": "user"}),
        PlaybookStep(2, "reset_password", "Force password reset", {}),
        PlaybookStep(3, "mfa_reset", "Reset MFA tokens", {}),
        PlaybookStep(4, "audit_activity", "Review recent activity", {"time_range": "7d"}),
        PlaybookStep(5, "notify_user", "Contact user", {}),
    ],
)

PLAYBOOKS["PB-DATA-002"] = Playbook(
    id="PB-DATA-002",
    name="Sensitive Data Access",
    description="Respond to unauthorized sensitive data access",
    triggers=["dlp.pii_access", "dlp.financial_data", "dlp.source_code"],
    priority=PlaybookPriority.HIGH,
    requires_oversight=True,
    steps=[
        PlaybookStep(1, "audit_access", "Review access patterns", {}),
        PlaybookStep(2, "revoke_access", "Remove data access", {}, auto_approve=False),
        PlaybookStep(3, "legal_notify", "Notify legal team", {}),
    ],
)

PLAYBOOKS["PB-CONTAINER-001"] = Playbook(
    id="PB-CONTAINER-001",
    name="Container Security Event",
    description="Respond to container/K8s security events",
    triggers=["k8s.privileged_pod", "k8s.host_mount", "container.escape_attempt"],
    priority=PlaybookPriority.CRITICAL,
    steps=[
        PlaybookStep(1, "pod_forensics", "Collect pod state", {}),
        PlaybookStep(2, "delete_pod", "Terminate compromised pod", {}, auto_approve=False),
        PlaybookStep(3, "network_policy", "Apply restrictive network policy", {}),
        PlaybookStep(4, "node_cordon", "Cordon affected node", {}, auto_approve=False),
    ],
)
