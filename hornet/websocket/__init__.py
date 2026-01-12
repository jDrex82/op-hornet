"""HORNET WebSocket - Real-time incident updates with authentication."""
from typing import Dict, Set, Optional
from uuid import UUID
import json
import asyncio
import structlog
from fastapi import WebSocket, WebSocketDisconnect, Query
from hornet.middleware import api_key_auth

logger = structlog.get_logger()


class ConnectionManager:
    def __init__(self):
        self._connections: Dict[str, Set[WebSocket]] = {}  # tenant_id -> connections
        self._authenticated: Dict[WebSocket, dict] = {}  # websocket -> tenant info
    
    async def authenticate(self, websocket: WebSocket, api_key: str) -> Optional[dict]:
        """Authenticate WebSocket connection."""
        if not api_key:
            return None
        tenant = await api_key_auth.validate_key(api_key)
        if tenant:
            self._authenticated[websocket] = tenant
        return tenant
    
    async def connect(self, websocket: WebSocket, tenant_id: str):
        await websocket.accept()
        if tenant_id not in self._connections:
            self._connections[tenant_id] = set()
        self._connections[tenant_id].add(websocket)
        logger.info("websocket_connected", tenant_id=tenant_id, total=len(self._connections[tenant_id]))
    
    def disconnect(self, websocket: WebSocket, tenant_id: str):
        if tenant_id in self._connections:
            self._connections[tenant_id].discard(websocket)
        self._authenticated.pop(websocket, None)
        logger.info("websocket_disconnected", tenant_id=tenant_id)
    
    async def broadcast_to_tenant(self, tenant_id: str, message: dict):
        if tenant_id not in self._connections:
            return
        dead = set()
        for ws in self._connections[tenant_id]:
            try:
                await ws.send_json(message)
            except:
                dead.add(ws)
        for ws in dead:
            self._connections[tenant_id].discard(ws)
    
    async def send_incident_update(self, tenant_id: str, incident_id: UUID, event_type: str, data: dict = None):
        await self.broadcast_to_tenant(tenant_id, {
            "type": event_type,
            "incident_id": str(incident_id),
            "data": data or {},
            "timestamp": asyncio.get_event_loop().time(),
        })


ws_manager = ConnectionManager()


async def websocket_endpoint(websocket: WebSocket, tenant_id: str, api_key: str = Query(None)):
    """WebSocket endpoint with authentication."""
    # Authenticate
    tenant = await ws_manager.authenticate(websocket, api_key)
    if not tenant:
        await websocket.close(code=4001, reason="Authentication required")
        return
    
    # Verify tenant_id matches
    if tenant.get("tenant_id") != tenant_id:
        await websocket.close(code=4003, reason="Tenant mismatch")
        return
    
    await ws_manager.connect(websocket, tenant_id)
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            
            if msg.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
            elif msg.get("type") == "subscribe":
                await websocket.send_json({"type": "subscribed", "channel": msg.get("channel")})
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, tenant_id)
    except Exception as e:
        logger.error("websocket_error", error=str(e))
        ws_manager.disconnect(websocket, tenant_id)
