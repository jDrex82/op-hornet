"""Full schema with all tables and RLS

Revision ID: 002_full_schema
Revises: 001_initial
Create Date: 2024-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '002_full_schema'
down_revision = '001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Events table
    op.create_table(
        'events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('source', sa.String(255), nullable=False),
        sa.Column('source_type', sa.String(50), nullable=False),
        sa.Column('severity', sa.String(20), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ingested_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('entities', postgresql.JSONB, default={}),
        sa.Column('raw_payload', postgresql.JSONB, default={}),
        sa.Column('embedding', postgresql.ARRAY(sa.Float), nullable=True),
        sa.Column('incident_id', postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index('ix_events_tenant_timestamp', 'events', ['tenant_id', 'timestamp'])
    op.create_index('ix_events_event_type', 'events', ['event_type'])
    op.create_index('ix_events_incident', 'events', ['incident_id'])

    # Incidents table
    op.create_table(
        'incidents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('state', sa.String(20), nullable=False, default='IDLE'),
        sa.Column('severity', sa.String(20), nullable=True),
        sa.Column('confidence', sa.Float, default=0.0),
        sa.Column('summary', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('outcome', sa.String(50), nullable=True),
        sa.Column('tokens_used', sa.Integer, default=0),
        sa.Column('token_budget', sa.Integer, default=50000),
        sa.Column('escalation_reason', sa.Text, nullable=True),
        sa.Column('assigned_to', sa.String(255), nullable=True),
        sa.Column('playbook_id', sa.String(50), nullable=True),
        sa.Column('mitre_techniques', postgresql.ARRAY(sa.String), default=[]),
        sa.Column('verdict', postgresql.JSONB, nullable=True),
        sa.Column('proposal', postgresql.JSONB, nullable=True),
    )
    op.create_index('ix_incidents_tenant_state', 'incidents', ['tenant_id', 'state'])
    op.create_index('ix_incidents_created', 'incidents', ['created_at'])

    # Agent findings table
    op.create_table(
        'agent_findings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('incident_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('incidents.id'), nullable=False),
        sa.Column('agent_name', sa.String(50), nullable=False),
        sa.Column('output_type', sa.String(50), nullable=False),
        sa.Column('confidence', sa.Float, nullable=False),
        sa.Column('content', postgresql.JSONB, nullable=False),
        sa.Column('reasoning', sa.Text, nullable=True),
        sa.Column('tokens_used', sa.Integer, default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('mitre_techniques', postgresql.ARRAY(sa.String), default=[]),
    )
    op.create_index('ix_findings_incident', 'agent_findings', ['incident_id'])
    op.create_index('ix_findings_agent', 'agent_findings', ['agent_name'])

    # Actions table
    op.create_table(
        'actions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('incident_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('incidents.id'), nullable=False),
        sa.Column('action_type', sa.String(50), nullable=False),
        sa.Column('target', sa.String(255), nullable=False),
        sa.Column('parameters', postgresql.JSONB, default={}),
        sa.Column('risk_level', sa.String(20), nullable=False),
        sa.Column('justification', sa.Text, nullable=True),
        sa.Column('status', sa.String(20), nullable=False, default='PENDING'),
        sa.Column('proposed_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('approved_by', sa.String(255), nullable=True),
        sa.Column('executed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('result', postgresql.JSONB, nullable=True),
        sa.Column('rollback_id', sa.String(255), nullable=True),
        sa.Column('auto_approved', sa.Boolean, default=False),
    )
    op.create_index('ix_actions_incident', 'actions', ['incident_id'])
    op.create_index('ix_actions_status', 'actions', ['status'])

    # Patterns table (for similarity search)
    op.create_table(
        'patterns',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('pattern_type', sa.String(50), nullable=False),
        sa.Column('embedding', postgresql.ARRAY(sa.Float), nullable=True),
        sa.Column('mitre_techniques', postgresql.ARRAY(sa.String), default=[]),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('last_seen', sa.DateTime(timezone=True), nullable=True),
        sa.Column('occurrence_count', sa.Integer, default=0),
        sa.Column('is_malicious', sa.Boolean, default=True),
    )
    op.create_index('ix_patterns_tenant', 'patterns', ['tenant_id'])

    # Entity baselines table
    op.create_table(
        'entity_baselines',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('entity_type', sa.String(50), nullable=False),  # user, host, network
        sa.Column('entity_id', sa.String(255), nullable=False),
        sa.Column('metric_name', sa.String(100), nullable=False),
        sa.Column('mean', sa.Float, nullable=False),
        sa.Column('std', sa.Float, nullable=False),
        sa.Column('min_value', sa.Float, nullable=True),
        sa.Column('max_value', sa.Float, nullable=True),
        sa.Column('percentiles', postgresql.JSONB, default={}),
        sa.Column('sample_count', sa.Integer, default=0),
        sa.Column('calculated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('valid_until', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_baselines_entity', 'entity_baselines', ['tenant_id', 'entity_type', 'entity_id'])
    op.create_unique_constraint('uq_baseline_entity_metric', 'entity_baselines', ['tenant_id', 'entity_type', 'entity_id', 'metric_name'])

    # Audit log table (immutable)
    op.create_table(
        'audit_log',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('actor', sa.String(255), nullable=False),
        sa.Column('actor_type', sa.String(50), nullable=False),  # user, agent, system
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('resource_type', sa.String(50), nullable=False),
        sa.Column('resource_id', sa.String(255), nullable=True),
        sa.Column('details', postgresql.JSONB, default={}),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.Text, nullable=True),
        sa.Column('signature', sa.String(64), nullable=True),  # HMAC for tamper detection
    )
    op.create_index('ix_audit_tenant_time', 'audit_log', ['tenant_id', 'timestamp'])
    op.create_index('ix_audit_actor', 'audit_log', ['actor'])
    op.create_index('ix_audit_resource', 'audit_log', ['resource_type', 'resource_id'])

    # Integrations table
    op.create_table(
        'integrations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('integration_type', sa.String(50), nullable=False),  # log_source, action, notification
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('connector_type', sa.String(50), nullable=False),
        sa.Column('config', postgresql.JSONB, default={}),  # Encrypted in practice
        sa.Column('is_enabled', sa.Boolean, default=True),
        sa.Column('last_health_check', sa.DateTime(timezone=True), nullable=True),
        sa.Column('health_status', sa.String(20), default='UNKNOWN'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_integrations_tenant', 'integrations', ['tenant_id'])

    # Thresholds table
    op.create_table(
        'thresholds',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('threshold_type', sa.String(50), nullable=False),
        sa.Column('agent_name', sa.String(50), nullable=True),  # NULL = global
        sa.Column('value', sa.Float, nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_by', sa.String(255), nullable=True),
    )
    op.create_unique_constraint('uq_threshold', 'thresholds', ['tenant_id', 'threshold_type', 'agent_name'])

    # Feedback table (for tuner)
    op.create_table(
        'feedback',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('incident_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('incidents.id'), nullable=False),
        sa.Column('action_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('feedback_type', sa.String(20), nullable=False),  # APPROVE, REJECT, MODIFY
        sa.Column('agent_name', sa.String(50), nullable=True),
        sa.Column('original_confidence', sa.Float, nullable=True),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('justification', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_feedback_tenant', 'feedback', ['tenant_id'])
    op.create_index('ix_feedback_incident', 'feedback', ['incident_id'])

    # Add foreign key for events.incident_id
    op.create_foreign_key('fk_events_incident', 'events', 'incidents', ['incident_id'], ['id'])


def downgrade() -> None:
    op.drop_table('feedback')
    op.drop_table('thresholds')
    op.drop_table('integrations')
    op.drop_table('audit_log')
    op.drop_table('entity_baselines')
    op.drop_table('patterns')
    op.drop_table('actions')
    op.drop_table('agent_findings')
    op.drop_table('incidents')
    op.drop_table('events')
