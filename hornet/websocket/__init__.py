"""HORNET WebSocket - Real-time incident updates with Redis pub/sub."""
from typing import Dict, Set, Optional
from uuid import UUID
import json
import asyncio
import structlog
from fastapi import WebSocket, WebSocketDisconnect, Query
from hornet.middleware import api_key_auth
from hornet.config import get_settings
import redis.asyncio as redis

logger = structlog.get_logger()
settings = get_settings()


class ConnectionManager:
    def __init__(self):
        self._connections: Dict[str, Set[WebSocket]] = {}  # tenant_id -> connections
        self._authenticated: Dict[WebSocket, dict] = {}  # websocket -> tenant info
        self._redis: Optional[redis.Redis] = None
        self._pubsub_task: Optional[asyncio.Task] = None

    async def start_pubsub_listener(self):
        """Start listening to Redis pub/sub for real-time updates."""
        if self._pubsub_task is not None:
            return
            
        self._redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
        self._pubsub_task = asyncio.create_task(self._listen_pubsub())
        logger.info("websocket_pubsub_started")

    async def _listen_pubsub(self):
        """Listen to Redis pub/sub and broadcast to all connected clients."""
        pubsub = self._redis.pubsub()
        await pubsub.subscribe("hornet:realtime")
        
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        # Broadcast to all tenants (in production, filter by tenant)
                        await self.broadcast_all(data)
                    except Exception as e:
                        logger.error("pubsub_broadcast_error", error=str(e))
        except asyncio.CancelledError:
            await pubsub.unsubscribe("hornet:realtime")
            raise
        except Exception as e:
            logger.error("pubsub_listener_error", error=str(e))
            # Restart listener after delay
            await asyncio.sleep(5)
            self._pubsub_task = asyncio.create_task(self._listen_pubsub())

    async def broadcast_all(self, message: dict):
        """Broadcast message to all connected WebSocket clients."""
        dead = []
        for tenant_id, connections in self._connections.items():
            for ws in connections:
                try:
                    await ws.send_json(message)
                except Exception:
                    dead.append((tenant_id, ws))
        
        for tenant_id, ws in dead:
            self._connections.get(tenant_id, set()).discard(ws)
            self._authenticated.pop(ws, None)

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
        
        # Start pub/sub listener if not running
        await self.start_pubsub_listener()
        
        logger.info("websocket_connected", tenant_id=tenant_id, total=len(self._connections[tenant_id]))
        
        # Send initial connection confirmation
        await websocket.send_json({"type": "connected", "tenant_id": tenant_id})

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
        })


ws_manager = ConnectionManager()


async def websocket_endpoint(websocket: WebSocket, tenant_id: str, api_key: str = Query(None)):
    """WebSocket endpoint with authentication."""
    # Authenticate
    tenant = await ws_manager.authenticate(websocket, api_key)
    if not tenant:
        await websocket.close(code=4001, reason="Authentication required")
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