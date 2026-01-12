# 🐝 HORNET - Autonomous SOC Swarm

**54-Agent Security Operations Center powered by Claude**

HORNET is a fully autonomous security operations platform that uses a swarm of specialized AI agents to detect, investigate, and respond to security incidents with minimal human intervention.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           HORNET SWARM                                  │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │  DETECTION  │  │ INTELLIGENCE│  │  ANALYSIS   │  │   ACTION    │    │
│  │  (10 agents)│  │  (2 agents) │  │  (3 agents) │  │  (4 agents) │    │
│  │             │  │             │  │             │  │             │    │
│  │ Hunter      │  │ Intel       │  │ Analyst     │  │ Responder   │    │
│  │ Sentinel    │  │ Correlator  │  │ Triage      │  │ Deceiver    │    │
│  │ Behavioral  │  │             │  │ Forensics   │  │ Recovery    │    │
│  │ NetWatch    │  │             │  │             │  │ Playbook    │    │
│  │ Endpoint    │  │             │  │             │  │             │    │
│  │ Gatekeeper  │  │             │  │             │  │             │    │
│  │ DataGuard   │  │             │  │             │  │             │    │
│  │ Phisherman  │  │             │  │             │  │             │    │
│  │ CloudWatch  │  │             │  │             │  │             │    │
│  │ DNS         │  │             │  │             │  │             │    │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │
│                                                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌───────────────────────────────┐   │
│  │ GOVERNANCE  │  │    META     │  │        SPECIALISTS            │   │
│  │ (3 agents)  │  │ (3 agents)  │  │        (16 agents)            │   │
│  │             │  │             │  │                               │   │
│  │ Oversight ⚠ │  │ Router      │  │ Sandbox  Scanner  RedSim      │   │
│  │ Compliance  │  │ Memory      │  │ Vision   Social   Change      │   │
│  │ Legal       │  │ Health      │  │ Backup   Uptime   API         │   │
│  │             │  │             │  │ Container DarkWeb Physical    │   │
│  │ ⚠ = VETO   │  │             │  │ Supply   Surface  Tuner Synth │   │
│  └─────────────┘  └─────────────┘  └───────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │      FSM COORDINATOR          │
                    │                               │
                    │  IDLE → DETECTION → ENRICHMENT│
                    │    → ANALYSIS → PROPOSAL      │
                    │    → OVERSIGHT → EXECUTION    │
                    │    → CLOSED / ESCALATED       │
                    └───────────────────────────────┘
```

## Quick Start

### Docker Compose (Recommended)

```bash
# Clone and configure
cp .env.example .env
# Edit .env with your API keys

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f api

# Access dashboard
open http://localhost:8000/dashboard
```

### Kubernetes

```bash
# Create namespace and secrets
kubectl apply -f k8s/namespace.yaml
kubectl create secret generic hornet-secrets \
  --from-literal=ANTHROPIC_API_KEY=your_key \
  --from-literal=OPENAI_API_KEY=your_key \
  --from-literal=SECRET_KEY=your_secret \
  -n hornet

# Deploy
kubectl apply -f k8s/
```

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Start Redis and Postgres
docker run -d -p 6379:6379 redis:7-alpine
docker run -d -p 5432:5432 -e POSTGRES_USER=hornet -e POSTGRES_PASSWORD=hornet -e POSTGRES_DB=hornet pgvector/pgvector:pg16

# Run migrations
alembic upgrade head

# Start API
uvicorn hornet.main:app --reload

# Start worker (separate terminal)
python -m hornet.worker
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/events` | POST | Ingest security event |
| `/api/v1/events` | GET | List events |
| `/api/v1/incidents` | GET | List incidents |
| `/api/v1/incidents/{id}` | GET | Get incident details |
| `/api/v1/incidents/{id}/timeline` | GET | Get incident timeline |
| `/api/v1/incidents/{id}/actions/{action_id}/approve` | POST | Approve/reject action |
| `/api/v1/health` | GET | System health |
| `/api/v1/health/agents` | GET | Agent health |
| `/api/v1/config/thresholds` | GET/PUT | Detection thresholds |
| `/api/v1/webhooks/cloudflare` | POST | Cloudflare webhook |
| `/api/v1/webhooks/aws-sns` | POST | AWS SNS webhook |
| `/api/v1/ws/{tenant_id}` | WS | Real-time updates |
| `/dashboard` | GET | Web dashboard |
| `/metrics` | GET | Prometheus metrics |

## FSM States

