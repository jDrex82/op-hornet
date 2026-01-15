"""
HORNET Base Agent
Abstract base class with full tool calling support.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any, Dict, List, Callable, Awaitable
from uuid import UUID, uuid4
from enum import Enum
import json
import asyncio
import structlog

from anthropic import AsyncAnthropic
import tiktoken

from hornet.config import get_settings, AGENT_CONFIG, MODEL_MAP


logger = structlog.get_logger()
settings = get_settings()


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class AgentContext:
    """Context passed to agents during processing."""
    incident_id: UUID = None
    tenant_id: UUID = None
    event_id: UUID = None
    event_data: Dict[str, Any] = field(default_factory=dict)
    entities: List[Dict[str, Any]] = field(default_factory=list)
    prior_findings: List[Dict[str, Any]] = field(default_factory=list)
    enrichments: List[Dict[str, Any]] = field(default_factory=list)
    token_budget_remaining: int = 50000
    timestamp: datetime = field(default_factory=datetime.utcnow)
    tool_results: Dict[str, Any] = field(default_factory=dict)
    # Aliases for coordinator compatibility
    state: str = None
    events: List[Dict[str, Any]] = field(default_factory=list)
    findings: List[Dict[str, Any]] = field(default_factory=list)
    token_budget: int = 50000
    tokens_used: int = 0


@dataclass
class AgentOutput:
    """Standardized output from an agent."""
    agent_name: str
    output_type: str
    content: Dict[str, Any]
    confidence: float
    reasoning: str
    tokens_used: int
    tool_calls_made: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    message_id: UUID = field(default_factory=uuid4)


@dataclass
class ToolDefinition:
    """Claude-format tool definition."""
    name: str
    description: str
    input_schema: Dict[str, Any]
    handler: Callable[..., Awaitable[Dict[str, Any]]]


# =============================================================================
# TOOL DEFINITIONS
# =============================================================================

class AgentTools:
    """Tool definitions available to agents."""
    
    @staticmethod
    def get_intel_tools() -> List[Dict[str, Any]]:
        """Threat intelligence tools."""
        return [
            {
                "name": "query_virustotal_ip",
                "description": "Query VirusTotal for IP reputation. Returns malicious score, country, ASN, and tags.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "ip": {"type": "string", "description": "IP address to query"}
                    },
                    "required": ["ip"]
                }
            },
            {
                "name": "query_virustotal_hash",
                "description": "Query VirusTotal for file hash reputation. Returns detection count, file type, and names.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "file_hash": {"type": "string", "description": "MD5, SHA1, or SHA256 hash"}
                    },
                    "required": ["file_hash"]
                }
            },
            {
                "name": "query_virustotal_domain",
                "description": "Query VirusTotal for domain reputation.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "domain": {"type": "string", "description": "Domain to query"}
                    },
                    "required": ["domain"]
                }
            },
            {
                "name": "query_abuseipdb",
                "description": "Query AbuseIPDB for IP abuse reports. Returns abuse score, report count, and ISP info.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "ip": {"type": "string", "description": "IP address to query"},
                        "max_age_days": {"type": "integer", "default": 90, "description": "Max age of reports"}
                    },
                    "required": ["ip"]
                }
            },
            {
                "name": "query_shodan",
                "description": "Query Shodan for host information. Returns open ports, vulnerabilities, and services.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "ip": {"type": "string", "description": "IP address to query"}
                    },
                    "required": ["ip"]
                }
            },
            {
                "name": "query_greynoise",
                "description": "Query GreyNoise to check if IP is mass scanner or targeted attack.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "ip": {"type": "string", "description": "IP address to query"}
                    },
                    "required": ["ip"]
                }
            },
            {
                "name": "enrich_ip",
                "description": "Enrich IP with ALL available intel sources (VirusTotal, AbuseIPDB, Shodan, GreyNoise).",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "ip": {"type": "string", "description": "IP address to enrich"}
                    },
                    "required": ["ip"]
                }
            },
            {
                "name": "enrich_domain",
                "description": "Enrich domain with VirusTotal, WHOIS, and DNS resolution.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "domain": {"type": "string", "description": "Domain to enrich"}
                    },
                    "required": ["domain"]
                }
            },
            {
                "name": "enrich_hash",
                "description": "Enrich file hash with VirusTotal and OTX.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "file_hash": {"type": "string", "description": "File hash to enrich"}
                    },
                    "required": ["file_hash"]
                }
            },
        ]
    
    @staticmethod
    def get_action_tools() -> List[Dict[str, Any]]:
        """Response action tools."""
        return [
            {
                "name": "block_ip",
                "description": "Block an IP address at the firewall. Specify duration in hours.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "ip": {"type": "string", "description": "IP to block"},
                        "duration_hours": {"type": "integer", "default": 24, "description": "Block duration in hours"},
                        "reason": {"type": "string", "description": "Reason for blocking"}
                    },
                    "required": ["ip"]
                }
            },
            {
                "name": "unblock_ip",
                "description": "Remove IP block from firewall.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "ip": {"type": "string", "description": "IP to unblock"}
                    },
                    "required": ["ip"]
                }
            },
            {
                "name": "isolate_host",
                "description": "Network isolate a compromised host. Host can only communicate with management.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "host_id": {"type": "string", "description": "Host ID or hostname"},
                        "reason": {"type": "string", "description": "Reason for isolation"}
                    },
                    "required": ["host_id"]
                }
            },
            {
                "name": "unisolate_host",
                "description": "Remove network isolation from host.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "host_id": {"type": "string", "description": "Host ID or hostname"}
                    },
                    "required": ["host_id"]
                }
            },
            {
                "name": "kill_process",
                "description": "Terminate a malicious process on a host.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "host_id": {"type": "string", "description": "Host ID"},
                        "pid": {"type": "integer", "description": "Process ID to kill"},
                        "reason": {"type": "string", "description": "Reason for termination"}
                    },
                    "required": ["host_id", "pid"]
                }
            },
            {
                "name": "quarantine_file",
                "description": "Quarantine a malicious file on a host.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "host_id": {"type": "string", "description": "Host ID"},
                        "file_path": {"type": "string", "description": "Full path to file"}
                    },
                    "required": ["host_id", "file_path"]
                }
            },
            {
                "name": "disable_user",
                "description": "Disable a user account to prevent further access.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string", "description": "User ID or email"},
                        "reason": {"type": "string", "description": "Reason for disabling"}
                    },
                    "required": ["user_id"]
                }
            },
            {
                "name": "revoke_sessions",
                "description": "Revoke all active sessions for a user.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string", "description": "User ID or email"}
                    },
                    "required": ["user_id"]
                }
            },
            {
                "name": "reset_mfa",
                "description": "Reset MFA for a user (forces re-enrollment).",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string", "description": "User ID or email"}
                    },
                    "required": ["user_id"]
                }
            },
            {
                "name": "force_password_reset",
                "description": "Force password reset for a user on next login.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string", "description": "User ID or email"}
                    },
                    "required": ["user_id"]
                }
            },
            {
                "name": "quarantine_email",
                "description": "Quarantine an email message.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "message_id": {"type": "string", "description": "Email message ID"},
                        "reason": {"type": "string", "description": "Reason for quarantine"}
                    },
                    "required": ["message_id"]
                }
            },
            {
                "name": "block_sender",
                "description": "Block an email sender organization-wide.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "sender": {"type": "string", "description": "Sender email or domain"},
                        "scope": {"type": "string", "enum": ["user", "organization"], "default": "organization"}
                    },
                    "required": ["sender"]
                }
            },
        ]
    
    @staticmethod
    def get_query_tools() -> List[Dict[str, Any]]:
        """Query and search tools."""
        return [
            {
                "name": "search_siem",
                "description": "Search SIEM for events matching a query.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "hours_back": {"type": "integer", "default": 24, "description": "Hours to search back"},
                        "limit": {"type": "integer", "default": 100, "description": "Max results"}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "get_user_activity",
                "description": "Get recent activity for a user.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string", "description": "User ID or email"},
                        "days": {"type": "integer", "default": 7, "description": "Days of history"}
                    },
                    "required": ["user_id"]
                }
            },
            {
                "name": "get_host_processes",
                "description": "Get running processes on a host.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "host_id": {"type": "string", "description": "Host ID"}
                    },
                    "required": ["host_id"]
                }
            },
            {
                "name": "dns_resolve",
                "description": "Resolve DNS records for a domain.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "domain": {"type": "string", "description": "Domain to resolve"},
                        "record_type": {"type": "string", "default": "A", "description": "Record type (A, AAAA, MX, etc)"}
                    },
                    "required": ["domain"]
                }
            },
            {
                "name": "reverse_dns",
                "description": "Reverse DNS lookup for an IP.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "ip": {"type": "string", "description": "IP address"}
                    },
                    "required": ["ip"]
                }
            },
            {
                "name": "whois_domain",
                "description": "WHOIS lookup for domain registration info.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "domain": {"type": "string", "description": "Domain to lookup"}
                    },
                    "required": ["domain"]
                }
            },
            {
                "name": "whois_ip",
                "description": "WHOIS lookup for IP registration info.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "ip": {"type": "string", "description": "IP to lookup"}
                    },
                    "required": ["ip"]
                }
            },
        ]
    
    @staticmethod
    def get_forensics_tools() -> List[Dict[str, Any]]:
        """Digital forensics tools."""
        return [
            {
                "name": "capture_memory",
                "description": "Capture memory dump from a host for forensic analysis.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "host_id": {"type": "string", "description": "Host ID"}
                    },
                    "required": ["host_id"]
                }
            },
            {
                "name": "capture_disk",
                "description": "Capture disk image from a host.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "host_id": {"type": "string", "description": "Host ID"},
                        "volumes": {"type": "array", "items": {"type": "string"}, "description": "Volume list"}
                    },
                    "required": ["host_id"]
                }
            },
            {
                "name": "collect_artifacts",
                "description": "Collect forensic artifacts (logs, registry, prefetch, etc) from host.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "host_id": {"type": "string", "description": "Host ID"},
                        "artifact_types": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Types: logs, registry, prefetch, browser, memory"
                        }
                    },
                    "required": ["host_id", "artifact_types"]
                }
            },
            {
                "name": "preserve_logs",
                "description": "Preserve logs for legal hold.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "sources": {"type": "array", "items": {"type": "string"}, "description": "Log sources"},
                        "start_time": {"type": "string", "description": "ISO timestamp"},
                        "end_time": {"type": "string", "description": "ISO timestamp"}
                    },
                    "required": ["sources", "start_time", "end_time"]
                }
            },
        ]
    
    @staticmethod
    def get_sandbox_tools() -> List[Dict[str, Any]]:
        """Malware sandbox tools."""
        return [
            {
                "name": "submit_to_sandbox",
                "description": "Submit a file hash to sandbox for detonation and analysis.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "file_hash": {"type": "string", "description": "File hash to submit"}
                    },
                    "required": ["file_hash"]
                }
            },
            {
                "name": "submit_url_to_sandbox",
                "description": "Submit a URL to sandbox for analysis.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "URL to analyze"}
                    },
                    "required": ["url"]
                }
            },
            {
                "name": "get_sandbox_report",
                "description": "Get sandbox analysis report for a submission.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "submission_id": {"type": "string", "description": "Sandbox submission ID"}
                    },
                    "required": ["submission_id"]
                }
            },
        ]
    
    @staticmethod
    def get_notification_tools() -> List[Dict[str, Any]]:
        """Notification and alerting tools."""
        return [
            {
                "name": "send_slack",
                "description": "Send a Slack notification.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "channel": {"type": "string", "description": "Slack channel"},
                        "message": {"type": "string", "description": "Message text"}
                    },
                    "required": ["channel", "message"]
                }
            },
            {
                "name": "send_email",
                "description": "Send an email notification.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "recipients": {"type": "array", "items": {"type": "string"}, "description": "Email addresses"},
                        "subject": {"type": "string", "description": "Email subject"},
                        "body": {"type": "string", "description": "Email body"}
                    },
                    "required": ["recipients", "subject", "body"]
                }
            },
            {
                "name": "page_oncall",
                "description": "Page the on-call team via PagerDuty.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "severity": {"type": "string", "enum": ["critical", "error", "warning", "info"]},
                        "title": {"type": "string", "description": "Alert title"},
                        "details": {"type": "string", "description": "Alert details"}
                    },
                    "required": ["severity", "title", "details"]
                }
            },
            {
                "name": "create_ticket",
                "description": "Create a ticket in the ticketing system.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Ticket title"},
                        "description": {"type": "string", "description": "Ticket description"},
                        "priority": {"type": "string", "enum": ["low", "medium", "high", "critical"]}
                    },
                    "required": ["title", "description"]
                }
            },
        ]
    
    @staticmethod
    def get_cloud_tools() -> List[Dict[str, Any]]:
        """Cloud security tools."""
        return [
            {
                "name": "aws_stop_instance",
                "description": "Stop an AWS EC2 instance.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "instance_id": {"type": "string", "description": "EC2 instance ID"},
                        "region": {"type": "string", "default": "us-east-1"}
                    },
                    "required": ["instance_id"]
                }
            },
            {
                "name": "aws_revoke_iam_keys",
                "description": "Revoke IAM access keys for a user.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "username": {"type": "string", "description": "IAM username"},
                        "access_key_id": {"type": "string", "description": "Access key to revoke"}
                    },
                    "required": ["username", "access_key_id"]
                }
            },
            {
                "name": "aws_block_s3_public",
                "description": "Block public access to an S3 bucket.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "bucket": {"type": "string", "description": "S3 bucket name"}
                    },
                    "required": ["bucket"]
                }
            },
            {
                "name": "azure_stop_vm",
                "description": "Stop an Azure VM.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "vm_name": {"type": "string", "description": "VM name"},
                        "resource_group": {"type": "string", "description": "Resource group"}
                    },
                    "required": ["vm_name", "resource_group"]
                }
            },
            {
                "name": "azure_disable_user",
                "description": "Disable an Azure AD user.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string", "description": "Azure AD user ID or UPN"}
                    },
                    "required": ["user_id"]
                }
            },
            {
                "name": "gcp_stop_instance",
                "description": "Stop a GCP compute instance.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "instance_name": {"type": "string"},
                        "project": {"type": "string"},
                        "zone": {"type": "string"}
                    },
                    "required": ["instance_name", "project", "zone"]
                }
            },
        ]
    
    @staticmethod
    def get_deception_tools() -> List[Dict[str, Any]]:
        """Deception and honeypot tools."""
        return [
            {
                "name": "deploy_honeypot",
                "description": "Deploy a honeypot to attract attackers.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "honeypot_type": {"type": "string", "enum": ["ssh", "rdp", "web", "smb", "ftp"]},
                        "location": {"type": "string", "description": "Network segment or host"}
                    },
                    "required": ["honeypot_type", "location"]
                }
            },
            {
                "name": "deploy_breadcrumb",
                "description": "Deploy a breadcrumb/canary credential.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "breadcrumb_type": {"type": "string", "enum": ["credential", "file", "token"]},
                        "target_host": {"type": "string", "description": "Host to place breadcrumb"},
                        "lure_data": {"type": "object", "description": "Fake credential or file info"}
                    },
                    "required": ["breadcrumb_type", "target_host"]
                }
            },
            {
                "name": "create_decoy_account",
                "description": "Create a decoy/canary account.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "username": {"type": "string", "description": "Decoy username"},
                        "account_type": {"type": "string", "enum": ["user", "service", "admin"]}
                    },
                    "required": ["username"]
                }
            },
        ]


# =============================================================================
# TOOL EXECUTOR
# =============================================================================

class ToolExecutor:
    """Execute tools and return results."""
    
    def __init__(self):
        self._handlers: Dict[str, Callable] = {}
        self._register_handlers()
    
    def _register_handlers(self):
        """Register all tool handlers."""
        from hornet.tools import (
            virustotal, abuseipdb, shodan, greynoise, otx,
            firewall, edr, identity, email, siem, dns, whois,
            sandbox, forensics, deception, notification, aws, azure, gcp,
            enrich_ip, enrich_domain, enrich_hash,
        )
        
        # Intel tools
        self._handlers["query_virustotal_ip"] = lambda ip: virustotal.query_ip(ip)
        self._handlers["query_virustotal_hash"] = lambda file_hash: virustotal.query_hash(file_hash)
        self._handlers["query_virustotal_domain"] = lambda domain: virustotal.query_domain(domain)
        self._handlers["query_abuseipdb"] = lambda ip, max_age_days=90: abuseipdb.check_ip(ip, max_age_days)
        self._handlers["query_shodan"] = lambda ip: shodan.lookup_ip(ip)
        self._handlers["query_greynoise"] = lambda ip: greynoise.check_ip(ip)
        self._handlers["enrich_ip"] = enrich_ip
        self._handlers["enrich_domain"] = enrich_domain
        self._handlers["enrich_hash"] = enrich_hash
        
        # Action tools
        self._handlers["block_ip"] = lambda ip, duration_hours=24, reason="": firewall.block_ip(ip, duration_hours, reason)
        self._handlers["unblock_ip"] = lambda ip: firewall.unblock_ip(ip)
        self._handlers["isolate_host"] = lambda host_id, reason="": edr.isolate_host(host_id, reason)
        self._handlers["unisolate_host"] = lambda host_id: edr.unisolate_host(host_id)
        self._handlers["kill_process"] = lambda host_id, pid, reason="": edr.kill_process(host_id, pid, reason)
        self._handlers["quarantine_file"] = lambda host_id, file_path: edr.quarantine_file(host_id, file_path)
        self._handlers["disable_user"] = lambda user_id, reason="": identity.disable_user(user_id, reason)
        self._handlers["revoke_sessions"] = lambda user_id: identity.revoke_sessions(user_id)
        self._handlers["reset_mfa"] = lambda user_id: identity.reset_mfa(user_id)
        self._handlers["force_password_reset"] = lambda user_id: identity.force_password_reset(user_id)
        self._handlers["quarantine_email"] = lambda message_id, reason="": email.quarantine_message(message_id, reason)
        self._handlers["block_sender"] = lambda sender, scope="organization": email.block_sender(sender, scope)
        
        # Query tools
        self._handlers["search_siem"] = lambda query, hours_back=24, limit=100: siem.search_events(query, limit=limit)
        self._handlers["get_user_activity"] = lambda user_id, days=7: identity.get_user_activity(user_id, days)
        self._handlers["get_host_processes"] = lambda host_id: edr.get_process_tree(host_id)
        self._handlers["dns_resolve"] = lambda domain, record_type="A": dns.resolve(domain, record_type)
        self._handlers["reverse_dns"] = lambda ip: dns.reverse_lookup(ip)
        self._handlers["whois_domain"] = lambda domain: whois.lookup_domain(domain)
        self._handlers["whois_ip"] = lambda ip: whois.lookup_ip(ip)
        
        # Forensics tools
        self._handlers["capture_memory"] = lambda host_id: forensics.capture_memory(host_id)
        self._handlers["capture_disk"] = lambda host_id, volumes=None: forensics.capture_disk(host_id, volumes)
        self._handlers["collect_artifacts"] = lambda host_id, artifact_types: edr.collect_artifacts(host_id, artifact_types)
        self._handlers["preserve_logs"] = lambda sources, start_time, end_time: forensics.preserve_logs(sources, start_time, end_time)
        
        # Sandbox tools
        self._handlers["submit_to_sandbox"] = lambda file_hash: sandbox.submit_file(file_hash)
        self._handlers["submit_url_to_sandbox"] = lambda url: sandbox.submit_url(url)
        self._handlers["get_sandbox_report"] = lambda submission_id: sandbox.get_report(submission_id)
        
        # Notification tools
        self._handlers["send_slack"] = lambda channel, message: notification.send_slack(channel, message)
        self._handlers["send_email"] = lambda recipients, subject, body: notification.send_email(recipients, subject, body)
        self._handlers["page_oncall"] = lambda severity, title, details: notification.page_oncall(severity, title, details)
        self._handlers["create_ticket"] = lambda title, description, priority="medium": notification.create_ticket(title, description, priority)
        
        # Cloud tools
        self._handlers["aws_stop_instance"] = lambda instance_id, region="us-east-1": aws.stop_instance(instance_id, region)
        self._handlers["aws_revoke_iam_keys"] = lambda username, access_key_id: aws.revoke_iam_keys(username, access_key_id)
        self._handlers["aws_block_s3_public"] = lambda bucket: aws.block_s3_public(bucket)
        self._handlers["azure_stop_vm"] = lambda vm_name, resource_group: azure.stop_vm(vm_name, resource_group)
        self._handlers["azure_disable_user"] = lambda user_id: azure.disable_aad_user(user_id)
        self._handlers["gcp_stop_instance"] = lambda instance_name, project, zone: gcp.stop_instance(instance_name, project, zone)
        
        # Deception tools
        self._handlers["deploy_honeypot"] = lambda honeypot_type, location: deception.deploy_honeypot(honeypot_type, location)
        self._handlers["deploy_breadcrumb"] = lambda breadcrumb_type, target_host, lure_data=None: deception.deploy_breadcrumb(breadcrumb_type, target_host, lure_data or {})
        self._handlers["create_decoy_account"] = lambda username, account_type="user": deception.create_decoy_account(username, account_type)
    
    async def execute(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool and return results."""
        handler = self._handlers.get(tool_name)
        if not handler:
            return {"error": f"Unknown tool: {tool_name}", "success": False}
        
        try:
            result = await handler(**arguments)
            # Handle single ToolResult
            if hasattr(result, 'success') and hasattr(result, 'data'):
                return {"success": result.success, "data": result.data, "source": getattr(result, 'source', ''), "error": getattr(result, 'error', None)}
            # Handle dict of ToolResults (e.g., from enrich_ip)
            elif isinstance(result, dict):
                converted = {}
                for k, v in result.items():
                    if hasattr(v, 'success') and hasattr(v, 'data'):
                        converted[k] = {"success": v.success, "data": v.data, "source": getattr(v, 'source', ''), "error": getattr(v, 'error', None)}
                    else:
                        converted[k] = v
                return {"success": True, "data": converted}
            else:
                return {"success": True, "data": result}
        except Exception as e:
            logger.error("tool_execution_error", tool=tool_name, error=str(e))
            return {"error": str(e), "success": False}


