"""Test middleware components."""
import pytest
import time
from hornet.middleware import RateLimiter, APIKeyAuth


class TestRateLimiter:
    @pytest.fixture
    def limiter(self):
        return RateLimiter()
    
    @pytest.mark.asyncio
    async def test_allows_under_limit(self, limiter):
        allowed, info = await limiter.is_allowed("test_key", max_requests=10, window_seconds=60)
        assert allowed is True
        assert info["remaining"] == 9
    
    @pytest.mark.asyncio
    async def test_blocks_over_limit(self, limiter):
        for i in range(10):
            await limiter.is_allowed("test_key_2", max_requests=10, window_seconds=60)
        allowed, info = await limiter.is_allowed("test_key_2", max_requests=10, window_seconds=60)
        assert allowed is False
        assert info["remaining"] == 0


class TestAPIKeyAuth:
    @pytest.fixture
    def auth(self):
        return APIKeyAuth()
    
    @pytest.mark.asyncio
    async def test_valid_key_format(self, auth):
        result = await auth.validate_key("hnt_validkey123")
        assert result is not None
        assert "tenant_id" in result
    
    @pytest.mark.asyncio
    async def test_invalid_key_format(self, auth):
        result = await auth.validate_key("invalid_key")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_empty_key(self, auth):
        result = await auth.validate_key("")
        assert result is None
