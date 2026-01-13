"""HORNET Events API"""
from typing import Optional, List
from uuid import UUID, uuid4
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Request, Query
from pydantic import BaseModel, Field
from hornet.middleware import get_current_tenant, get_optional_tenant
from hornet.event_bus import EventBus

router = APIRouter()

# Shared event bus instance
_event_bus: Optional[EventBus] = None

async def get_event_bus() -> EventBus:
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
        await _event_bus.connect()
    return _event_bus

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
    data: dict = Field(default_factory=dict)

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
    incident_id = uuid4()
    
    # Create event dict
    event_dict = {
        "id": str(event_id),
        "event_type": event.event_type,
        "source": event.source,
        "source_type": event.source_type,
        "severity": event.severity,
        "timestamp": event.timestamp.isoformat(),
        "entities": [e.dict() for e in event.entities],
        "data": event.data,
        "tenant_id": tenant["tenant_id"],
        "incident_id": str(incident_id),
    }
    
    # Push to event queue for workers
    event_bus = await get_event_bus()
    await event_bus.publish_event(event_dict)
    
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
    
    event_bus = await get_event_bus()
    results = []
    
    for event in events:
        event_id = uuid4()
        incident_id = uuid4()
        event_dict = {
            "id": str(event_id),
            "event_type": event.event_type,
            "source": event.source,
            "source_type": event.source_type,
            "severity": event.severity,
            "timestamp": event.timestamp.isoformat(),
            "entities": [e.dict() for e in event.entities],
            "data": event.data,
            "tenant_id": tenant["tenant_id"],
            "incident_id": str(incident_id),
        }
        await event_bus.publish_event(event_dict)
        results.append({"id": str(event_id), "incident_id": str(incident_id)})
    
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
    return {"data": [], "meta": {"total": 0, "limit": limit, "offset": offset}}

@router.get("/{event_id}")
async def get_event(event_id: UUID, tenant: dict = Depends(get_current_tenant)):
    """Get a specific event."""
    raise HTTPException(status_code=404, detail="Event not found")
