"""
HORNET Database Models
SQLAlchemy models for PostgreSQL with pgvector support.
"""

from datetime import datetime
from typing import Optional, List, Any
from uuid import uuid4

from sqlalchemy import (
    Column, String, Text, Float, Boolean, Integer, DateTime,
    ForeignKey, Index, Enum as SQLEnum, JSON, LargeBinary,
    text, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY, INET, JSONB
from sqlalchemy.orm import relationship, DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncAttrs, create_async_engine, async_sessionmaker
from pgvector.sqlalchemy import Vector

import enum


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for all models."""
    pass


# Enums
class IncidentState(str, enum.Enum):
    IDLE = "IDLE"
    DETECTION = "DETECTION"
    ENRICHMENT = "ENRICHMENT"
    ANALYSIS = "ANALYSIS"
    PROPOSAL = "PROPOSAL"
    OVERSIGHT = "OVERSIGHT"
    EXECUTION = "EXECUTION"
    ESCALATED = "ESCALATED"
    CLOSED = "CLOSED"
    ERROR = "ERROR"


class Severity(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Verdict(str, enum.Enum):
    CONFIRMED = "CONFIRMED"
    DISMISSED = "DISMISSED"
    UNCERTAIN = "UNCERTAIN"


class ActionStatus(str, enum.Enum):
    PROPOSED = "PROPOSED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    VETOED = "VETOED"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ROLLED_BACK = "ROLLED_BACK"


class ActionRisk(str, enum.Enum):
    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class OversightDecision(str, enum.Enum):
    APPROVE = "APPROVE"
    PARTIAL = "PARTIAL"
    VETO = "VETO"


class HumanResponse(str, enum.Enum):
    APPROVE = "APPROVE"
    APPROVE_MODIFIED = "APPROVE_MODIFIED"
    REJECT = "REJECT"
    INVESTIGATE = "INVESTIGATE"
    OVERRIDE_VETO = "OVERRIDE_VETO"


# Core Tables
class Tenant(Base):
    """Multi-tenant organization."""
    __tablename__ = "tenants"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    settings: Mapped[dict] = mapped_column(JSONB, default=dict)
    subscription_tier: Mapped[str] = mapped_column(String(50), default="solo")
    api_key_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Relationships
    events = relationship("Event", back_populates="tenant", lazy="dynamic")
    incidents = relationship("Incident", back_populates="tenant", lazy="dynamic")
    integrations = relationship("TenantIntegration", back_populates="tenant")


class Event(Base):
    """Normalized security event."""
    __tablename__ = "events"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(100), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default="LOW")
    entities: Mapped[dict] = mapped_column(JSONB, default=list)
    raw_payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    embedding = mapped_column(Vector(1536), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    processed: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="events")
    incident_events = relationship("IncidentEvent", back_populates="event")
    
    __table_args__ = (
        Index("ix_events_tenant_timestamp", "tenant_id", "timestamp", postgresql_using="btree"),
        Index("ix_events_event_type", "event_type"),
        Index("ix_events_embedding", "embedding", postgresql_using="ivfflat", postgresql_ops={"embedding": "vector_cosine_ops"}),
    )


class Incident(Base):
    """Security incident being processed by the swarm."""
    __tablename__ = "incidents"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    state: Mapped[str] = mapped_column(String(20), default=IncidentState.IDLE.value)
    priority_score: Mapped[float] = mapped_column(Float, default=0.0)
    severity: Mapped[str] = mapped_column(String(20), default=Severity.LOW.value)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    impact_score: Mapped[float] = mapped_column(Float, default=0.0)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    verdict: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    outcome: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Token tracking
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    token_budget: Mapped[int] = mapped_column(Integer, default=50000)
    
    # Degradation tracking
    degradation_mode: Mapped[str] = mapped_column(String(20), default="FULL")
    
    # Relationships
    tenant = relationship("Tenant", back_populates="incidents")
    incident_events = relationship("IncidentEvent", back_populates="incident")
    findings = relationship("AgentFinding", back_populates="incident")
    actions = relationship("Action", back_populates="incident")
    messages = relationship("AgentMessage", back_populates="incident")
    
    __table_args__ = (
        Index("ix_incidents_tenant_state", "tenant_id", "state"),
        Index("ix_incidents_priority", "priority_score", postgresql_using="btree"),
    )


class IncidentEvent(Base):
    """Junction table for incident-event relationship."""
    __tablename__ = "incident_events"
    
    incident_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("incidents.id"), primary_key=True)
    event_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("events.id"), primary_key=True)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    
    incident = relationship("Incident", back_populates="incident_events")
    event = relationship("Event", back_populates="incident_events")


class AgentFinding(Base):
    """Finding produced by an agent."""
    __tablename__ = "agent_findings"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    incident_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("incidents.id"), nullable=False)
    agent: Mapped[str] = mapped_column(String(50), nullable=False)
    finding_type: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default=Severity.LOW.value)
    content: Mapped[dict] = mapped_column(JSONB, default=dict)
    reasoning: Mapped[str] = mapped_column(Text, nullable=True)
    mitre_techniques: Mapped[list] = mapped_column(ARRAY(String), default=list)
    entities: Mapped[dict] = mapped_column(JSONB, default=list)
    evidence: Mapped[dict] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Token tracking
    tokens_consumed: Mapped[int] = mapped_column(Integer, default=0)
    
    incident = relationship("Incident", back_populates="findings")
    
    __table_args__ = (
        Index("ix_findings_incident_agent", "incident_id", "agent"),
    )


class Action(Base):
    """Response action proposed, approved, or executed."""
    __tablename__ = "actions"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    incident_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("incidents.id"), nullable=False)
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)
    target: Mapped[str] = mapped_column(String(255), nullable=False)
    parameters: Mapped[dict] = mapped_column(JSONB, default=dict)
    risk_level: Mapped[str] = mapped_column(String(20), default=ActionRisk.LOW.value)
    
    status: Mapped[str] = mapped_column(String(20), default=ActionStatus.PROPOSED.value)
    proposed_by: Mapped[str] = mapped_column(String(50), nullable=False)
    proposed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    
    approved_by: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    executed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    result: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    
    rollback_plan: Mapped[dict] = mapped_column(JSONB, default=dict)
    rollback_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    
    justification: Mapped[str] = mapped_column(Text, nullable=True)
    veto_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    constraint_violated: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    incident = relationship("Incident", back_populates="actions")
    
    __table_args__ = (
        Index("ix_actions_incident_status", "incident_id", "status"),
    )


class AgentMessage(Base):
    """Inter-agent communication log."""
    __tablename__ = "agent_messages"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    incident_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("incidents.id"), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    target: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    message_type: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[dict] = mapped_column(JSONB, default=dict)
    
    incident = relationship("Incident", back_populates="messages")
    
    __table_args__ = (
        Index("ix_messages_incident_timestamp", "incident_id", "timestamp"),
    )


# Memory Tables
class Pattern(Base):
    """Learned attack pattern for similarity matching."""
    __tablename__ = "patterns"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    embedding = mapped_column(Vector(1536), nullable=True)
    mitre_techniques: Mapped[list] = mapped_column(ARRAY(String), default=list)
    detection_agents: Mapped[list] = mapped_column(ARRAY(String), default=list)
    source_incident_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    
    __table_args__ = (
        Index("ix_patterns_embedding", "embedding", postgresql_using="ivfflat", postgresql_ops={"embedding": "vector_cosine_ops"}),
    )


class EntityBaseline(Base):
    """Behavioral baseline for users, hosts, etc."""
    __tablename__ = "entity_baselines"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(255), nullable=False)
    baseline_data: Mapped[dict] = mapped_column(JSONB, default=dict)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    
    __table_args__ = (
        UniqueConstraint("tenant_id", "entity_type", "entity_id", name="uq_entity_baseline"),
        Index("ix_baselines_entity", "tenant_id", "entity_type", "entity_id"),
    )


# Configuration Tables
class TenantIntegration(Base):
    """Integration configuration per tenant."""
    __tablename__ = "tenant_integrations"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    integration_type: Mapped[str] = mapped_column(String(50), nullable=False)
    config: Mapped[dict] = mapped_column(JSONB, default=dict)
    credentials_encrypted: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_health_check: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    health_status: Mapped[str] = mapped_column(String(20), default="unknown")
    
    tenant = relationship("Tenant", back_populates="integrations")


class NotificationChannel(Base):
    """Notification channel configuration."""
    __tablename__ = "notification_channels"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    channel_type: Mapped[str] = mapped_column(String(50), nullable=False)
    config: Mapped[dict] = mapped_column(JSONB, default=dict)
    severity_filter: Mapped[list] = mapped_column(ARRAY(String), default=list)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


# Audit Tables
class AuditLog(Base):
    """Immutable audit log for compliance."""
    __tablename__ = "audit_log"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    actor: Mapped[str] = mapped_column(String(255), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    details: Mapped[dict] = mapped_column(JSONB, default=dict)
    ip_address = mapped_column(INET, nullable=True)
    
    __table_args__ = (
        Index("ix_audit_tenant_timestamp", "tenant_id", "timestamp"),
    )


# Research Tables
class AlignmentObservation(Base):
    """Alignment research data collection."""
    __tablename__ = "alignment_observations"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    incident_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    agent: Mapped[str] = mapped_column(String(50), nullable=False)
    observation_type: Mapped[str] = mapped_column(String(50), nullable=False)
    deception_score: Mapped[float] = mapped_column(Float, default=0.0)
    evidence: Mapped[dict] = mapped_column(JSONB, default=dict)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


# Database initialization
async def init_db(database_url: str):
    """Initialize database connection."""
    engine = create_async_engine(database_url, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    
    async with engine.begin() as conn:
        # Enable pgvector extension
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
    
    return engine, async_session