# Global executor
tool_executor = ToolExecutor()


# =============================================================================
# BASE AGENT CLASS
# =============================================================================

class BaseAgent(ABC):
    """Abstract base class for HORNET agents with full tool support."""
    
    def __init__(self, name: str):
        self.name = name
        self.config = AGENT_CONFIG.get(name, {"model": "haiku", "weight": 1.0, "max_findings": 3})
        self.model = MODEL_MAP.get(self.config["model"], settings.DEFAULT_MODEL)
        self.weight = self.config["weight"]
        self.max_findings = self.config["max_findings"]
        self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        self._tools: List[Dict[str, Any]] = []
        self._max_tool_calls = 10
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        pass
    
    @abstractmethod
    async def process(self, context: AgentContext) -> AgentOutput:
        pass
    
    @abstractmethod
    def get_output_schema(self) -> Dict[str, Any]:
        pass
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """Return tools available to this agent. Override in subclasses."""
        return self._tools
    
    def set_tools(self, tools: List[Dict[str, Any]]):
        """Set tools available to this agent."""
        self._tools = tools
    
    def count_tokens(self, text: str) -> int:
        return len(self.tokenizer.encode(text))
    
    async def call_llm(
        self,
        context: AgentContext,
        user_message: str,
        max_tokens: int = 2000,
        temperature: float = 0.3,
        use_tools: bool = True,
    ) -> tuple[str, int, List[str]]:
        """
        Make an LLM call with optional tool use.
        
        Returns:
            tuple: (response_text, tokens_used, tool_calls_made)
        """
        system_prompt = self.get_system_prompt()
        tools = self.get_tools() if use_tools else []
        
        messages = [{"role": "user", "content": user_message}]
        total_tokens = 0
        tool_calls_made = []
        
        for iteration in range(self._max_tool_calls + 1):
            try:
                kwargs = {
                    "model": self.model,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "system": system_prompt,
                    "messages": messages,
                }
                
                if tools:
                    kwargs["tools"] = tools
                
                response = await self.client.messages.create(**kwargs)
                total_tokens += response.usage.input_tokens + response.usage.output_tokens
                
                # Check if we need to handle tool calls
                if response.stop_reason == "tool_use":
                    # Process tool calls
                    assistant_content = response.content
                    messages.append({"role": "assistant", "content": assistant_content})
                    
                    tool_results = []
                    for block in assistant_content:
                        if block.type == "tool_use":
                            tool_name = block.name
                            tool_input = block.input
                            tool_calls_made.append(tool_name)
                            
                            logger.info(
                                "agent_tool_call",
                                agent=self.name,
                                tool=tool_name,
                                incident_id=str(context.incident_id),
                            )
                            
                            # Execute tool
                            result = await tool_executor.execute(tool_name, tool_input)
                            
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": json.dumps(result),
                            })
                    
                    messages.append({"role": "user", "content": tool_results})
                    continue
                
                # No more tool calls, get final response
                response_text = ""
                for block in response.content:
                    if hasattr(block, "text"):
                        response_text += block.text

                # NUDGE: If Claude is silent after tool calls, force JSON output
                if not response_text.strip() and tool_calls_made:
                    logger.info("llm_nudge_required", agent=self.name, incident_id=str(context.incident_id))
                    messages.append({"role": "user", "content": "Tool calls complete. Now provide your final response in the required JSON format only."})
                    nudge_response = await self.client.messages.create(
                        model=self.model, max_tokens=max_tokens, temperature=temperature,
                        system=system_prompt, messages=messages
                    )
                    total_tokens += nudge_response.usage.input_tokens + nudge_response.usage.output_tokens
                    for block in nudge_response.content:
                        if hasattr(block, "text"):
                            response_text += block.text
                
                logger.info(
                    "llm_call_complete",
                    agent=self.name,
                    incident_id=str(context.incident_id),
                    tokens_used=total_tokens,
                    tool_calls=len(tool_calls_made),
                )
                
                return response_text, total_tokens, tool_calls_made
                
            except Exception as e:
                logger.error(
                    "llm_call_failed",
                    agent=self.name,
                    incident_id=str(context.incident_id),
                    error=str(e),
                )
                raise
        
        # Max iterations reached
        return "", total_tokens, tool_calls_made
    
    def parse_json_output(self, text: str) -> Dict[str, Any]:
        """Parse JSON from LLM output with robust extraction."""
        import re
        
        if not text or not text.strip():
            raise ValueError("Empty response from LLM")
        
        # Sanitize control characters that break JSON parsing
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
        
        # Try markdown code block first
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            if end > start:
                text = text[start:end].strip()
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            if end > start:
                text = text[start:end].strip()
        
        # Try direct parse first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # Fallback: extract first JSON object using balanced braces
        try:
            start_idx = text.find('{')
            if start_idx >= 0:
                depth = 0
                for i, c in enumerate(text[start_idx:], start_idx):
                    if c == '{':
                        depth += 1
                    elif c == '}':
                        depth -= 1
                        if depth == 0:
                            return json.loads(text[start_idx:i+1])
        except json.JSONDecodeError as e:
            logger.error("json_parse_failed", agent=self.name, error=str(e))
            raise ValueError(f"Failed to parse JSON: {e}")
        
        raise ValueError(f"No valid JSON found in response")
    
    def validate_output(self, output: Dict[str, Any]) -> bool:
        """Validate output against schema."""
        import jsonschema
        try:
            jsonschema.validate(output, self.get_output_schema())
            return True
        except jsonschema.ValidationError as e:
            logger.error("output_validation_failed", agent=self.name, error=str(e))
            return False
    
    def build_context_message(self, context: AgentContext) -> str:
        """Build context message for LLM."""
        parts = [
            f"## Event Details",
            f"Event ID: {context.event_id}",
            f"Incident ID: {context.incident_id}",
            f"Timestamp: {context.timestamp.isoformat()}",
            f"Event Type: {context.event_data.get('event_type', 'unknown')}",
            f"Source: {context.event_data.get('source', 'unknown')}",
            f"Severity: {context.event_data.get('severity', 'unknown')}",
            "",
            "## Entities",
            json.dumps(context.entities, indent=2),
            "",
            "## Raw Payload",
            json.dumps(context.event_data.get('raw_payload', {}), indent=2),
        ]
        
        if context.prior_findings:
            parts.extend(["", "## Prior Findings", json.dumps(context.prior_findings, indent=2)])
        
        if context.enrichments:
            parts.extend(["", "## Enrichment Data", json.dumps(context.enrichments, indent=2)])
        
        if context.tool_results:
            parts.extend(["", "## Tool Results", json.dumps(context.tool_results, indent=2)])
        
        return "\n".join(parts)


