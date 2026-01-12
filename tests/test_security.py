"""Test security utilities."""
import pytest
from hornet.utils.security import (
    SecretManager, AuditLogger, generate_api_key, 
    hash_api_key, verify_webhook_signature, sanitize_log_data
)


class TestSecretManager:
    @pytest.fixture
    def manager(self):
        return SecretManager("master_key_12345")
    
    def test_encrypt_decrypt(self, manager):
        original = "sensitive data"
        encrypted = manager.encrypt(original, "tenant-1")
        decrypted = manager.decrypt(encrypted, "tenant-1")
        assert decrypted == original
    
    def test_tenant_isolation(self, manager):
        data = "secret"
        encrypted = manager.encrypt(data, "tenant-1")
        with pytest.raises(Exception):
            manager.decrypt(encrypted, "tenant-2")


class TestAuditLogger:
    @pytest.fixture
    def audit(self):
        return AuditLogger()
    
    @pytest.mark.asyncio
    async def test_log_event(self, audit):
        result = await audit.log(
            tenant_id="tenant-1",
            actor="user@example.com",
            action="login",
            resource_type="session",
        )
        assert result is not None
        assert "signature" in result


class TestHelpers:
    def test_generate_api_key(self):
        key = generate_api_key()
        assert key.startswith("hnt_")
        assert len(key) > 40
    
    def test_hash_api_key(self):
        key = "hnt_testkey123"
        hashed = hash_api_key(key)
        assert hashed != key
        assert len(hashed) == 64
    
    def test_verify_webhook_signature_valid(self):
        payload = b'{"test": "data"}'
        secret = "webhook_secret"
        import hmac
        import hashlib
        sig = f"sha256={hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()}"
        assert verify_webhook_signature(payload, sig, secret) is True
    
    def test_verify_webhook_signature_invalid(self):
        assert verify_webhook_signature(b"data", "sha256=invalid", "secret") is False
    
    def test_sanitize_log_data(self):
        data = {
            "user": "john",
            "password": "secret123",
            "api_key": "key123",
            "normal": "value",
        }
        sanitized = sanitize_log_data(data)
        assert sanitized["user"] == "john"
        assert sanitized["password"] == "[REDACTED]"
        assert sanitized["api_key"] == "[REDACTED]"
        assert sanitized["normal"] == "value"
