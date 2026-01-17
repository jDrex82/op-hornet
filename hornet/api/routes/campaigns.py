"""HORNET Campaign API Routes"""
from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from hornet.middleware import get_current_tenant
from hornet.repository import incident_repo
from hornet.db import get_tenant_session
from sqlalchemy import text

router = APIRouter()


@router.get("/graph")
async def get_campaign_graph(
    tenant: dict = Depends(get_current_tenant),
    hours_back: int = Query(24, le=168),
):
    """Get campaign graph data for visualization."""
    async for session in get_tenant_session():
        # Get all incidents with links
        incidents_result = await session.execute(
            text("""
                SELECT i.id, i.state, i.severity, i.confidence, i.summary, i.created_at,
                       COUNT(DISTINCT ie.entity_value) as entity_count
                FROM incidents i
                LEFT JOIN incident_entities ie ON i.id = ie.incident_id
                WHERE i.created_at >= NOW() - INTERVAL ':hours hours'
                GROUP BY i.id
                ORDER BY i.created_at DESC
                LIMIT 100
            """.replace(':hours', str(hours_back)))
        )
        incidents = [dict(row) for row in incidents_result.mappings().all()]
        
        # Get all links
        links_result = await session.execute(
            text("""
                SELECT incident_a, incident_b, link_type, confidence, link_reason
                FROM incident_links
                WHERE created_at >= NOW() - INTERVAL ':hours hours'
            """.replace(':hours', str(hours_back)))
        )
        links = [dict(row) for row in links_result.mappings().all()]
        
        # Format for graph visualization
        nodes = [
            {
                "id": str(i["id"]),
                "severity": i["severity"],
                "state": i["state"],
                "confidence": i["confidence"],
                "summary": i["summary"][:100] if i["summary"] else None,
                "entity_count": i["entity_count"],
                "created_at": i["created_at"].isoformat() if i["created_at"] else None,
            }
            for i in incidents
        ]
        
        edges = [
            {
                "source": str(l["incident_a"]),
                "target": str(l["incident_b"]),
                "link_type": l["link_type"],
                "confidence": l["confidence"],
            }
            for l in links
        ]
        
        return {"nodes": nodes, "edges": edges}


@router.get("/stats")
async def get_campaign_stats(
    tenant: dict = Depends(get_current_tenant),
):
    """Get campaign statistics."""
    async for session in get_tenant_session():
        # Total links
        links_result = await session.execute(
            text("SELECT COUNT(*) as total FROM incident_links")
        )
        total_links = links_result.scalar()
        
        # High confidence links
        high_conf_result = await session.execute(
            text("SELECT COUNT(*) as total FROM incident_links WHERE confidence >= 0.7")
        )
        high_confidence_links = high_conf_result.scalar()
        
        # Linked incidents count
        linked_result = await session.execute(
            text("""
                SELECT COUNT(DISTINCT incident_id) as total
                FROM (
                    SELECT incident_a as incident_id FROM incident_links
                    UNION
                    SELECT incident_b as incident_id FROM incident_links
                ) linked
            """)
        )
        linked_incidents = linked_result.scalar()
        
        # Top shared entities
        entities_result = await session.execute(
            text("""
                SELECT entity_type, entity_value, COUNT(DISTINCT incident_id) as incident_count
                FROM incident_entities
                GROUP BY entity_type, entity_value
                HAVING COUNT(DISTINCT incident_id) >= 2
                ORDER BY incident_count DESC
                LIMIT 10
            """)
        )
        top_entities = [dict(row) for row in entities_result.mappings().all()]
        
        # Link types breakdown
        types_result = await session.execute(
            text("""
                SELECT link_type, COUNT(*) as count, AVG(confidence) as avg_confidence
                FROM incident_links
                GROUP BY link_type
                ORDER BY count DESC
            """)
        )
        link_types = [dict(row) for row in types_result.mappings().all()]
        
        return {
            "total_links": total_links,
            "high_confidence_links": high_confidence_links,
            "linked_incidents": linked_incidents,
            "top_shared_entities": top_entities,
            "link_types": link_types,
        }


@router.get("/{incident_id}/related")
async def get_related_incidents(
    incident_id: UUID,
    tenant: dict = Depends(get_current_tenant),
):
    """Get incidents related to a specific incident via links."""
    related = await incident_repo.find_related_incidents(incident_id)
    campaign_members = await incident_repo.get_campaign_incidents(incident_id)
    
    return {
        "incident_id": str(incident_id),
        "related": related,
        "campaign_members": [
            {
                "id": str(m["id"]),
                "state": m["state"],
                "severity": m["severity"],
                "confidence": m["confidence"],
                "created_at": m["created_at"].isoformat() if m["created_at"] else None,
            }
            for m in campaign_members
        ],
    }


@router.get("/{incident_id}/entities")
async def get_incident_entities(
    incident_id: UUID,
    tenant: dict = Depends(get_current_tenant),
):
    """Get entities associated with an incident."""
    async for session in get_tenant_session():
        result = await session.execute(
            text("""
                SELECT entity_type, entity_value, created_at
                FROM incident_entities
                WHERE incident_id = :incident_id
            """),
            {"incident_id": incident_id}
        )
        entities = [dict(row) for row in result.mappings().all()]
        
        return {
            "incident_id": str(incident_id),
            "entities": entities,
        }