# =============================================================================
# SPECIALIZED BASE CLASSES
# =============================================================================

class DetectionAgent(BaseAgent):
    """Base for Detection layer agents with intel tools."""
    
    def __init__(self, name: str):
        super().__init__(name)
        self.set_tools(AgentTools.get_intel_tools())
    
    def get_output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["findings", "reasoning"],
            "properties": {
                "findings": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["id", "description", "confidence", "evidence"],
                        "properties": {
                            "id": {"type": "string"},
                            "description": {"type": "string"},
                            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                            "severity": {"enum": ["LOW", "MEDIUM", "HIGH", "CRITICAL"]},
                            "entities": {"type": "array"},
                            "evidence": {"type": "array"},
                            "mitre": {"type": "string"},
                        }
                    }
                },
                "reasoning": {"type": "string"}
            }
        }
    
    async def process(self, context: AgentContext) -> AgentOutput:
        message = self.build_context_message(context)
        message += "\n\nAnalyze this event using available tools. Provide findings in JSON."
        
        response_text, tokens_used, tool_calls = await self.call_llm(context, message)
        output_data = self.parse_json_output(response_text)
        
        return AgentOutput(
            agent_name=self.name,
            output_type="FINDING",
            content=output_data,
            confidence=self._aggregate_confidence(output_data.get("findings", [])),
            reasoning=output_data.get("reasoning", ""),
            tokens_used=tokens_used,
            tool_calls_made=tool_calls,
        )
    
    def _aggregate_confidence(self, findings: List[Dict]) -> float:
        if not findings:
            return 0.0
        return max(f.get("confidence", 0.0) for f in findings)


