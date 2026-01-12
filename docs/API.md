# HORNET API Reference

## Authentication

All API requests require an API key:

```
X-API-Key: hnt_your_api_key_here
```

Or Authorization header:
```
Authorization: Bearer hnt_your_api_key_here
```

## Endpoints

### Health

```
GET /api/v1/health
GET /api/v1/health/ready
GET /api/v1/health/live
GET /api/v1/health/agents
```

### Events

```
POST /api/v1/events
POST /api/v1/events/batch
GET  /api/v1/events
GET  /api/v1/events/{event_id}
```

### Incidents

```
GET  /api/v1/incidents
GET  /api/v1/incidents/{incident_id}
GET  /api/v1/incidents/{incident_id}/timeline
POST /api/v1/incidents/{incident_id}/actions/{action_id}/approve
POST /api/v1/incidents/{incident_id}/escalate
POST /api/v1/incidents/{incident_id}/close
```

### Configuration

```
GET  /api/v1/config/thresholds
PUT  /api/v1/config/thresholds
GET  /api/v1/config/agents
GET  /api/v1/config/playbooks
GET  /api/v1/config/playbooks/{playbook_id}
```

### Webhooks

```
POST /api/v1/webhooks/cloudflare
POST /api/v1/webhooks/aws-sns
POST /api/v1/webhooks/generic
```

### WebSocket

```
WS /api/v1/ws/{tenant_id}
```

### Metrics

```
GET /metrics
```

## Event Ingestion

```json
POST /api/v1/events
{
  "event_type": "auth.brute_force",
  "source": "auth_gateway",
  "source_type": "siem",
  "severity": "HIGH",
  "timestamp": "2024-01-15T14:30:00Z",
  "entities": [
    {"type": "ip", "value": "192.168.1.100"},
    {"type": "user", "value": "admin"}
  ],
  "raw_payload": {
    "failed_attempts": 50
  }
}
```

## Action Approval

```json
POST /api/v1/incidents/{id}/actions/{action_id}/approve
{
  "response_type": "APPROVE",
  "justification": "Confirmed malicious activity"
}
```

Response types: APPROVE, REJECT, MODIFY
