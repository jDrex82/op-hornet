-- ============================================================================
-- HORNET App User Setup (RLS enforced)
-- ============================================================================

BEGIN;

-- 1. Create app user
DO
\$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'hornet_app') THEN
        CREATE ROLE hornet_app WITH LOGIN PASSWORD 'hornet_app_secure_pwd_change_me';
    END IF;
END
\$\$;

-- 2. Grant connect
GRANT CONNECT ON DATABASE hornet TO hornet_app;

-- 3. Grant schema usage
GRANT USAGE ON SCHEMA public TO hornet_app;

-- 4. Grant table permissions
GRANT SELECT, INSERT, UPDATE ON 
    incidents, 
    events, 
    agent_findings, 
    incident_events,
    api_keys,
    tenants
TO hornet_app;

-- 5. Grant sequence usage
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO hornet_app;

COMMIT;
