# HORNET Architecture

## System Overview

HORNET is a 54-agent autonomous SOC powered by Claude. It processes security events through a finite state machine (FSM), orchestrating specialized AI agents to detect, investigate, and respond to security incidents.

## FSM States

| State | Description | Timeout |
|-------|-------------|---------|
| IDLE | Waiting for events | - |
| DETECTION | Running detection agents | 15s |
| ENRICHMENT | Gathering intelligence | 10s |
| ANALYSIS | Analyst verdict | 30s |
| PROPOSAL | Generating response | 20s |
| OVERSIGHT | Governance review | 30s |
| EXECUTION | Running actions | 60s |
| ESCALATED | Human required | 30m |
| CLOSED | Complete | - |

## Agent Layers

1. **Detection (10)**: Hunter, Sentinel, Behavioral, NetWatch, Endpoint, Gatekeeper, DataGuard, Phisherman, CloudWatch, DNS
2. **Intelligence (2)**: Intel, Correlator
3. **Analysis (3)**: Analyst, Triage, Forensics
4. **Action (4)**: Responder, Deceiver, Recovery, Playbook
5. **Governance (3)**: Oversight (VETO), Compliance, Legal
6. **Meta (3)**: Router, Memory, Health
7. **Specialists (16+)**: Sandbox, Vision, DarkWeb, Container, API, etc.

## Token Budget

50,000 tokens per incident with thresholds at 80% (warn), 90% (force transition), 95% (close).

## Veto Mechanics

Oversight agent has veto authority for: PATIENT_SAFETY, LEGAL_VIOLATION, DISPROPORTIONATE, COLLATERAL_DAMAGE, EVIDENCE_DESTRUCTION, PRIVACY_VIOLATION.
