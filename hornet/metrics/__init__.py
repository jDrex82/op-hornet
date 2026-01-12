"""
HORNET Metrics and Observability
Prometheus metrics and OpenTelemetry tracing.
"""
from datetime import datetime
from typing import Dict, Any, Optional
from functools import wraps
import time
import structlog

from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest, CONTENT_TYPE_LATEST

logger = structlog.get_logger()


# Counters
INCIDENTS_TOTAL = Counter(
    'hornet_incidents_total',
    'Total incidents processed',
    ['tenant_id', 'severity', 'outcome']
)

EVENTS_TOTAL = Counter(
    'hornet_events_total',
    'Total events ingested',
    ['tenant_id', 'event_type', 'source']
)

AGENT_CALLS_TOTAL = Counter(
    'hornet_agent_calls_total',
    'Total agent invocations',
    ['agent', 'status']
)

ACTIONS_TOTAL = Counter(
    'hornet_actions_total',
    'Total actions executed',
    ['action_type', 'status', 'risk_level']
)

ESCALATIONS_TOTAL = Counter(
    'hornet_escalations_total',
    'Total escalations to humans',
    ['tenant_id', 'escalation_type']
)

VETO_TOTAL = Counter(
    'hornet_veto_total',
    'Total veto decisions',
    ['veto_type', 'constraint']
)


# Histograms
INCIDENT_DURATION = Histogram(
    'hornet_incident_duration_seconds',
    'Incident processing duration',
    ['tenant_id', 'severity'],
    buckets=[1, 5, 10, 30, 60, 120, 300, 600]
)

AGENT_LATENCY = Histogram(
    'hornet_agent_latency_seconds',
    'Agent response latency',
    ['agent'],
    buckets=[0.1, 0.5, 1, 2, 5, 10]
)

ACTION_DURATION = Histogram(
    'hornet_action_duration_seconds',
    'Action execution duration',
    ['action_type'],
    buckets=[0.1, 0.5, 1, 5, 10, 30]
)

LLM_LATENCY = Histogram(
    'hornet_llm_latency_seconds',
    'LLM API call latency',
    ['model'],
    buckets=[0.1, 0.5, 1, 2, 5, 10]
)


# Gauges
ACTIVE_INCIDENTS = Gauge(
    'hornet_active_incidents',
    'Currently active incidents',
    ['tenant_id', 'state']
)

QUEUE_DEPTH = Gauge(
    'hornet_queue_depth',
    'Event queue depth',
    ['queue_name']
)

TOKEN_BUDGET_REMAINING = Gauge(
    'hornet_token_budget_remaining',
    'Remaining token budget',
    ['incident_id']
)

AGENT_HEALTH = Gauge(
    'hornet_agent_health',
    'Agent health status (1=healthy, 0=unhealthy)',
    ['agent']
)

INTEGRATION_HEALTH = Gauge(
    'hornet_integration_health',
    'Integration health status',
    ['integration_type', 'integration_name']
)

WEBSOCKET_CONNECTIONS = Gauge(
    'hornet_websocket_connections',
    'Active WebSocket connections',
    ['tenant_id']
)


# Info
HORNET_INFO = Info('hornet', 'HORNET application information')


# Token tracking
TOKENS_USED = Counter(
    'hornet_tokens_used_total',
    'Total tokens consumed',
    ['model', 'agent']
)


# Confidence distribution
CONFIDENCE_DISTRIBUTION = Histogram(
    'hornet_confidence_distribution',
    'Distribution of confidence scores',
    ['agent', 'finding_type'],
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)


