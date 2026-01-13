"""
HORNET Configuration
Central configuration management for the autonomous SOC swarm.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    APP_NAME: str = "HORNET"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    OTEL_ENABLED: bool = False
    
    # API Keys
    ANTHROPIC_API_KEY: str = Field(..., description="Claude API key")
    OPENAI_API_KEY: str = Field(..., description="OpenAI API key for embeddings")
    
    # Database
    DATABASE_URL: str = Field(
        "postgresql+asyncpg://hornet:hornet@localhost:5432/hornet",
        description="PostgreSQL connection string"
    )
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    
    # Redis
    REDIS_URL: str = Field(
        "redis://localhost:6379/0",
        description="Redis connection string"
    )
    
    # LLM Configuration
    DEFAULT_MODEL: str = "claude-3-haiku-20240307"
    ANALYSIS_MODEL: str = "claude-sonnet-4-20250514"
    ADVANCED_MODEL: str = "claude-opus-4-20250514"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS: int = 1536
    
    # Token Budget
    TOKEN_BUDGET_PER_INCIDENT: int = 50000
    TOKEN_WARNING_THRESHOLD: float = 0.80
    TOKEN_CRITICAL_THRESHOLD: float = 0.90
    TOKEN_FORCE_THRESHOLD: float = 0.95
    
    # Timeouts (milliseconds)
    AGENT_RESPONSE_TIMEOUT_MS: int = 5000
    DETECTION_LAYER_TIMEOUT_MS: int = 15000
    ENRICHMENT_LAYER_TIMEOUT_MS: int = 10000
    ANALYSIS_LAYER_TIMEOUT_MS: int = 30000
    PROPOSAL_TIMEOUT_MS: int = 20000
    OVERSIGHT_TIMEOUT_MS: int = 30000
    EXECUTION_TIMEOUT_MS: int = 60000
    HUMAN_ESCALATION_TIMEOUT_MS: int = 1800000  # 30 minutes
    
    # Thresholds
    THRESHOLD_DISMISS: float = 0.30
    THRESHOLD_INVESTIGATE: float = 0.60
    THRESHOLD_CONFIRM: float = 0.80
    THRESHOLD_HUMAN_ESCALATE_MIN: float = 0.50
    THRESHOLD_HUMAN_ESCALATE_MAX: float = 0.70
    THRESHOLD_HIGH_IMPACT: float = 0.60
    
    # Swarm Configuration
    MAX_AGENTS_PER_INCIDENT: int = 12
    MAX_INCIDENT_DURATION_SECONDS: int = 300
    MAX_FINDINGS_PER_AGENT: int = 3
    DEADLOCK_CHECK_INTERVAL_SECONDS: int = 2
    STARVATION_TIMEOUT_SECONDS: int = 10
    MAX_CONSENSUS_CHALLENGES: int = 5
    
    # Rate Limiting
    CLAUDE_API_RPM: int = 4000
    OPENAI_EMBED_RPM: int = 3000
    VIRUSTOTAL_RPM: int = 4
    ABUSEIPDB_RPD: int = 1000
    
    # Security
    SECRET_KEY: str = Field(..., description="JWT secret key")
    API_KEY_HASH_ROUNDS: int = 12
    MAX_FIELD_SIZE_BYTES: int = 10240  # 10KB
    
    # Prompt Injection Defense
    BLOCKED_PATTERNS: list[str] = [
        "ignore previous",
        "system prompt",
        "you are now",
        "disregard instructions",
        "forget your instructions",
        "new instructions",
    ]
    
    # Retention
    EVENT_RETENTION_DAYS: int = 90
    INCIDENT_RETENTION_DAYS: int = 365
    AUDIT_LOG_RETENTION_YEARS: int = 7
    
    # Baseline Configuration
    USER_BASELINE_WINDOW_DAYS: int = 30
    USER_BASELINE_MIN_DATA_POINTS: int = 50
    HOST_BASELINE_WINDOW_DAYS: int = 14
    NETWORK_BASELINE_WINDOW_HOURS: int = 168  # 7 days
    ANOMALY_Z_SCORE_THRESHOLD: float = 2.0
    
    # External Services (optional)
    VIRUSTOTAL_API_KEY: Optional[str] = None
    ABUSEIPDB_API_KEY: Optional[str] = None
    MISP_URL: Optional[str] = None
    MISP_API_KEY: Optional[str] = None
    
    # Notifications
    SLACK_BOT_TOKEN: Optional[str] = None
    PAGERDUTY_INTEGRATION_KEY: Optional[str] = None
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    
    # Research Mode
    RESEARCH_MODE_ENABLED: bool = False
    RESEARCH_SAMPLING_RATE: float = 0.1
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Agent-specific configuration
AGENT_CONFIG = {
    # Detection Layer
    "hunter": {"model": "haiku", "weight": 1.0, "max_findings": 3},
    "sentinel": {"model": "haiku", "weight": 1.0, "max_findings": 3},
    "behavioral": {"model": "haiku", "weight": 1.1, "max_findings": 3},
    "netwatch": {"model": "haiku", "weight": 1.0, "max_findings": 3},
    "endpoint": {"model": "haiku", "weight": 1.0, "max_findings": 3},
    "gatekeeper": {"model": "haiku", "weight": 1.0, "max_findings": 3},
    "dataguard": {"model": "haiku", "weight": 1.0, "max_findings": 3},
    "phisherman": {"model": "haiku", "weight": 1.0, "max_findings": 3},
    "cloudwatch": {"model": "haiku", "weight": 1.0, "max_findings": 3},
    "container": {"model": "haiku", "weight": 1.0, "max_findings": 3},
    "dns": {"model": "haiku", "weight": 1.0, "max_findings": 3},
    
    # Intelligence Layer
    "intel": {"model": "haiku", "weight": 1.2, "max_findings": 5},
    "correlator": {"model": "haiku", "weight": 1.3, "max_findings": 5},
    
    # Analysis Layer
    "analyst": {"model": "sonnet", "weight": 1.5, "max_findings": 1},
    "triage": {"model": "haiku", "weight": 1.0, "max_findings": 1},
    "forensics": {"model": "sonnet", "weight": 1.4, "max_findings": 10},
    
    # Action Layer
    "responder": {"model": "sonnet", "weight": 1.0, "max_findings": 5},
    "deceiver": {"model": "haiku", "weight": 1.0, "max_findings": 3},
    "recovery": {"model": "haiku", "weight": 1.0, "max_findings": 5},
    "playbook": {"model": "haiku", "weight": 1.0, "max_findings": 1},
    
    # Governance Layer
    "oversight": {"model": "sonnet", "weight": 1.0, "max_findings": 1},
    "compliance": {"model": "haiku", "weight": 1.0, "max_findings": 5},
    "legal": {"model": "sonnet", "weight": 1.0, "max_findings": 3},
    
    # Meta Layer
    "router": {"model": "haiku", "weight": 1.0, "max_findings": 1},
    "memory": {"model": "haiku", "weight": 1.0, "max_findings": 10},
    "health": {"model": "haiku", "weight": 1.0, "max_findings": 5},
    
    # Specialized
    "sandbox": {"model": "sonnet", "weight": 1.4, "max_findings": 3},
    "redsim": {"model": "sonnet", "weight": 1.2, "max_findings": 5},
    "vision": {"model": "sonnet", "weight": 1.0, "max_findings": 3},
}

# Event classification matrix
EVENT_CLASSIFICATION = {
    # Authentication Events
    "auth.login_failure": ["gatekeeper", "behavioral", "intel", "correlator"],
    "auth.login_success_anomaly": ["gatekeeper", "behavioral", "intel"],
    "auth.privilege_escalation": ["gatekeeper", "behavioral", "cloudwatch", "compliance"],
    "auth.password_change": ["gatekeeper", "behavioral"],
    "auth.mfa_disabled": ["gatekeeper", "compliance", "oversight"],
    "auth.service_account_abuse": ["gatekeeper", "cloudwatch", "change"],
    "auth.impossible_travel": ["gatekeeper", "behavioral", "intel", "correlator"],
    "auth.brute_force": ["gatekeeper", "intel", "correlator", "responder"],
    
    # Network Events
    "network.c2_beacon": ["netwatch", "dns", "hunter", "intel", "redsim"],
    "network.lateral_movement": ["netwatch", "hunter", "endpoint", "correlator"],
    "network.dns_tunnel": ["dns", "netwatch", "intel", "dataguard"],
    "network.port_scan": ["netwatch", "hunter", "surface"],
    "network.ddos": ["uptime", "netwatch", "responder"],
    "network.firewall_bypass": ["netwatch", "hunter", "change"],
    "network.data_exfil": ["netwatch", "dataguard", "behavioral", "oversight"],
    
    # Endpoint Events
    "endpoint.malware_detected": ["endpoint", "sandbox", "hunter", "intel"],
    "endpoint.ransomware_behavior": ["endpoint", "backup", "responder", "oversight"],
    "endpoint.process_injection": ["endpoint", "hunter", "redsim"],
    "endpoint.persistence_mechanism": ["endpoint", "hunter", "forensics"],
    "endpoint.suspicious_script": ["endpoint", "sandbox", "hunter"],
    "endpoint.memory_injection": ["endpoint", "hunter", "redsim", "forensics"],
    "endpoint.driver_load": ["endpoint", "change", "hunter"],
    
    # Email Events
    "email.phishing_detected": ["phisherman", "intel", "vision"],
    "email.bec_attempt": ["phisherman", "behavioral", "social"],
    "email.malicious_attachment": ["phisherman", "sandbox", "endpoint"],
    "email.credential_harvest": ["phisherman", "intel", "gatekeeper"],
    "email.spam_campaign": ["phisherman", "intel", "correlator"],
    
    # Cloud Events
    "cloud.config_change": ["cloudwatch", "change", "compliance"],
    "cloud.public_exposure": ["cloudwatch", "surface", "compliance", "oversight"],
    "cloud.iam_modification": ["cloudwatch", "gatekeeper", "change"],
    "cloud.container_escape": ["container", "cloudwatch", "hunter"],
    "cloud.api_abuse": ["api", "cloudwatch", "behavioral"],
    "cloud.storage_access": ["cloudwatch", "dataguard", "behavioral"],
    
    # Data Events
    "data.exfiltration_attempt": ["dataguard", "netwatch", "behavioral", "oversight"],
    "data.sensitive_access": ["dataguard", "gatekeeper", "behavioral"],
    "data.mass_download": ["dataguard", "behavioral", "correlator"],
    "data.encryption_anomaly": ["dataguard", "endpoint", "backup"],
    "data.classification_violation": ["dataguard", "compliance", "oversight"],
}

# Model mapping
MODEL_MAP = {
    "haiku": "claude-3-haiku-20240307",
    "sonnet": "claude-sonnet-4-20250514",
    "opus": "claude-opus-4-20250514",
}


