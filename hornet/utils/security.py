"""
HORNET Security Utilities
Encryption, audit logging, and security helpers.
"""
import hashlib
import hmac
import secrets
import base64
from datetime import datetime
from typing import Dict, Any, Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import structlog

logger = structlog.get_logger()


class SecretManager:
    """
    Manages encryption of sensitive data.
    Uses Fernet (AES-128-CBC) with per-tenant keys.
    """
    
    def __init__(self, master_key: str):
        self.master_key = master_key.encode()
        self._tenant_keys: Dict[str, bytes] = {}
    
    def _derive_tenant_key(self, tenant_id: str) -> bytes:
        """Derive a tenant-specific key from master key."""
        if tenant_id in self._tenant_keys:
            return self._tenant_keys[tenant_id]
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=tenant_id.encode(),
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.master_key))
        self._tenant_keys[tenant_id] = key
        return key
    
    def encrypt(self, data: str, tenant_id: str) -> bytes:
        """Encrypt data with tenant-specific key."""
        key = self._derive_tenant_key(tenant_id)
        f = Fernet(key)
        return f.encrypt(data.encode())
    
    def decrypt(self, encrypted_data: bytes, tenant_id: str) -> str:
        """Decrypt data with tenant-specific key."""
        key = self._derive_tenant_key(tenant_id)
        f = Fernet(key)
        return f.decrypt(encrypted_data).decode()
    
    def rotate_master_key(self, new_master_key: str):
        """Rotate the master key (would need to re-encrypt all data)."""
        self.master_key = new_master_key.encode()
        self._tenant_keys.clear()
        logger.warning("master_key_rotated")


class AuditLogger:
    """
    Immutable audit logging for compliance.
    Logs security-relevant actions with tamper detection.
    """
    
    def __init__(self, db_session=None):
        self.db = db_session
        self._signing_key = secrets.token_bytes(32)
    
    def _compute_signature(self, data: str) -> str:
        """Compute HMAC signature for tamper detection."""
        return hmac.new(self._signing_key, data.encode(), hashlib.sha256).hexdigest()
    
    async def log(
        self,
        tenant_id: str,
        actor: str,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        details: Dict[str, Any] = None,
        ip_address: str = None,
    ):
        """Log an audit event."""
        timestamp = datetime.utcnow().isoformat()
        
        log_data = {
            "tenant_id": tenant_id,
            "timestamp": timestamp,
            "actor": actor,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "details": details or {},
            "ip_address": ip_address,
        }
        
        # Compute signature
        signature = self._compute_signature(str(log_data))
        log_data["signature"] = signature
        
        # Log to structured logger
        logger.info(
            "audit_event",
            **{k: v for k, v in log_data.items() if k != "signature"}
        )
        
        # Would persist to database in production
        return log_data
    
    async def log_auth_event(self, tenant_id: str, user: str, action: str, success: bool, ip: str):
        """Log authentication event."""
        await self.log(
            tenant_id=tenant_id,
            actor=user,
            action=f"auth.{action}",
            resource_type="user",
            resource_id=user,
            details={"success": success},
            ip_address=ip,
        )
    
    async def log_config_change(self, tenant_id: str, actor: str, config_type: str, changes: Dict):
        """Log configuration change."""
        await self.log(
            tenant_id=tenant_id,
            actor=actor,
            action="config.update",
            resource_type="config",
            resource_id=config_type,
            details={"changes": changes},
        )
    
    async def log_action_execution(
        self,
        tenant_id: str,
        actor: str,
        action_type: str,
        target: str,
        result: str,
    ):
        """Log action execution."""
        await self.log(
            tenant_id=tenant_id,
            actor=actor,
            action=f"action.{action_type}",
            resource_type="action",
            resource_id=target,
            details={"result": result},
        )
    
    async def log_human_override(
        self,
        tenant_id: str,
        actor: str,
        incident_id: str,
        override_type: str,
        justification: str,
    ):
        """Log human override of automated decision."""
        await self.log(
            tenant_id=tenant_id,
            actor=actor,
            action=f"override.{override_type}",
            resource_type="incident",
            resource_id=incident_id,
            details={"justification": justification},
        )


# Row-Level Security (RLS) SQL policies
RLS_POLICIES = """
-- Enable RLS on all tables
ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;
ALTER TABLE events ENABLE ROW LEVEL SECURITY;
ALTER TABLE incidents ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_findings ENABLE ROW LEVEL SECURITY;
ALTER TABLE actions ENABLE ROW LEVEL SECURITY;
ALTER TABLE patterns ENABLE ROW LEVEL SECURITY;
ALTER TABLE entity_baselines ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;

-- Create policies for tenant isolation
CREATE POLICY tenant_isolation_events ON events
    FOR ALL
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

CREATE POLICY tenant_isolation_incidents ON incidents
    FOR ALL
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

CREATE POLICY tenant_isolation_findings ON agent_findings
    FOR ALL
    USING (incident_id IN (SELECT id FROM incidents WHERE tenant_id = current_setting('app.current_tenant_id')::uuid));

CREATE POLICY tenant_isolation_actions ON actions
    FOR ALL
    USING (incident_id IN (SELECT id FROM incidents WHERE tenant_id = current_setting('app.current_tenant_id')::uuid));

CREATE POLICY tenant_isolation_patterns ON patterns
    FOR ALL
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

CREATE POLICY tenant_isolation_baselines ON entity_baselines
    FOR ALL
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

CREATE POLICY tenant_isolation_audit ON audit_log
    FOR SELECT
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

-- Audit log is insert-only (immutable)
CREATE POLICY audit_log_insert ON audit_log
    FOR INSERT
    WITH CHECK (true);

-- Prevent updates and deletes on audit log
CREATE POLICY audit_log_no_update ON audit_log
    FOR UPDATE
    USING (false);

CREATE POLICY audit_log_no_delete ON audit_log
    FOR DELETE
    USING (false);
"""


def generate_api_key() -> str:
    """Generate a secure API key."""
    return f"hnt_{secrets.token_urlsafe(32)}"


def hash_api_key(api_key: str) -> str:
    """Hash API key for secure storage."""
    return hashlib.sha256(api_key.encode()).hexdigest()


def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify webhook HMAC signature."""
    expected = f"sha256={hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()}"
    return hmac.compare_digest(expected, signature)


def sanitize_log_data(data: Dict[str, Any], sensitive_keys: set = None) -> Dict[str, Any]:
    """Sanitize sensitive data before logging."""
    sensitive_keys = sensitive_keys or {"password", "secret", "token", "key", "credential", "api_key"}
    
    result = {}
    for k, v in data.items():
        if any(s in k.lower() for s in sensitive_keys):
            result[k] = "[REDACTED]"
        elif isinstance(v, dict):
            result[k] = sanitize_log_data(v, sensitive_keys)
        else:
            result[k] = v
    return result
