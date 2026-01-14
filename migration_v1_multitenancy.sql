-- ============================================================================
-- HORNET Multi-Tenancy Migration v1
-- ============================================================================

BEGIN;

-- 1. UPGRADE api_keys TABLE
ALTER TABLE api_keys 
    ADD COLUMN IF NOT EXISTS tenant_id UUID REFERENCES tenants(id),
    ADD COLUMN IF NOT EXISTS scopes TEXT[] DEFAULT ARRAY['full']::TEXT[],
    ADD COLUMN IF NOT EXISTS last_used_at TIMESTAMP WITH TIME ZONE,
    ADD COLUMN IF NOT EXISTS expires_at TIMESTAMP WITH TIME ZONE;

UPDATE api_keys 
SET tenant_id = '00000000-0000-0000-0000-000000000001'
WHERE tenant_id IS NULL;

ALTER TABLE api_keys ALTER COLUMN tenant_id SET NOT NULL;
CREATE INDEX IF NOT EXISTS ix_api_keys_tenant ON api_keys(tenant_id);

-- 2. UPGRADE agent_findings TABLE
ALTER TABLE agent_findings 
    ADD COLUMN IF NOT EXISTS tenant_id UUID REFERENCES tenants(id);

UPDATE agent_findings af
SET tenant_id = i.tenant_id
FROM incidents i
WHERE af.incident_id = i.id
  AND af.tenant_id IS NULL;

ALTER TABLE agent_findings ALTER COLUMN tenant_id SET NOT NULL;
CREATE INDEX IF NOT EXISTS ix_agent_findings_tenant ON agent_findings(tenant_id);

-- 3. ENABLE RLS
ALTER TABLE incidents ENABLE ROW LEVEL SECURITY;
ALTER TABLE events ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_findings ENABLE ROW LEVEL SECURITY;

-- 4. CREATE RLS POLICIES
DROP POLICY IF EXISTS tenant_isolation ON incidents;
DROP POLICY IF EXISTS tenant_isolation ON events;
DROP POLICY IF EXISTS tenant_isolation ON agent_findings;

CREATE POLICY tenant_isolation ON incidents
    FOR ALL
    USING (tenant_id::text = current_setting('app.current_tenant_id', true))
    WITH CHECK (tenant_id::text = current_setting('app.current_tenant_id', true));

CREATE POLICY tenant_isolation ON events
    FOR ALL
    USING (tenant_id::text = current_setting('app.current_tenant_id', true))
    WITH CHECK (tenant_id::text = current_setting('app.current_tenant_id', true));

CREATE POLICY tenant_isolation ON agent_findings
    FOR ALL
    USING (tenant_id::text = current_setting('app.current_tenant_id', true))
    WITH CHECK (tenant_id::text = current_setting('app.current_tenant_id', true));

COMMIT;
