"""HORNET Events API"""
from typing import Optional, List
from uuid import UUID, uuid4
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Request, Query
from pydantic import BaseModel, Field

from hornet.middleware import get_current_tenant, get_optional_tenant

router = APIRouter()


class EntityModel(BaseModel):
    type: str
    value: str


class EventCreate(BaseModel):
    event_type: str = Field(..., description="Event type identifier")
    source: str = Field(..., description="Source system")
    source_type: str = Field(..., description="Type of source")
    severity: str = Field(..., description="LOW|MEDIUM|HIGH|CRITICAL")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    entities: List[EntityModel] = Field(default_factory=list)
    raw_payload: dict = Field(default_factory=dict)


class EventResponse(BaseModel):
    id: UUID
    event_type: str
    source: str
    severity: str
    timestamp: datetime
    incident_id: Optional[UUID] = None


@router.post("", response_model=EventResponse, status_code=201)
async def ingest_event(
    request: Request,
    event: EventCreate,
    tenant: dict = Depends(get_current_tenant),
):
    """Ingest a security event for processing."""
    event_id = uuid4()
    
    # Get coordinator from app state
    coordinator = getattr(request.app.state, "coordinator", None)
    
    # Create event dict
    event_dict = {
        "id": str(event_id),
        "event_type": event.event_type,
        "source": event.source,
        "source_type": event.source_type,
        "severity": event.severity,
        "timestamp": event.timestamp.isoformat(),
        "entities": [e.dict() for e in event.entities],
        "raw_payload": event.raw_payload,
        "tenant_id": tenant["tenant_id"],
    }
    
    # Process through coordinator
    incident_id = None
    if coordinator:
        context = coordinator._create_context(event_dict, tenant["tenant_id"])
        incident_id = context.incident_id
        # Would trigger async processing here
    
    return EventResponse(
        id=event_id,
        event_type=event.event_type,
        source=event.source,
        severity=event.severity,
        timestamp=event.timestamp,
        incident_id=incident_id,
    )


@router.post("/batch", status_code=202)
async def ingest_batch(
    request: Request,
    events: List[EventCreate],
    tenant: dict = Depends(get_current_tenant),
):
    """Ingest a batch of events."""
    if len(events) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 events per batch")
    
    results = []
    for event in events:
        event_id = uuid4()
        results.append({"id": str(event_id), "event_type": event.event_type})
    
    return {"accepted": len(results), "events": results}


@router.get("")
async def list_events(
    request: Request,
    tenant: dict = Depends(get_current_tenant),
    event_type: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
    offset: int = Query(0),
):
    """List events for tenant."""
    # Would query database
    return {
        "data": [],
        "meta": {
            "total": 0,
            "limit": limit,
            "offset": offset,
        }
    }


@router.get("/{event_id}")
async def get_event(
    event_id: UUID,
    tenant: dict = Depends(get_current_tenant),
):
    """Get a specific event."""
    raise HTTPException(status_code=404, detail="Event not found")
