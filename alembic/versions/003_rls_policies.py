"""Row Level Security Policies

Revision ID: 003_rls_policies
Revises: 002_full_schema
Create Date: 2024-01-01 00:00:01.000000
"""
from alembic import op

revision = '003_rls_policies'
down_revision = '002_full_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable RLS on all multi-tenant tables
    op.execute("ALTER TABLE events ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE incidents ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE agent_findings ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE actions ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE patterns ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE entity_baselines ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE integrations ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE thresholds ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE feedback ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY")

    # Create policies for events
    op.execute("""
        CREATE POLICY tenant_isolation_events ON events
        FOR ALL
        USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
    """)

    # Create policies for incidents
    op.execute("""
        CREATE POLICY tenant_isolation_incidents ON incidents
        FOR ALL
        USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
    """)

    # Create policies for agent_findings (via incident)
    op.execute("""
        CREATE POLICY tenant_isolation_findings ON agent_findings
        FOR ALL
        USING (incident_id IN (
            SELECT id FROM incidents 
            WHERE tenant_id = current_setting('app.current_tenant_id', true)::uuid
        ))
    """)

    # Create policies for actions (via incident)
    op.execute("""
        CREATE POLICY tenant_isolation_actions ON actions
        FOR ALL
        USING (incident_id IN (
            SELECT id FROM incidents 
            WHERE tenant_id = current_setting('app.current_tenant_id', true)::uuid
        ))
    """)

    # Create policies for patterns
    op.execute("""
        CREATE POLICY tenant_isolation_patterns ON patterns
        FOR ALL
        USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
    """)

    # Create policies for baselines
    op.execute("""
        CREATE POLICY tenant_isolation_baselines ON entity_baselines
        FOR ALL
        USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
    """)

    # Create policies for integrations
    op.execute("""
        CREATE POLICY tenant_isolation_integrations ON integrations
        FOR ALL
        USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
    """)

    # Create policies for thresholds
    op.execute("""
        CREATE POLICY tenant_isolation_thresholds ON thresholds
        FOR ALL
        USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
    """)

    # Create policies for feedback
    op.execute("""
        CREATE POLICY tenant_isolation_feedback ON feedback
        FOR ALL
        USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
    """)

    # Audit log - read only for tenants, insert only for system
    op.execute("""
        CREATE POLICY audit_read ON audit_log
        FOR SELECT
        USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
    """)
    
    op.execute("""
        CREATE POLICY audit_insert ON audit_log
        FOR INSERT
        WITH CHECK (true)
    """)

    # Prevent updates and deletes on audit log
    op.execute("""
        CREATE POLICY audit_no_update ON audit_log
        FOR UPDATE
        USING (false)
    """)
    
    op.execute("""
        CREATE POLICY audit_no_delete ON audit_log
        FOR DELETE
        USING (false)
    """)


def downgrade() -> None:
    # Drop all policies
    tables = ['events', 'incidents', 'agent_findings', 'actions', 'patterns', 
              'entity_baselines', 'integrations', 'thresholds', 'feedback', 'audit_log']
    
    for table in tables:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_{table} ON {table}")
    
    op.execute("DROP POLICY IF EXISTS audit_read ON audit_log")
    op.execute("DROP POLICY IF EXISTS audit_insert ON audit_log")
    op.execute("DROP POLICY IF EXISTS audit_no_update ON audit_log")
    op.execute("DROP POLICY IF EXISTS audit_no_delete ON audit_log")
    
    # Disable RLS
    for table in tables:
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
