"""HORNET MITRE ATT&CK Mappings"""
from typing import Dict, List
from dataclasses import dataclass


@dataclass
class Technique:
    id: str
    name: str
    tactic: str
    description: str
    detecting_agents: List[str]
    data_sources: List[str]
    platforms: List[str]


TECHNIQUES: Dict[str, Technique] = {
    "T1566": Technique("T1566", "Phishing", "initial-access", "Phishing messages", ["phisherman", "emailgateway", "vision"], ["Email Gateway"], ["Windows", "macOS", "Linux"]),
    "T1566.001": Technique("T1566.001", "Spearphishing Attachment", "initial-access", "Attachment phishing", ["phisherman", "sandbox"], ["Email Gateway", "File Monitoring"], ["Windows", "macOS", "Linux"]),
    "T1566.002": Technique("T1566.002", "Spearphishing Link", "initial-access", "Link phishing", ["phisherman", "vision", "waf"], ["Email Gateway", "Web Proxy"], ["Windows", "macOS", "Linux"]),
    "T1190": Technique("T1190", "Exploit Public-Facing Application", "initial-access", "Web app exploits", ["waf", "scanner"], ["Application Log"], ["Windows", "Linux"]),
    "T1078": Technique("T1078", "Valid Accounts", "initial-access", "Stolen credentials", ["gatekeeper", "behavioral", "identity"], ["Auth Logs"], ["Windows", "Linux", "Cloud"]),
    "T1059": Technique("T1059", "Command and Scripting Interpreter", "execution", "Script execution", ["endpoint", "hunter", "sandbox"], ["Process Monitoring"], ["Windows", "macOS", "Linux"]),
    "T1059.001": Technique("T1059.001", "PowerShell", "execution", "PowerShell execution", ["endpoint", "hunter"], ["PowerShell Logs"], ["Windows"]),
    "T1547": Technique("T1547", "Boot or Logon Autostart Execution", "persistence", "Autostart persistence", ["endpoint", "hunter"], ["Registry"], ["Windows", "macOS", "Linux"]),
    "T1055": Technique("T1055", "Process Injection", "privilege-escalation", "Process injection", ["endpoint", "hunter", "sandbox"], ["Process Monitoring"], ["Windows", "Linux"]),
    "T1003": Technique("T1003", "OS Credential Dumping", "credential-access", "Credential dump", ["endpoint", "hunter"], ["Process Monitoring"], ["Windows", "Linux"]),
    "T1003.001": Technique("T1003.001", "LSASS Memory", "credential-access", "LSASS dump", ["endpoint", "hunter"], ["Process Access"], ["Windows"]),
    "T1110": Technique("T1110", "Brute Force", "credential-access", "Brute force", ["gatekeeper", "behavioral"], ["Auth Logs"], ["Windows", "Linux", "Cloud"]),
    "T1021": Technique("T1021", "Remote Services", "lateral-movement", "Remote access", ["netwatch", "gatekeeper"], ["Auth Logs", "Network Traffic"], ["Windows", "Linux"]),
    "T1071": Technique("T1071", "Application Layer Protocol", "command-and-control", "C2 over app protocols", ["netwatch", "dns"], ["Network Traffic"], ["Windows", "Linux"]),
    "T1071.004": Technique("T1071.004", "DNS", "command-and-control", "DNS C2", ["dns", "netwatch"], ["DNS Logs"], ["Windows", "Linux"]),
    "T1041": Technique("T1041", "Exfiltration Over C2 Channel", "exfiltration", "Exfil over C2", ["dataguard", "netwatch"], ["Network Traffic"], ["Windows", "Linux"]),
    "T1486": Technique("T1486", "Data Encrypted for Impact", "impact", "Ransomware", ["endpoint", "hunter", "backup"], ["File Monitoring"], ["Windows", "Linux"]),
    "T1496": Technique("T1496", "Resource Hijacking", "impact", "Cryptomining", ["crypto", "endpoint"], ["Process Monitoring"], ["Windows", "Linux"]),
}


def get_technique(tid: str) -> Technique:
    return TECHNIQUES.get(tid)


def get_detecting_agents(tid: str) -> List[str]:
    t = TECHNIQUES.get(tid)
    return t.detecting_agents if t else []


def get_techniques_for_agent(agent: str) -> List[Technique]:
    return [t for t in TECHNIQUES.values() if agent in t.detecting_agents]


def get_coverage_score(agents: List[str]) -> float:
    covered = sum(1 for t in TECHNIQUES.values() if any(a in t.detecting_agents for a in agents))
    return covered / len(TECHNIQUES) if TECHNIQUES else 0.0


TACTIC_ORDER = ["initial-access", "execution", "persistence", "privilege-escalation", "defense-evasion", "credential-access", "discovery", "lateral-movement", "collection", "command-and-control", "exfiltration", "impact"]