| State | Description | Timeout |
|-------|-------------|---------|
| IDLE | Waiting for events | - |
| DETECTION | Detection agents analyzing | 15s |
| ENRICHMENT | Intel + correlation | 10s |
| ANALYSIS | Analyst verdict | 30s |
| PROPOSAL | Action planning | 20s |
| OVERSIGHT | Governance review | 30s |
| EXECUTION | Executing actions | 60s |
| ESCALATED | Human required | 30m |
| CLOSED | Resolved | - |

## Agent Layers

### Detection (10 agents)
- **Hunter**: APT detection, living-off-land, fileless malware
- **Sentinel**: Asset inventory, configuration drift, shadow IT
- **Behavioral**: UEBA, insider threats, z-score anomalies
- **NetWatch**: Network traffic, C2 beacons, lateral movement
- **Endpoint**: Process execution, persistence, memory injection
- **Gatekeeper**: Authentication, brute force, impossible travel
- **DataGuard**: DLP, exfiltration, mass downloads
- **Phisherman**: Email security, BEC, credential harvesting
- **CloudWatch**: Cloud misconfigurations, IAM abuse
- **DNS**: DNS tunneling, DGA detection

### Specialists (16 agents)
- **Sandbox**: Malware detonation analysis
- **Scanner**: Attack surface monitoring
- **RedSim**: Adversary simulation
- **Vision**: Image/screenshot analysis
- **Social**: Social engineering detection
- **Change**: Change management correlation
- **Backup**: Backup integrity verification
- **Uptime**: DDoS/availability monitoring
- **API**: API abuse detection
- **Container**: K8s/container security
- **DarkWeb**: Credential leak monitoring
- **Physical**: Physical security integration
- **Supply**: Supply chain risk
- **Surface**: Attack surface management
- **Tuner**: Detection threshold optimization
- **Synth**: Synthetic event generation

## Token Budget

Each incident has a 50,000 token budget:
- 80% warning
- 90% force transition to next state
- 95% close incident

## Veto Mechanics

Oversight agent has VETO AUTHORITY. Mandatory veto triggers:
1. PATIENT_SAFETY - Medical device/patient care impact
2. LEGAL_VIOLATION - Action would violate law
3. DISPROPORTIONATE - Severity exceeds threat by 2+ levels
4. COLLATERAL_DAMAGE - >100 uninvolved users/systems
5. EVIDENCE_DESTRUCTION - Would destroy evidence
6. PRIVACY_VIOLATION - Inappropriate data access

## Playbooks

| ID | Name | Auto-Approve | Priority |
|----|------|--------------|----------|
| PB-AUTH-001 | Brute Force | Yes | MEDIUM |
| PB-AUTH-003 | Impossible Travel | No | HIGH |
| PB-MALWARE-001 | Ransomware | No | CRITICAL |
| PB-EMAIL-001 | Phishing | Yes | MEDIUM |
| PB-DATA-001 | Exfiltration | No | CRITICAL |
| PB-NETWORK-001 | C2 Beacon | No | HIGH |
| PB-CLOUD-001 | Public Exposure | No | HIGH |

## Integrations

### Log Sources
- Cloudflare WAF
- AWS CloudTrail
- Azure Activity Logs
- GCP Audit Logs
- Microsoft 365
- Microsoft Defender
- Syslog

### Action Connectors
- Palo Alto Networks
- Okta
- CrowdStrike
- SentinelOne
- AWS (EC2, IAM, S3)
- Azure
- GCP

### Notifications
- Slack
- PagerDuty
- Email
- Webhooks

## Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=hornet

# Generate synthetic events
python scripts/synth.py --scenario brute_force -v

# Available scenarios
python scripts/synth.py --list
```

## Configuration

Key environment variables:

```bash
# Required
ANTHROPIC_API_KEY=your_key
OPENAI_API_KEY=your_key
SECRET_KEY=random_string
DATABASE_URL=postgresql+asyncpg://...
REDIS_URL=redis://...

# Optional
VIRUSTOTAL_API_KEY=
ABUSEIPDB_API_KEY=
SLACK_BOT_TOKEN=
PAGERDUTY_INTEGRATION_KEY=
```

## Research Mode

Enable alignment research logging:

```python
from hornet.research import research_logger
research_logger.enabled = True
research_logger.sampling_rate = 0.1  # 10% sampling

# Get summary
print(research_logger.get_summary())
```

## License

Proprietary - All rights reserved

## Support

For issues and questions, contact the HORNET team.
