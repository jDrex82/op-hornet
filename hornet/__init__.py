"""
HORNET - Autonomous SOC Swarm
54-Agent Security Operations Center powered by Claude

Modules:
- agents: 54 specialized AI agents across 6 layers
- coordinator: FSM-based incident orchestration
- event_bus: Redis Streams event distribution
- embedding: Vector similarity search
- baseline: Behavioral anomaly detection
- executor: Action execution with rollback
- websocket: Real-time updates
- playbooks: Automated response playbooks
- integrations: Log sources, actions, notifications
- middleware: Auth, rate limiting, logging
- metrics: Prometheus observability
- tuner: Threshold optimization feedback loop
- research: AI alignment instrumentation
"""

__version__ = "2.0.0"
__author__ = "HORNET Team"

from hornet.config import get_settings

settings = get_settings()
