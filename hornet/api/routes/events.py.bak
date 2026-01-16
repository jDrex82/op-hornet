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


import re
from typing import List, Dict

def extract_entities_from_data(data: dict) -> List[Dict]:
    """Auto-extract entities (IPs, domains, hashes) from event data."""
    entities = []
    data_str = str(data).lower()
    
    # IP addresses (IPv4)
    ip_pattern = r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b'
    for ip in set(re.findall(ip_pattern, str(data))):
        if not ip.startswith(('0.', '127.', '255.')):  # Skip invalid/localhost
            entities.append({"type": "ip", "value": ip})
    
    # MD5 hashes
    md5_pattern = r'\b[a-fA-F0-9]{32}\b'
    for h in set(re.findall(md5_pattern, str(data))):
        entities.append({"type": "hash", "value": h, "hash_type": "md5"})
    
    # SHA256 hashes
    sha256_pattern = r'\b[a-fA-F0-9]{64}\b'
    for h in set(re.findall(sha256_pattern, str(data))):
        entities.append({"type": "hash", "value": h, "hash_type": "sha256"})
    
    # Domains (basic pattern)
    domain_pattern = r'\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+(?:com|net|org|io|edu|gov|co|info|biz|ru|cn|uk)\b'
    for d in set(re.findall(domain_pattern, str(data))):
        if d not in ('example.com', 'test.com'):
            entities.append({"type": "domain", "value": d})
    
    # Email addresses
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    for e in set(re.findall(email_pattern, str(data))):
        entities.append({"type": "email", "value": e})
    
    # Hostnames from common keys
    for key in ['hostname', 'host', 'computer_name', 'machine', 'device']:
        if key in data and isinstance(data[key], str):
            entities.append({"type": "hostname", "value": data[key]})
    
    # Users from common keys
    for key in ['user', 'username', 'user_id', 'account', 'actor']:
        if key in data and isinstance(data[key], str):
            entities.append({"type": "user", "value": data[key]})
    
    return entities

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
        "entities": [e.dict() for e in event.entities] or extract_entities_from_data(event.data),
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
            "entities": [e.dict() for e in event.entities] or extract_entities_from_data(event.data),
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
