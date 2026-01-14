"""
HORNET Middleware
Tenant-aware authentication with RLS context setting.
"""
from datetime import datetime
from typing import Optional, Dict, Callable
import hashlib
import time
import structlog

from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from sqlalchemy import text

from hornet.db import set_tenant_context, clear_tenant_context, engine

logger = structlog.get_logger()


class APIKeyAuth:
    """API Key authentication with database lookup."""

    def __init__(self):
        self._key_cache: Dict[str, dict] = {}
        self._cache_ttl = 300  # 5 minutes

    def _hash_key(self, api_key: str) -> str:
        return hashlib.sha256(api_key.encode()).hexdigest()

    async def validate_key(self, api_key: str) -> Optional[dict]:
        """Validate API key and return tenant info."""
        if not api_key or not api_key.startswith("hnt_"):
            return None

        key_hash = self._hash_key(api_key)

        # Check cache first
        cached = self._key_cache.get(key_hash)
        if cached and cached["expires"] > time.time():
            return cached["tenant"]

        # Query database (using superuser connection for auth lookup)
        try:
            async with engine.connect() as conn:
                result = await conn.execute(
                    text("""
                        SELECT 
                            ak.id as key_id,
                            ak.tenant_id,
                            ak.scopes,
                            ak.name as key_name,
                            t.name as tenant_name,
                            t.is_active
                        FROM api_keys ak
                        JOIN tenants t ON ak.tenant_id = t.id
                        WHERE ak.key_hash = :key_hash
                          AND ak.is_active = true
                          AND t.is_active = true
                          AND (ak.expires_at IS NULL OR ak.expires_at > NOW())
                    """),
                    {"key_hash": key_hash}
                )
                row = result.mappings().first()

                if not row:
                    return None

                tenant = {
                    "tenant_id": str(row["tenant_id"]),
                    "tenant_name": row["tenant_name"],
                    "key_id": str(row["key_id"]),
                    "key_name": row["key_name"],
                    "scopes": row["scopes"] or ["full"],
                }

                # Update last_used_at
                await conn.execute(
                    text("UPDATE api_keys SET last_used_at = NOW() WHERE id = :key_id"),
                    {"key_id": row["key_id"]}
                )
                await conn.commit()

                # Cache it
                self._key_cache[key_hash] = {
                    "tenant": tenant,
                    "expires": time.time() + self._cache_ttl
                }

                return tenant

        except Exception as e:
            logger.error("api_key_validation_failed", error=str(e))
            return None


api_key_auth = APIKeyAuth()
security = HTTPBearer(auto_error=False)


async def get_current_tenant(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> dict:
    """Validate API key and set tenant context for RLS."""
    api_key = (
        credentials.credentials if credentials
        else request.headers.get("X-API-Key")
        or request.query_params.get("api_key")
    )

    if not api_key:
        raise HTTPException(status_code=401, detail="API key required")

    tenant = await api_key_auth.validate_key(api_key)
    if not tenant:
        raise HTTPException(status_code=401, detail="Invalid API key")

    # Set tenant context for RLS
    set_tenant_context(tenant["tenant_id"])
    request.state.tenant = tenant

    logger.debug("tenant_authenticated", tenant_id=tenant["tenant_id"], key_name=tenant["key_name"])
    return tenant


async def get_optional_tenant(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[dict]:
    """Optional tenant auth - returns None if no valid key."""
    try:
        return await get_current_tenant(request, credentials)
    except HTTPException:
        return None


class TenantContextMiddleware(BaseHTTPMiddleware):
    """Middleware to clear tenant context after each request."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            response = await call_next(request)
            return response
        finally:
            # Always clear tenant context after request
            clear_tenant_context()


class RateLimiter:
    """Simple in-memory rate limiter."""

    def __init__(self):
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
        return allowed, {
            "limit": max_requests,
            "remaining": max(0, max_requests - current_count - 1),
            "reset": int(now + window_seconds)
        }


rate_limiter = RateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting by tenant and endpoint."""

    TIER_LIMITS = {
        "free": {"requests": 100, "window": 3600},
        "starter": {"requests": 1000, "window": 3600},
        "enterprise": {"requests": 10000, "window": 3600}
    }
    ENDPOINT_LIMITS = {
        "/api/v1/events": {"requests": 1000, "window": 60}
    }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for health/public endpoints
        if request.url.path.startswith("/api/v1/health") or request.url.path in ["/", "/metrics", "/dashboard"]:
            return await call_next(request)

        tenant = getattr(request.state, "tenant", None)
        if not tenant:
            return await call_next(request)

        tenant_id = tenant.get("tenant_id", "unknown")
        tier = tenant.get("tier", "free")
        limits = self.ENDPOINT_LIMITS.get(
            request.url.path,
            self.TIER_LIMITS.get(tier, self.TIER_LIMITS["free"])
        )

        key = f"{tenant_id}:{request.url.path}"
        allowed, info = await rate_limiter.is_allowed(key, limits["requests"], limits["window"])

        headers = {
            "X-RateLimit-Limit": str(info["limit"]),
            "X-RateLimit-Remaining": str(info["remaining"]),
            "X-RateLimit-Reset": str(info["reset"])
        }

        if not allowed:
            return Response(
                content='{"error": "rate_limit_exceeded"}',
                status_code=429,
                headers=headers,
                media_type="application/json"
            )

        response = await call_next(request)
        for k, v in headers.items():
            response.headers[k] = v
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Request logging with timing."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID", str(time.time_ns()))
        start_time = time.time()
        request.state.request_id = request_id

        try:
            response = await call_next(request)
            logger.info(
                "http_request",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=round((time.time() - start_time) * 1000, 2),
                tenant_id=getattr(request.state, "tenant", {}).get("tenant_id")
            )
            response.headers["X-Request-ID"] = request_id
            return response
        except Exception as e:
            logger.error("http_request_error", request_id=request_id, error=str(e))
            raise