class IntelligenceAgent(BaseAgent):
    """Base for Intelligence layer agents with full intel tools."""
    
    def __init__(self, name: str):
        super().__init__(name)
        self.set_tools(AgentTools.get_intel_tools() + AgentTools.get_query_tools())
    
    def get_output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["enrichments", "reasoning"],
            "properties": {
                "enrichments": {"type": "array"},
                "reasoning": {"type": "string"}
            }
        }


class AnalysisAgent(BaseAgent):
    """Base for Analysis layer agents."""
    
    def __init__(self, name: str):
        super().__init__(name)
        self.set_tools(AgentTools.get_query_tools())
    
    def get_output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["verdict", "confidence", "severity", "reasoning"],
            "properties": {
                "verdict": {"enum": ["CONFIRMED", "DISMISSED", "UNCERTAIN"]},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                "severity": {"enum": ["LOW", "MEDIUM", "HIGH", "CRITICAL"]},
                "summary": {"type": "string"},
                "mitre_techniques": {"type": "array"},
                "reasoning": {"type": "string"}
            }
        }


class ActionAgent(BaseAgent):
    """Base for Action layer agents with response tools."""
    
    def __init__(self, name: str):
        super().__init__(name)
        self.set_tools(
            AgentTools.get_action_tools() +
            AgentTools.get_cloud_tools() +
            AgentTools.get_notification_tools()
        )
    
    def get_output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["actions", "justification"],
            "properties": {
                "actions": {"type": "array"},
                "justification": {"type": "string"}
            }
        }


