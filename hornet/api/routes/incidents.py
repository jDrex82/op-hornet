"""HORNET Incidents API"""
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Request, Query
from pydantic import BaseModel, Field

from hornet.middleware import get_current_tenant

router = APIRouter()


class ActionApproval(BaseModel):
    response_type: str = Field(..., description="APPROVE|REJECT|MODIFY")
    justification: str = Field(default="")
    modifications: Optional[dict] = None


class IncidentSummary(BaseModel):
    id: UUID
    state: str
    severity: Optional[str]
    confidence: float
    summary: Optional[str]
    created_at: datetime
    updated_at: datetime


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
    coordinator = getattr(request.app.state, "coordinator", None)
    
    if coordinator:
        incidents = coordinator.list_incidents(tenant["tenant_id"])
        data = [
            {
                "id": str(i.incident_id),
                "state": i.state.value,
                "severity": i.severity,
                "confidence": i.confidence,
                "summary": i.verdict.get("summary") if i.verdict else None,
                "created_at": i.created_at.isoformat(),
                "updated_at": i.updated_at.isoformat(),
                "tokens_used": i.tokens_used,
                "token_budget": i.token_budget,
                "findings_count": len(i.findings),
            }
            for i in incidents
        ]
    else:
        data = []
    
    return {
        "data": data,
        "meta": {
            "total": len(data),
            "limit": limit,
            "offset": offset,
        }
    }


@router.get("/{incident_id}")
async def get_incident(
    request: Request,
    incident_id: UUID,
    tenant: dict = Depends(get_current_tenant),
):
    """Get incident details."""
    coordinator = getattr(request.app.state, "coordinator", None)
    
    if coordinator:
        context = coordinator.get_incident(incident_id)
        if context and context.tenant_id == tenant["tenant_id"]:
            return {
                "id": str(context.incident_id),
                "state": context.state.value,
                "severity": context.severity,
                "confidence": context.confidence,
                "created_at": context.created_at.isoformat(),
                "updated_at": context.updated_at.isoformat(),
                "tokens_used": context.tokens_used,
                "token_budget": context.token_budget,
                "events": context.events,
                "entities": {k: list(v) for k, v in context.entities.items()},
                "mitre_techniques": list(context.mitre_techniques),
                "findings": [
                    {
                        "agent": f.agent_name,
                        "type": f.output_type,
                        "confidence": f.confidence,
                        "content": f.content,
                        "reasoning": f.reasoning,
                    }
                    for f in context.findings
                ],
                "verdict": context.verdict,
                "proposal": context.proposal,
                "escalation_reason": context.escalation_reason,
            }
    
    raise HTTPException(status_code=404, detail="Incident not found")


@router.get("/{incident_id}/timeline")
async def get_incident_timeline(
    request: Request,
    incident_id: UUID,
    tenant: dict = Depends(get_current_tenant),
):
    """Get incident timeline."""
    coordinator = getattr(request.app.state, "coordinator", None)
    
    if coordinator:
        context = coordinator.get_incident(incident_id)
        if context and context.tenant_id == tenant["tenant_id"]:
            return {"timeline": context.timeline}
    
    raise HTTPException(status_code=404, detail="Incident not found")


@router.post("/{incident_id}/actions/{action_id}/approve")
async def approve_action(
    request: Request,
    incident_id: UUID,
    action_id: str,
    approval: ActionApproval,
    tenant: dict = Depends(get_current_tenant),
):
    """Approve or reject a proposed action."""
    # Record feedback for tuner
    from hornet.tuner import tuner, FeedbackType
    
    feedback_type = {
        "APPROVE": FeedbackType.APPROVE,
        "REJECT": FeedbackType.REJECT,
        "MODIFY": FeedbackType.MODIFY,
    }.get(approval.response_type, FeedbackType.MODIFY)
    
    await tuner.record_feedback(
        incident_id=str(incident_id),
        agent_name="responder",
        feedback_type=feedback_type,
        confidence=0.0,
        user_id=tenant.get("user_id", "unknown"),
        justification=approval.justification,
    )
    
    return {
        "status": "accepted",
        "action_id": action_id,
        "response": approval.response_type,
    }


@router.post("/{incident_id}/escalate")
async def escalate_incident(
    request: Request,
    incident_id: UUID,
    reason: str = Query(...),
    tenant: dict = Depends(get_current_tenant),
):
    """Manually escalate an incident."""
    coordinator = getattr(request.app.state, "coordinator", None)
    
    if coordinator:
        context = coordinator.get_incident(incident_id)
        if context and context.tenant_id == tenant["tenant_id"]:
            from hornet.coordinator import FSMState
            context.escalation_reason = reason
            coordinator._transition_state(context, FSMState.ESCALATED)
            return {"status": "escalated", "incident_id": str(incident_id)}
    
    raise HTTPException(status_code=404, detail="Incident not found")


@router.post("/{incident_id}/close")
async def close_incident(
    request: Request,
    incident_id: UUID,
    outcome: str = Query(..., description="RESOLVED|FALSE_POSITIVE|DUPLICATE|IGNORED"),
    tenant: dict = Depends(get_current_tenant),
):
    """Manually close an incident."""
    coordinator = getattr(request.app.state, "coordinator", None)
    
    if coordinator:
        context = coordinator.get_incident(incident_id)
        if context and context.tenant_id == tenant["tenant_id"]:
            from hornet.coordinator import FSMState
            coordinator._transition_state(context, FSMState.CLOSED)
            context.add_timeline_event("manually_closed", details={"outcome": outcome})
            return {"status": "closed", "incident_id": str(incident_id), "outcome": outcome}
    
    raise HTTPException(status_code=404, detail="Incident not found")
