"""HORNET Configuration API"""
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field

from hornet.middleware import get_current_tenant
from hornet.config import get_settings
from hornet.playbooks import PLAYBOOKS

router = APIRouter()
settings = get_settings()


class ThresholdUpdate(BaseModel):
    DISMISS: Optional[float] = Field(None, ge=0.0, le=1.0)
    INVESTIGATE: Optional[float] = Field(None, ge=0.0, le=1.0)
    CONFIRM: Optional[float] = Field(None, ge=0.0, le=1.0)


@router.get("/thresholds")
async def get_thresholds(tenant: dict = Depends(get_current_tenant)):
    """Get detection thresholds."""
    return {
        "DISMISS": settings.THRESHOLD_DISMISS,
        "INVESTIGATE": settings.THRESHOLD_INVESTIGATE,
        "CONFIRM": settings.THRESHOLD_CONFIRM,
    }


@router.put("/thresholds")
async def update_thresholds(
    thresholds: ThresholdUpdate,
    tenant: dict = Depends(get_current_tenant),
):
    """Update detection thresholds (per-tenant in production)."""
    # Would persist to database per tenant
    updated = {}
    if thresholds.DISMISS is not None:
        updated["DISMISS"] = thresholds.DISMISS
    if thresholds.INVESTIGATE is not None:
        updated["INVESTIGATE"] = thresholds.INVESTIGATE
    if thresholds.CONFIRM is not None:
        updated["CONFIRM"] = thresholds.CONFIRM
    
    return {"status": "updated", "thresholds": updated}


@router.get("/agents")
async def get_agents(request: Request, tenant: dict = Depends(get_current_tenant)):
    """Get available agents and their status."""
    registry = getattr(request.app.state, "agent_registry", None)
    
    if registry:
        agents = registry.get_all()
        return {
            "total": len(agents),
            "agents": [
                {
                    "name": name,
                    "type": type(agent).__name__,
                    "enabled": True,
                }
                for name, agent in agents.items()
            ]
        }
    
    return {"total": 0, "agents": []}


@router.get("/playbooks")
async def get_playbooks(tenant: dict = Depends(get_current_tenant)):
    """Get available playbooks."""
    return {
        "total": len(PLAYBOOKS),
        "playbooks": [
            {
                "id": pb.id,
                "name": pb.name,
                "description": pb.description,
                "triggers": pb.triggers,
                "priority": pb.priority.value,
                "auto_approve_all": pb.auto_approve_all,
                "requires_oversight": pb.requires_oversight,
                "steps_count": len(pb.steps),
            }
            for pb in PLAYBOOKS.values()
        ]
    }


@router.get("/playbooks/{playbook_id}")
async def get_playbook(playbook_id: str, tenant: dict = Depends(get_current_tenant)):
    """Get a specific playbook."""
    pb = PLAYBOOKS.get(playbook_id)
    if not pb:
        raise HTTPException(status_code=404, detail="Playbook not found")
    
    return {
        "id": pb.id,
        "name": pb.name,
        "description": pb.description,
        "triggers": pb.triggers,
        "priority": pb.priority.value,
        "auto_approve_all": pb.auto_approve_all,
        "requires_oversight": pb.requires_oversight,
        "steps": [
            {
                "order": s.order,
                "action_type": s.action_type,
                "target": s.target,
                "params": s.params,
                "auto_approve": s.auto_approve,
            }
            for s in pb.steps
        ],
    }


@router.get("/integrations")
async def get_integrations(tenant: dict = Depends(get_current_tenant)):
    """Get configured integrations."""
    from hornet.integrations.log_sources import CONNECTORS as LOG_CONNECTORS
    from hornet.integrations.action_connectors import CONNECTORS as ACTION_CONNECTORS
    
    return {
        "log_sources": list(LOG_CONNECTORS.keys()),
        "action_connectors": list(ACTION_CONNECTORS.keys()),
    }


@router.get("/tuner/summary")
async def get_tuner_summary(tenant: dict = Depends(get_current_tenant)):
    """Get tuner feedback summary."""
    from hornet.tuner import tuner
    return tuner.get_summary()
