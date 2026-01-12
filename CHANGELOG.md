# HORNET Changelog

## v2.0.0 (2024-01-15)

### Features
- 54-agent autonomous SOC swarm
- FSM-based incident coordination
- Multi-tier agent activation
- Token budget management (50K/incident)
- Veto authority for governance agents
- 23 automated response playbooks
- Real-time WebSocket dashboard
- MITRE ATT&CK mappings
- Behavioral baseline anomaly detection
- Vector similarity search for patterns

### Agents
- 10 Detection agents
- 2 Intelligence agents
- 3 Analysis agents
- 4 Action agents
- 3 Governance agents
- 3 Meta agents
- 16+ Specialist agents

### Integrations
- Log Sources: Cloudflare, AWS CloudTrail, Azure Activity, GCP Audit, M365, Defender, Syslog
- Action Connectors: Palo Alto, Okta, CrowdStrike, SentinelOne, AWS, Azure, GCP
- Notifications: Slack, PagerDuty, Email, Webhooks

### Infrastructure
- Docker Compose deployment
- Kubernetes manifests
- Helm chart
- GitHub Actions CI/CD
- Prometheus metrics
- OpenTelemetry tracing
- Grafana dashboards

### Security
- Multi-tenant isolation with RLS
- Per-tenant encryption
- Immutable audit logging
- Rate limiting
- API key authentication

### AI Safety
- Alignment research module
- Deception probing
- Confidence calibration
- Tuner feedback loop
