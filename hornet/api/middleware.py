"""
HORNET API Middleware
Authentication, rate limiting, and request processing.
"""
import time
import hashlib
from typing import Optional, Dict, Callable, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import asyncio
import structlog

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from hornet.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


# ============================================================================
# API Key Authentication
# ============================================================================

class APIKeyAuth:
    """API Key authentication and tenant resolution."""
    
    def __init__(self):
        self._key_cache: Dict[str, Tuple[str, datetime]] = {}  # hash -> (tenant_id, expires)
        self._cache_ttl = timedelta(minutes=5)
    
    def _hash_key(self, api_key: str) -> str:
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    async def validate_key(self, api_key: str, db_session=None) -> Optional[str]:
        """Validate API key and return tenant_id if valid."""
        if not api_key:
            return None
        
        key_hash = self._hash_key(api_key)
        
        # Check cache
        if key_hash in self._key_cache:
            tenant_id, expires = self._key_cache[key_hash]
            if datetime.utcnow() < expires:
                return tenant_id
            else:
                del self._key_cache[key_hash]
        
        # Validate against database
        # In production, would query: SELECT tenant_id FROM tenants WHERE api_key_hash = $1 AND is_active = true
        # For now, accept keys starting with "hnt_" and extract tenant from key
        if api_key.startswith("hnt_"):
            # Demo: extract tenant from key format hnt_<tenant>_<random>
            parts = api_key.split("_")
            if len(parts) >= 3:
                tenant_id = parts[1]
                self._key_cache[key_hash] = (tenant_id, datetime.utcnow() + self._cache_ttl)
                return tenant_id
        
        return None
    
    def invalidate_key(self, api_key: str):
        """Invalidate a cached API key."""
        key_hash = self._hash_key(api_key)
        self._key_cache.pop(key_hash, None)


api_key_auth = APIKeyAuth()


class AuthMiddleware(BaseHTTPMiddleware):
    """Authentication middleware for API requests."""
    
    EXEMPT_PATHS = {
        "/", "/health", "/api/v1/health", "/api/v1/health/live", 
        "/api/v1/health/ready", "/metrics", "/dashboard", "/docs", 
        "/openapi.json", "/redoc"
    }
    
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        
        # Skip auth for exempt paths
        if path in self.EXEMPT_PATHS or path.startswith("/dashboard"):
            return await call_next(request)
        
        # Extract API key from header
        api_key = request.headers.get("X-API-Key") or request.headers.get("Authorization", "").replace("Bearer ", "")
        
        if not api_key:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"error": "missing_api_key", "message": "API key required"}
            )
        
        # Validate key
        tenant_id = await api_key_auth.validate_key(api_key)
        
        if not tenant_id:
            logger.warning("invalid_api_key", path=path)
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"error": "invalid_api_key", "message": "Invalid or expired API key"}
            )
        
        # Attach tenant_id to request state
        request.state.tenant_id = tenant_id
        request.state.api_key = api_key
        
        return await call_next(request)


# ============================================================================
# Rate Limiting
# ============================================================================

class RateLimiter:
    """Token bucket rate limiter with per-tenant limits."""
    
    def __init__(self):
        # tenant_id -> {tokens, last_update}
        self._buckets: Dict[str, Dict] = defaultdict(lambda: {"tokens": 100, "last_update": time.time()})
        self._lock = asyncio.Lock()
    
    # Default limits per tier
    TIER_LIMITS = {
        "free": {"requests_per_minute": 60, "burst": 10},
        "pro": {"requests_per_minute": 300, "burst": 50},
        "enterprise": {"requests_per_minute": 1000, "burst": 100},
    }
    
    async def check_rate_limit(self, tenant_id: str, tier: str = "pro") -> Tuple[bool, Dict]:
        """Check if request is allowed under rate limit."""
        limits = self.TIER_LIMITS.get(tier, self.TIER_LIMITS["pro"])
        max_tokens = limits["burst"]
        refill_rate = limits["requests_per_minute"] / 60.0  # tokens per second
        
        async with self._lock:
            bucket = self._buckets[tenant_id]
            now = time.time()
            elapsed = now - bucket["last_update"]
            
            # Refill tokens
            bucket["tokens"] = min(max_tokens, bucket["tokens"] + elapsed * refill_rate)
            bucket["last_update"] = now
            
            if bucket["tokens"] >= 1:
                bucket["tokens"] -= 1
                return True, {
                    "remaining": int(bucket["tokens"]),
                    "limit": limits["requests_per_minute"],
                    "reset": int(now + (max_tokens - bucket["tokens"]) / refill_rate)
                }
            else:
                retry_after = (1 - bucket["tokens"]) / refill_rate
                return False, {
                    "remaining": 0,
                    "limit": limits["requests_per_minute"],
                    "reset": int(now + retry_after),
                    "retry_after": int(retry_after) + 1
                }


rate_limiter = RateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware."""
    
    EXEMPT_PATHS = {"/", "/health", "/api/v1/health", "/metrics", "/dashboard"}
    
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        
        if path in self.EXEMPT_PATHS or path.startswith("/dashboard"):
            return await call_next(request)
        
        tenant_id = getattr(request.state, "tenant_id", "anonymous")
        tier = getattr(request.state, "tier", "pro")
        
        allowed, info = await rate_limiter.check_rate_limit(tenant_id, tier)
        
        if not allowed:
            logger.warning("rate_limit_exceeded", tenant_id=tenant_id, path=path)
            response = JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"error": "rate_limit_exceeded", "retry_after": info["retry_after"]}
            )
            response.headers["Retry-After"] = str(info["retry_after"])
            response.headers["X-RateLimit-Limit"] = str(info["limit"])
            response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
            response.headers["X-RateLimit-Reset"] = str(info["reset"])
            return response
        
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
        response.headers["X-RateLimit-Reset"] = str(info["reset"])
        
        return response


# ============================================================================
# Request Logging
# ============================================================================

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Structured request logging middleware."""
    
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", f"req_{int(time.time() * 1000)}")
        start_time = time.time()
        
        # Bind request context to logger
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            tenant_id=getattr(request.state, "tenant_id", None),
        )
        
        try:
            response = await call_next(request)
            
            duration_ms = (time.time() - start_time) * 1000
            logger.info(
                "request_completed",
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2),
            )
            
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"
            
            return response
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                "request_failed",
                error=str(e),
                duration_ms=round(duration_ms, 2),
            )
            raise


# ============================================================================
# Tenant Context
# ============================================================================

class TenantContextMiddleware(BaseHTTPMiddleware):
    """Sets database tenant context for RLS."""
    
    async def dispatch(self, request: Request, call_next):
        tenant_id = getattr(request.state, "tenant_id", None)
        
        if tenant_id:
            # Would set PostgreSQL session variable for RLS
            # await db.execute(f"SET app.current_tenant_id = '{tenant_id}'")
            pass
        
        return await call_next(request)