class GovernanceAgent(BaseAgent):
    """Base for Governance layer agents."""
    
    def __init__(self, name: str):
        super().__init__(name)
        # Governance agents don't execute tools, they review
        self.set_tools([])
    
    def get_output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["decision", "approved", "rejected", "reasoning"],
            "properties": {
                "decision": {"enum": ["APPROVE", "PARTIAL", "VETO"]},
                "approved": {"type": "array"},
                "rejected": {"type": "array"},
                "escalate": {"type": "boolean"},
                "reasoning": {"type": "string"}
            }
        }


class ForensicsAgent(BaseAgent):
    """Base for forensics-focused agents."""
    
    def __init__(self, name: str):
        super().__init__(name)
        self.set_tools(
            AgentTools.get_forensics_tools() +
            AgentTools.get_sandbox_tools() +
            AgentTools.get_query_tools()
        )
    
    def get_output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["artifacts", "timeline", "reasoning"],
            "properties": {
                "artifacts": {"type": "array"},
                "timeline": {"type": "array"},
                "iocs": {"type": "array"},
                "reasoning": {"type": "string"}
            }
        }


class DeceptionAgent(BaseAgent):
    """Base for deception-focused agents."""
    
    def __init__(self, name: str):
        super().__init__(name)
        self.set_tools(AgentTools.get_deception_tools())
    
    def get_output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["deployments", "reasoning"],
            "properties": {
                "deployments": {"type": "array"},
                "reasoning": {"type": "string"}
            }
        }




