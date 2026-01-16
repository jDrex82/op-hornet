"""HORNET Incident Repository - Tenant Aware with Campaign Correlation"""
from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID, uuid4
from datetime import datetime, timedelta
from sqlalchemy import text
import structlog
import json

from hornet.db import get_tenant_session, current_tenant_id

logger = structlog.get_logger()


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
        effective_tenant = tenant_id or current_tenant_id.get()
        if not effective_tenant:
            logger.error("no_tenant_for_incident_creation")
            return False

        async for session in get_tenant_session():
            try:
                await session.execute(
                    text("""
                        INSERT INTO incidents (id, tenant_id, state, severity, confidence, tokens_used, token_budget, created_at, updated_at)
                        VALUES (:id, :tenant_id, 'DETECTION', :severity, 0.0, 0, 50000, NOW(), NOW())
                        ON CONFLICT (id) DO NOTHING
                    """),
                    {"id": incident_id, "tenant_id": effective_tenant, "severity": (severity or "MEDIUM").upper()}
                )
                
                # Index entities for this incident
                if event_data:
                    entities = event_data.get("entities", [])
                    await self._index_incident_entities(session, incident_id, effective_tenant, entities)
                
                await session.commit()
                logger.info("incident_persisted", incident_id=str(incident_id), tenant_id=str(effective_tenant))
                return True
            except Exception as e:
                logger.error("incident_persist_failed", error=str(e))
                await session.rollback()
                return False

    async def _index_incident_entities(
        self,
        session,
        incident_id: UUID,
        tenant_id: UUID,
        entities: List[Dict]
    ):
        """Index entities for fast cross-incident lookups."""
        for entity in entities:
            entity_type = entity.get("type", "unknown")
            entity_value = entity.get("value", "")
            if entity_value:
                try:
                    await session.execute(
                        text("""
                            INSERT INTO incident_entities (incident_id, tenant_id, entity_type, entity_value)
                            VALUES (:incident_id, :tenant_id, :entity_type, :entity_value)
                            ON CONFLICT DO NOTHING
                        """),
                        {
                            "incident_id": incident_id,
                            "tenant_id": tenant_id,
                            "entity_type": entity_type,
                            "entity_value": entity_value
                        }
                    )
                except Exception as e:
                    logger.warning("entity_index_failed", entity=entity_value, error=str(e))

    async def update_incident(
        self,
        incident_id: UUID,
        state: str = None,
        confidence: float = None,
        severity: str = None,
        tokens_used: int = None,
        verdict: str = None,
        summary: str = None,
        campaign_id: UUID = None,
        **kwargs
    ) -> None:
        async for session in get_tenant_session():
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
                if campaign_id is not None:
                    updates.append("campaign_id = :campaign_id")
                    params["campaign_id"] = campaign_id
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
        async for session in get_tenant_session():
            result = await session.execute(
                text("SELECT * FROM incidents WHERE id = :id"),
                {"id": incident_id}
            )
            row = result.mappings().first()
            return dict(row) if row else None

    async def list_incidents(
        self,
        tenant_id: UUID = None,
        state: str = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        async for session in get_tenant_session():
            where_clauses = []
            params = {"limit": limit, "offset": offset}

            effective_tenant = tenant_id or current_tenant_id.get()
            if effective_tenant:
                where_clauses.append("tenant_id = :tenant_id")
                params["tenant_id"] = str(effective_tenant)

            if state:
                where_clauses.append("state = :state")
                params["state"] = state
            where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
            sql = f"SELECT * FROM incidents {where_sql} ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
            result = await session.execute(text(sql), params)
            return [dict(row) for row in result.mappings().all()]

    async def add_finding(
        self,
        incident_id: UUID,
        agent: str,
        finding_type: str,
        confidence: float,
        content,
        reasoning: str = "",
        severity: str = "MEDIUM",
        tokens_consumed: int = 0
    ) -> bool:
        tenant_id = current_tenant_id.get()
        if not tenant_id:
            logger.error("no_tenant_for_finding")
            return False

        async for session in get_tenant_session():
            try:
                await session.execute(
                    text("""
                        INSERT INTO agent_findings
                        (incident_id, tenant_id, agent, finding_type, confidence, content, reasoning, severity, tokens_consumed, created_at)
                        VALUES (:inc_id, :tenant_id, :agent, :type, :conf, :content, :reason, :sev, :tokens, NOW())
                    """),
                    {
                        "inc_id": incident_id,
                        "tenant_id": tenant_id,
                        "agent": agent,
                        "type": finding_type,
                        "conf": confidence,
                        "content": json.dumps(content) if isinstance(content, dict) else str(content),
                        "reason": reasoning,
                        "sev": severity,
                        "tokens": tokens_consumed
                    }
                )
                await session.commit()
                logger.debug("finding_added", agent=agent, incident_id=str(incident_id))
                return True
            except Exception as e:
                logger.error("add_finding_failed", agent=agent, error=str(e))
                await session.rollback()
                return False

    async def get_findings(self, incident_id: UUID) -> List[Dict[str, Any]]:
        async for session in get_tenant_session():
            try:
                result = await session.execute(
                    text("SELECT * FROM agent_findings WHERE incident_id = :id ORDER BY created_at"),
                    {"id": incident_id}
                )
                return [dict(row) for row in result.mappings().all()]
            except Exception as e:
                logger.error("get_findings_failed", error=str(e))
                return []

    async def get_recent_findings(self, limit: int = 10) -> List[Dict[str, Any]]:
        async for session in get_tenant_session():
            try:
                result = await session.execute(
                    text("SELECT * FROM agent_findings ORDER BY created_at DESC LIMIT :limit"),
                    {"limit": limit}
                )
                return [dict(row) for row in result.mappings().all()]
            except Exception as e:
                logger.error("get_recent_findings_failed", error=str(e))
                return []

    # =========================================================================
    # CAMPAIGN CORRELATION METHODS
    # =========================================================================

    async def find_incidents_by_entity(
        self,
        entity_type: str,
        entity_value: str,
        minutes_back: int = 60,
        exclude_incident_id: UUID = None
    ) -> List[Dict[str, Any]]:
        """Find incidents containing the same entity within a time window."""
        tenant_id = current_tenant_id.get()
        if not tenant_id:
            return []

        async for session in get_tenant_session():
            try:
                params = {
                    "tenant_id": tenant_id,
                    "entity_type": entity_type,
                    "entity_value": entity_value,
                    "cutoff": datetime.utcnow() - timedelta(minutes=minutes_back)
                }
                
                exclude_clause = ""
                if exclude_incident_id:
                    exclude_clause = "AND i.id != :exclude_id"
                    params["exclude_id"] = exclude_incident_id

                result = await session.execute(
                    text(f"""
                        SELECT DISTINCT i.*, ie.entity_type, ie.entity_value
                        FROM incidents i
                        JOIN incident_entities ie ON i.id = ie.incident_id
                        WHERE ie.tenant_id = :tenant_id
                          AND ie.entity_type = :entity_type
                          AND ie.entity_value = :entity_value
                          AND i.created_at >= :cutoff
                          {exclude_clause}
                        ORDER BY i.created_at DESC
                        LIMIT 50
                    """),
                    params
                )
                return [dict(row) for row in result.mappings().all()]
            except Exception as e:
                logger.error("find_incidents_by_entity_failed", error=str(e))
                return []

    async def find_related_incidents(
        self,
        incident_id: UUID,
        minutes_back: int = 60
    ) -> Dict[str, Any]:
        """Find all incidents related via shared entities."""
        tenant_id = current_tenant_id.get()
        if not tenant_id:
            return {"related_incidents": [], "shared_entities": [], "campaign_score": 0.0}

        async for session in get_tenant_session():
            try:
                # Get entities from current incident
                entities_result = await session.execute(
                    text("""
                        SELECT entity_type, entity_value 
                        FROM incident_entities 
                        WHERE incident_id = :incident_id
                    """),
                    {"incident_id": incident_id}
                )
                current_entities = [dict(row) for row in entities_result.mappings().all()]

                if not current_entities:
                    return {"related_incidents": [], "shared_entities": [], "campaign_score": 0.0}

                cutoff = datetime.utcnow() - timedelta(minutes=minutes_back)
                related = {}
                shared_entities = []

                for entity in current_entities:
                    result = await session.execute(
                        text("""
                            SELECT DISTINCT i.id, i.state, i.severity, i.confidence, i.created_at, i.summary,
                                   ie.entity_type, ie.entity_value
                            FROM incidents i
                            JOIN incident_entities ie ON i.id = ie.incident_id
                            WHERE ie.tenant_id = :tenant_id
                              AND ie.entity_type = :entity_type
                              AND ie.entity_value = :entity_value
                              AND i.created_at >= :cutoff
                              AND i.id != :exclude_id
                            ORDER BY i.created_at DESC
                        """),
                        {
                            "tenant_id": tenant_id,
                            "entity_type": entity["entity_type"],
                            "entity_value": entity["entity_value"],
                            "cutoff": cutoff,
                            "exclude_id": incident_id
                        }
                    )
                    
                    rows = result.mappings().all()
                    if rows:
                        shared_entities.append({
                            "type": entity["entity_type"],
                            "value": entity["entity_value"],
                            "incident_count": len(rows)
                        })
                        
                        for row in rows:
                            inc_id = str(row["id"])
                            if inc_id not in related:
                                related[inc_id] = {
                                    "id": inc_id,
                                    "state": row["state"],
                                    "severity": row["severity"],
                                    "confidence": row["confidence"],
                                    "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                                    "summary": row["summary"],
                                    "shared_entities": []
                                }
                            related[inc_id]["shared_entities"].append({
                                "type": entity["entity_type"],
                                "value": entity["entity_value"]
                            })

                # Calculate campaign score
                campaign_score = 0.0
                if related:
                    incident_factor = min(len(related) / 5.0, 1.0)
                    entity_types = set(e["type"] for e in shared_entities)
                    diversity_factor = min(len(entity_types) / 3.0, 1.0)
                    max_appearances = max((e["incident_count"] for e in shared_entities), default=1)
                    frequency_factor = min(max_appearances / 3.0, 1.0)
                    campaign_score = (incident_factor * 0.4 + diversity_factor * 0.3 + frequency_factor * 0.3)

                return {
                    "related_incidents": list(related.values()),
                    "shared_entities": shared_entities,
                    "campaign_score": campaign_score,
                    "is_campaign": campaign_score >= 0.5 or len(related) >= 3
                }

            except Exception as e:
                logger.error("find_related_incidents_failed", error=str(e))
                return {"related_incidents": [], "shared_entities": [], "campaign_score": 0.0}

    async def link_incidents(
        self,
        incident_a: UUID,
        incident_b: UUID,
        link_type: str,
        shared_entities: List[Dict] = None,
        confidence: float = 0.8,
        link_reason: str = ""
    ) -> bool:
        """Link two incidents as part of a campaign."""
        tenant_id = current_tenant_id.get()
        if not tenant_id:
            return False

        async for session in get_tenant_session():
            try:
                await session.execute(
                    text("""
                        INSERT INTO incident_links (incident_a, incident_b, tenant_id, link_type, shared_entities, confidence, link_reason)
                        VALUES (:a, :b, :tenant_id, :link_type, :shared_entities, :confidence, :reason)
                        ON CONFLICT DO NOTHING
                    """),
                    {
                        "a": incident_a,
                        "b": incident_b,
                        "tenant_id": tenant_id,
                        "link_type": link_type,
                        "shared_entities": json.dumps(shared_entities or []),
                        "confidence": confidence,
                        "reason": link_reason
                    }
                )
                await session.commit()
                logger.info("incidents_linked", a=str(incident_a), b=str(incident_b), type=link_type)
                return True
            except Exception as e:
                logger.error("link_incidents_failed", error=str(e))
                await session.rollback()
                return False

    async def get_campaign_incidents(self, incident_id: UUID) -> List[Dict[str, Any]]:
        """Get all incidents linked to this one (campaign members)."""
        tenant_id = current_tenant_id.get()
        if not tenant_id:
            return []

        async for session in get_tenant_session():
            try:
                result = await session.execute(
                    text("""
                        WITH RECURSIVE campaign AS (
                            SELECT :incident_id::uuid as incident_id, 0 as depth
                            UNION
                            SELECT 
                                CASE 
                                    WHEN il.incident_a = c.incident_id THEN il.incident_b
                                    ELSE il.incident_a
                                END as incident_id,
                                c.depth + 1
                            FROM incident_links il
                            JOIN campaign c ON (il.incident_a = c.incident_id OR il.incident_b = c.incident_id)
                            WHERE c.depth < 10
                        )
                        SELECT DISTINCT i.*, c.depth
                        FROM incidents i
                        JOIN campaign c ON i.id = c.incident_id
                        WHERE i.tenant_id = :tenant_id
                        ORDER BY i.created_at ASC
                    """),
                    {"incident_id": incident_id, "tenant_id": tenant_id}
                )
                return [dict(row) for row in result.mappings().all()]
            except Exception as e:
                logger.error("get_campaign_incidents_failed", error=str(e))
                return []

    async def create_campaign(self, incident_ids: List[UUID], campaign_name: str = None) -> Optional[UUID]:
        """Create a campaign grouping multiple incidents."""
        tenant_id = current_tenant_id.get()
        if not tenant_id or not incident_ids:
            return None

        campaign_id = uuid4()
        
        async for session in get_tenant_session():
            try:
                for inc_id in incident_ids:
                    await session.execute(
                        text("UPDATE incidents SET campaign_id = :campaign_id WHERE id = :id AND tenant_id = :tenant_id"),
                        {"campaign_id": campaign_id, "id": inc_id, "tenant_id": tenant_id}
                    )
                
                for i, inc_a in enumerate(incident_ids):
                    for inc_b in incident_ids[i+1:]:
                        await session.execute(
                            text("""
                                INSERT INTO incident_links (incident_a, incident_b, tenant_id, link_type, confidence)
                                VALUES (:a, :b, :tenant_id, 'campaign', 0.95)
                                ON CONFLICT DO NOTHING
                            """),
                            {"a": inc_a, "b": inc_b, "tenant_id": tenant_id}
                        )
                
                await session.commit()
                logger.info("campaign_created", campaign_id=str(campaign_id), incidents=len(incident_ids))
                return campaign_id
            except Exception as e:
                logger.error("create_campaign_failed", error=str(e))
                await session.rollback()
                return None

    async def get_entity_timeline(
        self,
        entity_type: str,
        entity_value: str,
        hours_back: int = 24
    ) -> List[Dict[str, Any]]:
        """Get timeline of all incidents involving an entity."""
        tenant_id = current_tenant_id.get()
        if not tenant_id:
            return []

        async for session in get_tenant_session():
            try:
                result = await session.execute(
                    text("""
                        SELECT i.id, i.state, i.severity, i.confidence, i.summary, i.created_at,
                               array_agg(DISTINCT af.agent) as agents,
                               array_agg(DISTINCT af.finding_type) as finding_types
                        FROM incidents i
                        JOIN incident_entities ie ON i.id = ie.incident_id
                        LEFT JOIN agent_findings af ON i.id = af.incident_id
                        WHERE ie.tenant_id = :tenant_id
                          AND ie.entity_type = :entity_type
                          AND ie.entity_value = :entity_value
                          AND i.created_at >= :cutoff
                        GROUP BY i.id
                        ORDER BY i.created_at ASC
                    """),
                    {
                        "tenant_id": tenant_id,
                        "entity_type": entity_type,
                        "entity_value": entity_value,
                        "cutoff": datetime.utcnow() - timedelta(hours=hours_back)
                    }
                )
                return [dict(row) for row in result.mappings().all()]
            except Exception as e:
                logger.error("get_entity_timeline_failed", error=str(e))
                return []


incident_repo = IncidentRepository()
