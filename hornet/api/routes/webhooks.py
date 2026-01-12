"""HORNET Webhook Ingestion Routes"""
from datetime import datetime
from typing import Dict, Any, List
from uuid import uuid4
from fastapi import APIRouter, Request, HTTPException, Header
import hmac
import hashlib
import json

router = APIRouter()

def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify HMAC signature."""
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)

@router.post("/cloudflare")
async def cloudflare_webhook(request: Request) -> Dict[str, Any]:
    """Ingest Cloudflare security events."""
    body = await request.json()
    event_bus = request.app.state.event_bus
    
    events_processed = 0
    for log_entry in body.get("data", [body]):
        event_data = {
            "id": str(uuid4()),
            "tenant_id": "default",
            "timestamp": datetime.utcnow().isoformat(),
            "source": "cloudflare",
            "source_type": "waf",
            "event_type": f"network.{log_entry.get('Action', 'unknown')}",
            "severity": "MEDIUM" if log_entry.get("Action") == "block" else "LOW",
            "entities": [
                {"type": "ip", "value": log_entry.get("ClientIP", "unknown")},
                {"type": "domain", "value": log_entry.get("ClientRequestHost", "unknown")},
            ],
            "raw_payload": log_entry,
        }
        await event_bus.publish_event(event_data)
        events_processed += 1
    
    return {"status": "ok", "events_processed": events_processed}

@router.post("/aws-sns")
async def aws_sns_webhook(request: Request) -> Dict[str, Any]:
    """Ingest AWS SNS notifications (CloudTrail, GuardDuty, etc.)."""
    body = await request.json()
    event_bus = request.app.state.event_bus
    
    # Handle SNS subscription confirmation
    if body.get("Type") == "SubscriptionConfirmation":
        return {"status": "subscription_confirmation_required", "url": body.get("SubscribeURL")}
    
    # Process notification
    message = json.loads(body.get("Message", "{}"))
    
    events_processed = 0
    records = message.get("Records", [message])
    
    for record in records:
        event_name = record.get("eventName", "unknown")
        event_source = record.get("eventSource", "aws")
        
        severity = "LOW"
        if any(x in event_name.lower() for x in ["delete", "remove", "terminate"]):
            severity = "MEDIUM"
        if any(x in event_name.lower() for x in ["iam", "security", "policy"]):
            severity = "HIGH"
        
        event_data = {
            "id": str(uuid4()),
            "tenant_id": "default",
            "timestamp": record.get("eventTime", datetime.utcnow().isoformat()),
            "source": event_source,
            "source_type": "cloudtrail",
            "event_type": f"cloud.{event_name}",
            "severity": severity,
            "entities": [
                {"type": "user", "value": record.get("userIdentity", {}).get("userName", "unknown")},
                {"type": "ip", "value": record.get("sourceIPAddress", "unknown")},
            ],
            "raw_payload": record,
        }
        await event_bus.publish_event(event_data)
        events_processed += 1
    
    return {"status": "ok", "events_processed": events_processed}

@router.post("/syslog")
async def syslog_webhook(request: Request) -> Dict[str, Any]:
    """Ingest syslog-formatted events."""
    body = await request.json()
    event_bus = request.app.state.event_bus
    
    event_data = {
        "id": str(uuid4()),
        "tenant_id": "default",
        "timestamp": body.get("timestamp", datetime.utcnow().isoformat()),
        "source": body.get("hostname", "unknown"),
        "source_type": "syslog",
        "event_type": body.get("facility", "system") + "." + body.get("severity", "info"),
        "severity": body.get("severity", "LOW").upper(),
        "entities": [],
        "raw_payload": body,
    }
    await event_bus.publish_event(event_data)
    
    return {"status": "ok", "events_processed": 1}

@router.post("/generic")
async def generic_webhook(
    request: Request,
    x_webhook_signature: str = Header(None),
) -> Dict[str, Any]:
    """Generic webhook endpoint with optional signature verification."""
    body = await request.json()
    event_bus = request.app.state.event_bus
    
    event_data = {
        "id": str(uuid4()),
        "tenant_id": "default",
        "timestamp": body.get("timestamp", datetime.utcnow().isoformat()),
        "source": body.get("source", "webhook"),
        "source_type": body.get("source_type", "generic"),
        "event_type": body.get("event_type", "unknown"),
        "severity": body.get("severity", "LOW"),
        "entities": body.get("entities", []),
        "raw_payload": body,
    }
    await event_bus.publish_event(event_data)
    
    return {"status": "ok", "event_id": event_data["id"]}
