"""
HORNET Middleware
Authentication, rate limiting, and request processing.
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Callable, Any
import hashlib
import time
import structlog

from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = structlog.get_logger()


# ============================================================================
# API KEY AUTHENTICATION
# ============================================================================

class APIKeyAuth:
    """API Key authentication handler."""
    
    def __init__(self, db_session_factory=None):
        self.db = db_session_factory
        self._key_cache: Dict[str, dict] = {}
        self._cache_ttl = 300
    
    def _hash_key(self, api_key: str) -> str:
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    async def validate_key(self, api_key: str) -> Optional[dict]:
        if not api_key or not api_key.startswith("hnt_"):
            return None
        key_hash = self._hash_key(api_key)
        cached = self._key_cache.get(key_hash)
        if cached and cached["expires"] > time.time():
            return cached["tenant"]
        tenant = {"tenant_id": "default-tenant", "name": "Default Tenant", "tier": "enterprise", "rate_limit": 1000}
        self._key_cache[key_hash] = {"tenant": tenant, "expires": time.time() + self._cache_ttl}
        return tenant


api_key_auth = APIKeyAuth()
security = HTTPBearer(auto_error=False)


async def get_current_tenant(request: Request, credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> dict:
    api_key = credentials.credentials if credentials else request.headers.get("X-API-Key") or request.query_params.get("api_key")
    if not api_key:
        raise HTTPException(status_code=401, detail="API key required")
    tenant = await api_key_auth.validate_key(api_key)
    if not tenant:
        raise HTTPException(status_code=401, detail="Invalid API key")
    request.state.tenant = tenant
    return tenant


async def get_optional_tenant(request: Request, credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[dict]:
    try:
        return await get_current_tenant(request, credentials)
    except HTTPException:
        return None


# ============================================================================
# RATE LIMITING
# ============================================================================

class RateLimiter:
    def __init__(self, redis_client=None):
        self.redis = redis_client
        self._local_buckets: Dict[str, dict] = {}
    
    async def is_allowed(self, key: str, max_requests: int, window_seconds: int) -> tuple:
        now = time.time()
        bucket = self._local_buckets.get(key, {"requests": [], "window_start": now})
        window_start = now - window_seconds
        bucket["requests"] = [r for r in bucket["requests"] if r > window_start]
        current_count = len(bucket["requests"])
        allowed = current_count < max_requests
        if allowed:
            bucket["requests"].append(now)
        self._local_buckets[key] = bucket
        return allowed, {"limit": max_requests, "remaining": max(0, max_requests - current_count - 1), "reset": int(now + window_seconds)}


rate_limiter = RateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    TIER_LIMITS = {"free": {"requests": 100, "window": 3600}, "starter": {"requests": 1000, "window": 3600}, "enterprise": {"requests": 10000, "window": 3600}}
    ENDPOINT_LIMITS = {"/api/v1/events": {"requests": 1000, "window": 60}}
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path.startswith("/api/v1/health") or request.url.path in ["/", "/metrics", "/dashboard"]:
            return await call_next(request)
        tenant = getattr(request.state, "tenant", None)
        if not tenant:
            return await call_next(request)
        tenant_id = tenant.get("tenant_id", "unknown")
        tier = tenant.get("tier", "free")
        limits = self.ENDPOINT_LIMITS.get(request.url.path, self.TIER_LIMITS.get(tier, self.TIER_LIMITS["free"]))
        key = f"{tenant_id}:{request.url.path}"
        allowed, info = await rate_limiter.is_allowed(key, limits["requests"], limits["window"])
        headers = {"X-RateLimit-Limit": str(info["limit"]), "X-RateLimit-Remaining": str(info["remaining"]), "X-RateLimit-Reset": str(info["reset"])}
        if not allowed:
            return Response(content='{"error": "rate_limit_exceeded"}', status_code=429, headers=headers, media_type="application/json")
        response = await call_next(request)
        for k, v in headers.items():
            response.headers[k] = v
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID", str(time.time_ns()))
        start_time = time.time()
        request.state.request_id = request_id
        try:
            response = await call_next(request)
            logger.info("http_request", request_id=request_id, method=request.method, path=request.url.path, status_code=response.status_code, duration_ms=round((time.time() - start_time) * 1000, 2))
            response.headers["X-Request-ID"] = request_id
            return response
        except Exception as e:
            logger.error("http_request_error", request_id=request_id, error=str(e))
            raise