class MetricsCollector:
    """Centralized metrics collection."""
    
    def __init__(self):
        HORNET_INFO.info({
            'version': '2.0.0',
            'environment': 'production',
        })
    
    def record_incident_created(self, tenant_id: str, severity: str):
        ACTIVE_INCIDENTS.labels(tenant_id=tenant_id, state='DETECTION').inc()
    
    def record_incident_state_change(self, tenant_id: str, old_state: str, new_state: str):
        ACTIVE_INCIDENTS.labels(tenant_id=tenant_id, state=old_state).dec()
        ACTIVE_INCIDENTS.labels(tenant_id=tenant_id, state=new_state).inc()
    
    def record_incident_closed(self, tenant_id: str, severity: str, outcome: str, duration_seconds: float):
        INCIDENTS_TOTAL.labels(tenant_id=tenant_id, severity=severity, outcome=outcome).inc()
        INCIDENT_DURATION.labels(tenant_id=tenant_id, severity=severity).observe(duration_seconds)
    
    def record_event_ingested(self, tenant_id: str, event_type: str, source: str):
        EVENTS_TOTAL.labels(tenant_id=tenant_id, event_type=event_type, source=source).inc()
    
    def record_agent_call(self, agent: str, status: str, latency_seconds: float, tokens: int = 0, model: str = ""):
        AGENT_CALLS_TOTAL.labels(agent=agent, status=status).inc()
        AGENT_LATENCY.labels(agent=agent).observe(latency_seconds)
        if tokens > 0 and model:
            TOKENS_USED.labels(model=model, agent=agent).inc(tokens)
    
    def record_action_executed(self, action_type: str, status: str, risk_level: str, duration_seconds: float):
        ACTIONS_TOTAL.labels(action_type=action_type, status=status, risk_level=risk_level).inc()
        ACTION_DURATION.labels(action_type=action_type).observe(duration_seconds)
    
    def record_escalation(self, tenant_id: str, escalation_type: str):
        ESCALATIONS_TOTAL.labels(tenant_id=tenant_id, escalation_type=escalation_type).inc()
    
    def record_veto(self, veto_type: str, constraint: str):
        VETO_TOTAL.labels(veto_type=veto_type, constraint=constraint).inc()
    
    def record_confidence(self, agent: str, finding_type: str, confidence: float):
        CONFIDENCE_DISTRIBUTION.labels(agent=agent, finding_type=finding_type).observe(confidence)
    
    def record_llm_call(self, model: str, latency_seconds: float):
        LLM_LATENCY.labels(model=model).observe(latency_seconds)
    
    def set_queue_depth(self, queue_name: str, depth: int):
        QUEUE_DEPTH.labels(queue_name=queue_name).set(depth)
    
    def set_agent_health(self, agent: str, healthy: bool):
        AGENT_HEALTH.labels(agent=agent).set(1 if healthy else 0)
    
    def set_integration_health(self, integration_type: str, name: str, healthy: bool):
        INTEGRATION_HEALTH.labels(integration_type=integration_type, integration_name=name).set(1 if healthy else 0)
    
    def set_websocket_connections(self, tenant_id: str, count: int):
        WEBSOCKET_CONNECTIONS.labels(tenant_id=tenant_id).set(count)


# Decorator for timing functions
def timed(metric_name: str = None):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start
                logger.debug(f"{func.__name__}_duration", duration_seconds=duration)
        return wrapper
    return decorator


# Global metrics collector
metrics = MetricsCollector()


# Metrics endpoint handler
async def metrics_endpoint():
    """Return Prometheus metrics."""
    return generate_latest(), CONTENT_TYPE_LATEST


# Alerting rules (Prometheus alertmanager format)
ALERTING_RULES = """
groups:
  - name: hornet_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(hornet_agent_calls_total{status="error"}[5m]) / rate(hornet_agent_calls_total[5m]) > 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: High agent error rate detected
          
      - alert: IntegrationDown
        expr: hornet_integration_health == 0
        for: 3m
        labels:
          severity: high
        annotations:
          summary: Integration {{ $labels.integration_name }} is unhealthy
          
      - alert: QueueBackup
        expr: hornet_queue_depth > 100
        for: 5m
        labels:
          severity: high
        annotations:
          summary: Event queue depth exceeds threshold
          
      - alert: TokenBudgetBurn
        expr: (50000 - hornet_token_budget_remaining) / 50000 > 0.8
        for: 1m
        labels:
          severity: medium
        annotations:
          summary: Token budget usage exceeds 80%
          
      - alert: EscalationSLABreach
        expr: time() - hornet_escalation_timestamp > 300
        for: 0m
        labels:
          severity: critical
        annotations:
          summary: Critical escalation unacknowledged for 5+ minutes
"""
