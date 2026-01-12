# HORNET Agent Reference

## Agent Layers

### Detection Layer (10 Agents)

| Agent | Purpose | Key Capabilities |
|-------|---------|------------------|
| Hunter | APT/Advanced threat detection | LOLBins, fileless malware, living-off-land |
| Sentinel | Asset inventory & drift | Shadow IT, configuration changes |
| Behavioral | UEBA anomaly detection | Baseline deviation, insider threats |
| NetWatch | Network traffic analysis | C2 beacons, lateral movement, tunneling |
| Endpoint | Process/file monitoring | Execution chains, persistence, injection |
| Gatekeeper | Authentication security | Brute force, impossible travel, MFA bypass |
| DataGuard | Data loss prevention | Exfiltration, mass download, sensitive data |
| Phisherman | Email security | Phishing, BEC, credential harvesting |
| CloudWatch | Cloud security | Misconfigurations, IAM abuse, public exposure |
| DNS | DNS security | Tunneling, DGA, malicious domains |

### Intelligence Layer (2 Agents)

| Agent | Purpose | Key Capabilities |
|-------|---------|------------------|
| Intel | Threat intelligence | IOC enrichment, TTP mapping, actor attribution |
| Correlator | Event correlation | Pattern matching, kill chain mapping |

### Analysis Layer (3 Agents)

| Agent | Purpose | Key Capabilities |
|-------|---------|------------------|
| Analyst | Verdict determination | Evidence synthesis, confidence scoring |
| Triage | Priority assessment | Impact analysis, urgency scoring |
| Forensics | Deep investigation | Artifact collection, timeline reconstruction |

### Action Layer (4 Agents)

| Agent | Purpose | Key Capabilities |
|-------|---------|------------------|
| Responder | Response planning | Action proposal, playbook selection |
| Deceiver | Deception deployment | Honeypots, breadcrumbs, decoy accounts |
| Recovery | Incident recovery | Backup verification, restoration planning |
| Playbook | Playbook execution | Step orchestration, condition evaluation |

### Governance Layer (3 Agents)

| Agent | Purpose | Key Capabilities |
|-------|---------|------------------|
| Oversight | Veto authority | Action review, constraint enforcement |
| Compliance | Regulatory mapping | Framework alignment, reporting requirements |
| Legal | Legal assessment | Evidence preservation, notification requirements |

### Meta Layer (3 Agents)

| Agent | Purpose | Key Capabilities |
|-------|---------|------------------|
| Router | Agent activation | Workload distribution, tier management |
| Memory | Context management | Cross-incident correlation, pattern learning |
| Health | System monitoring | Agent health, performance metrics |

### Specialist Layer (16+ Agents)

| Agent | Purpose | Key Capabilities |
|-------|---------|------------------|
| Sandbox | Malware analysis | Detonation, behavioral analysis, IOC extraction |
| Scanner | Attack surface | External reconnaissance, port scanning |
| RedSim | Adversary simulation | Detection validation, evasion testing |
| Vision | Visual analysis | Screenshot analysis, brand impersonation |
| Social | Social engineering | Pretexting detection, authority exploitation |
| Change | Change correlation | Authorized vs unauthorized changes |
| Backup | Backup security | Integrity verification, recovery readiness |
| Uptime | Availability | DDoS detection, service monitoring |
| API | API security | Abuse detection, BOLA/IDOR |
| Container | K8s security | Escape detection, RBAC abuse |
| DarkWeb | Underground monitoring | Credential leaks, threat actor tracking |
| Physical | Physical security | Badge access, tailgating correlation |
| Supply | Supply chain | Third-party risk, dependency vulnerabilities |
| Surface | Shadow IT | Forgotten assets, subdomain discovery |
| Tuner | Threshold optimization | FP/FN analysis, auto-tuning |
| Synth | Test generation | Synthetic events for validation |

## Agent Output Format

All agents output structured JSON:

```json
{
  "findings": [
    {
      "id": "uuid",
      "description": "What was detected",
      "confidence": 0.0-1.0,
      "severity": "LOW|MEDIUM|HIGH|CRITICAL",
      "evidence": {...},
      "mitre_techniques": ["T1055", "T1003"],
      "entities": [{"type": "ip", "value": "..."}],
      "recommended_actions": [...]
    }
  ],
  "reasoning": "Step-by-step analysis explanation"
}
```

## Agent Activation Rules

1. **Router** always runs first
2. **Detection agents** activated based on event type
3. **Analysis agents** activated if confidence > threshold
4. **Action agents** activated if verdict is malicious
5. **Oversight** always reviews actions before execution
