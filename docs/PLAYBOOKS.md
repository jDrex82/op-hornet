# HORNET Playbook Reference

## Playbook Structure

```yaml
id: PB-XXX-NNN
name: Human-readable name
description: What this playbook handles
triggers:
  - event.type.pattern
  - another.pattern
priority: LOW|MEDIUM|HIGH|CRITICAL
auto_approve_all: false
requires_oversight: true
steps:
  - order: 1
    action_type: action_name
    target: target_spec
    params: {}
    auto_approve: true/false
```

## Available Playbooks

### Authentication

| ID | Name | Triggers | Auto-Approve |
|----|------|----------|--------------|
| PB-AUTH-001 | Brute Force Response | auth.brute_force, auth.password_spray | Yes (block IP) |
| PB-AUTH-002 | Credential Stuffing | auth.credential_stuffing | No |
| PB-AUTH-003 | Impossible Travel | auth.impossible_travel | No |
| PB-AUTH-004 | MFA Bypass | auth.mfa_bypass | No |

### Malware

| ID | Name | Triggers | Auto-Approve |
|----|------|----------|--------------|
| PB-MALWARE-001 | Ransomware Response | endpoint.ransomware, malware.encryption | No |
| PB-MALWARE-002 | Generic Malware | endpoint.malware_detected | No |

### Email

| ID | Name | Triggers | Auto-Approve |
|----|------|----------|--------------|
| PB-EMAIL-001 | Phishing Response | email.phishing, email.malicious_link | Yes (quarantine) |
| PB-EMAIL-002 | BEC Response | email.bec, email.wire_fraud | No |

### Data Loss

| ID | Name | Triggers | Auto-Approve |
|----|------|----------|--------------|
| PB-DATA-001 | Exfiltration Response | dlp.exfiltration, dlp.mass_download | No |
| PB-DATA-002 | Sensitive Data Access | dlp.pii_access, dlp.financial_data | No |

### Network

| ID | Name | Triggers | Auto-Approve |
|----|------|----------|--------------|
| PB-NETWORK-001 | C2 Beacon Response | network.c2_beacon | No |
| PB-NETWORK-002 | Lateral Movement | network.lateral_movement | No |
| PB-NETWORK-003 | DDoS Response | network.ddos | Yes (rate limit) |
| PB-NETWORK-004 | DNS Tunnel | network.dns_tunnel | No |

### Cloud

| ID | Name | Triggers | Auto-Approve |
|----|------|----------|--------------|
| PB-CLOUD-001 | Public Exposure | cloud.public_s3, cloud.public_exposure | Yes (block) |
| PB-CLOUD-002 | IAM Escalation | cloud.iam_escalation | No |
| PB-CLOUD-003 | Container Escape | k8s.container_escape | No |

### Insider

| ID | Name | Triggers | Auto-Approve |
|----|------|----------|--------------|
| PB-INSIDER-001 | Insider Threat | insider.data_hoarding, insider.resignation_risk | No |

## Creating Custom Playbooks

1. Define triggers (event type patterns)
2. Set priority and oversight requirements
3. Define steps with actions
4. Configure auto-approve per step
5. Test with synthetic events
