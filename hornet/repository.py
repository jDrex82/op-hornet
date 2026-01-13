"""HORNET Incident Repository - Fixed"""
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
import structlog

from hornet.config import get_settings

logger = structlog.get_logger()
settings = get_settings()

engine = create_async_engine(settings.DATABASE_URL, pool_size=20, max_overflow=10)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

DEFAULT_TENANT = UUID("00000000-0000-0000-0000-000000000001")


class IncidentRepository:

    async def create_incident(
        self,
        incident_id: UUID,
        tenant_id: UUID = None,
        event_id: UUID = None,
        event_data: Dict[str, Any] = None,
        severity: str = "MEDIUM",
        **kwargs
    ) -> bool:
        async with async_session() as session:
            try:
                await session.execute(
                    text("""
                        INSERT INTO incidents (id, tenant_id, state, severity, confidence, tokens_used, token_budget, created_at, updated_at)
                        VALUES (:id, :tenant_id, 'DETECTION', :severity, 0.0, 0, 50000, NOW(), NOW())
                        ON CONFLICT (id) DO NOTHING
                    """),
                    {"id": incident_id, "tenant_id": DEFAULT_TENANT, "severity": (severity or "MEDIUM").upper()}
                )
                await session.commit()
                logger.info("incident_persisted", incident_id=str(incident_id))
                return True
            except Exception as e:
                logger.error("incident_persist_failed", error=str(e))
                await session.rollback()
                return False

    async def update_incident(
        self,
        incident_id: UUID,
        state: str = None,
        confidence: float = None,
        severity: str = None,
        tokens_used: int = None,
        verdict: str = None,
        summary: str = None,
        **kwargs  # Accept any extra args
    ) -> None:
        async with async_session() as session:
            try:
                updates = ["updated_at = NOW()"]
                params = {"id": incident_id}
                
                if state is not None:
                    updates.append("state = :state")
                    params["state"] = state
                if confidence is not None:
                    updates.append("confidence = :confidence")
                    params["confidence"] = confidence
                if tokens_used is not None:
                    updates.append("tokens_used = :tokens_used")
                    params["tokens_used"] = tokens_used
                if summary is not None:
                    updates.append("summary = :summary")
                    params["summary"] = str(summary)[:1000] if summary else None
                if state == "CLOSED":
                    updates.append("closed_at = NOW()")
                
                sql = f"UPDATE incidents SET {', '.join(updates)} WHERE id = :id"
                await session.execute(text(sql), params)
                await session.commit()
                logger.debug("incident_updated", incident_id=str(incident_id))
            except Exception as e:
                logger.error("incident_update_failed", error=str(e))
                await session.rollback()

    async def get_incident(self, incident_id: UUID) -> Optional[Dict[str, Any]]:
        async with async_session() as session:
            result = await session.execute(text("SELECT * FROM incidents WHERE id = :id"), {"id": incident_id})
            row = result.mappings().first()
            return dict(row) if row else None

    async def list_incidents(self, tenant_id: UUID = None, state: str = None, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        async with async_session() as session:
            where_clauses = []
            params = {"limit": limit, "offset": offset}
            if state:
                where_clauses.append("state = :state")
                params["state"] = state
            where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
            sql = f"SELECT * FROM incidents {where_sql} ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
            result = await session.execute(text(sql), params)
            return [dict(row) for row in result.mappings().all()]





    async def add_finding(self, incident_id: UUID, agent: str, finding_type: str, confidence: float, content, reasoning: str = "", severity: str = "MEDIUM", tokens_consumed: int = 0) -> bool:
        """Persist an agent finding to the database."""
        async with async_session() as session:
            try:
                await session.execute(
                    text("""INSERT INTO agent_findings (incident_id, agent, finding_type, confidence, content, reasoning, severity, tokens_consumed, created_at)
                            VALUES (:inc_id, :agent, :type, :conf, :content, :reason, :sev, :tokens, NOW())"""),
                    {"inc_id": incident_id, "agent": agent, "type": finding_type, "conf": confidence,
                     "content": __import__("json").dumps(content) if isinstance(content, dict) else str(content),
                     "reason": reasoning, "sev": severity, "tokens": tokens_consumed}
                )
                await session.commit()
                logger.debug("finding_added", agent=agent, incident_id=str(incident_id))
                return True
            except Exception as e:
                logger.error("add_finding_failed", agent=agent, error=str(e))
                return False

incident_repo = IncidentRepository()
