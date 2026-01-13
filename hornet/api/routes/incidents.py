"""HORNET Incidents API"""
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Request, Query
from pydantic import BaseModel, Field
from hornet.middleware import get_current_tenant
from hornet.repository import incident_repo

router = APIRouter()


class ActionApproval(BaseModel):
    response_type: str = Field(..., description="APPROVE|REJECT|MODIFY")
    justification: str = Field(default="")
    modifications: Optional[dict] = None


@router.get("")
async def list_incidents(
    request: Request,
    tenant: dict = Depends(get_current_tenant),
    state: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
    offset: int = Query(0),
):
    """List incidents for tenant."""
    try:
        incidents = await incident_repo.list_incidents(
            tenant_id=None,  # For now, list all
            state=state,
            limit=limit,
            offset=offset,
        )
        return {
            "data": incidents,
            "meta": {"total": len(incidents), "limit": limit, "offset": offset}
        }
    except Exception as e:
        return {"data": [], "meta": {"total": 0, "limit": limit, "offset": offset, "error": str(e)}}


@router.get("/{incident_id}")
async def get_incident(
    incident_id: UUID,
    tenant: dict = Depends(get_current_tenant),
):
    """Get a specific incident."""
    incident = await incident_repo.get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    findings = await incident_repo.get_findings(incident_id)
    incident["findings"] = findings
    return incident


@router.get("/{incident_id}/timeline")
async def get_incident_timeline(
    incident_id: UUID,
    tenant: dict = Depends(get_current_tenant),
):
    """Get incident timeline."""
    incident = await incident_repo.get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return {"timeline": [], "incident_id": str(incident_id)}


@router.post("/{incident_id}/action")
async def submit_action(
    incident_id: UUID,
    action: ActionApproval,
    tenant: dict = Depends(get_current_tenant),
):
    """Submit human decision on incident action."""
    incident = await incident_repo.get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    return {
        "incident_id": str(incident_id),
        "action": action.response_type,
        "status": "accepted"
    }
