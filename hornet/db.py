"""
HORNET Database Module
Tenant-aware async database sessions with RLS enforcement.
"""
from contextvars import ContextVar
from typing import Optional, AsyncGenerator
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import AsyncAdaptedQueuePool
import structlog

from hornet.config import get_settings

logger = structlog.get_logger()
settings = get_settings()

# Context var to hold current tenant ID (set by middleware)
current_tenant_id: ContextVar[Optional[str]] = ContextVar("current_tenant_id", default=None)

# Create engine
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    poolclass=AsyncAdaptedQueuePool,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_tenant_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get a database session with tenant context set.
    RLS policies will automatically filter by tenant.
    """
    tenant_id = current_tenant_id.get()
    
    async with async_session_factory() as session:
        if tenant_id:
            # Validate UUID format to prevent injection
            try:
                UUID(tenant_id)  # Validates format
            except ValueError:
                logger.error("invalid_tenant_id_format", tenant_id=tenant_id)
                raise ValueError("Invalid tenant ID format")
            
            # SET doesn't support parameters in asyncpg, use safe string formatting
            # tenant_id is validated as UUID above
            await session.execute(text(f"SET app.current_tenant_id = '{tenant_id}'"))
            logger.debug("tenant_context_set", tenant_id=tenant_id)
        else:
            logger.warning("no_tenant_context_for_session")
        
        try:
            yield session
        finally:
            # Reset on return to pool
            try:
                await session.execute(text("RESET app.current_tenant_id"))
            except Exception:
                pass  # Connection might be closed


def set_tenant_context(tenant_id: str | UUID) -> None:
    """Set the current tenant ID in the context var."""
    current_tenant_id.set(str(tenant_id))


def get_tenant_context() -> Optional[str]:
    """Get the current tenant ID from context."""
    return current_tenant_id.get()


def clear_tenant_context() -> None:
    """Clear the tenant context."""
    current_tenant_id.set(None)
