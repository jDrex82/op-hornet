"""
HORNET Edge Gateway
Handles connections from Edge Agents deployed in customer networks.
"""
import asyncio
import json
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from typing import Dict, Set, Optional, Any
from dataclasses import dataclass, field, asdict
from uuid import uuid4
import structlog
from fastapi import WebSocket, WebSocketDisconnect, Query

from hornet.config import get_settings
from hornet.middleware import api_key_auth

logger = structlog.get_logger()
settings = get_settings()


@dataclass
class EdgeAgent:
    """Represents a connected Edge Agent."""
    agent_id: str
    tenant_id: str
    websocket: WebSocket
    connected_at: datetime
    last_heartbeat: datetime
    hostname: str = "unknown"
    version: str = "unknown"
    capabilities: list = field(default_factory=list)


@dataclass
class SignedAction:
    """Action to be executed by Edge Agent."""
    action_id: str
    tenant_id: str
    incident_id: str
    action_type: str
    target: str
    parameters: Dict[str, Any]
    expires_at: str
    nonce: str
    signature: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    def sign(self, secret: str) -> str:
        """Sign the action with HMAC-SHA256."""
        payload = json.dumps({
            "action_id": self.action_id,
            "tenant_id": self.tenant_id,
            "incident_id": self.incident_id,
            "action_type": self.action_type,
            "target": self.target,
            "parameters": self.parameters,
            "expires_at": self.expires_at,
            "nonce": self.nonce,
        }, sort_keys=True)
        self.signature = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
        return self.signature


class EdgeGateway:
    """Manages Edge Agent connections."""

    def __init__(self):
        self._agents: Dict[str, EdgeAgent] = {}
        self._tenant_agents: Dict[str, Set[str]] = {}
        self._action_secret = settings.SECRET_KEY or "hornet-edge-secret-change-me"
        self._pending_actions: Dict[str, SignedAction] = {}
        self._nonce_cache: Set[str] = set()

    @property
    def connected_count(self) -> int:
        return len(self._agents)

    def get_agents_for_tenant(self, tenant_id: str) -> list:
        agent_ids = self._tenant_agents.get(tenant_id, set())
        return [self._agents[aid] for aid in agent_ids if aid in self._agents]

    async def authenticate(self, api_key: str) -> Optional[dict]:
        if not api_key:
            return None
        return await api_key_auth.validate_key(api_key)

    async def register_agent(self, websocket: WebSocket, tenant_id: str,
                            hostname: str = "unknown", version: str = "unknown",
                            capabilities: list = None) -> EdgeAgent:
        agent_id = f"edge_{uuid4().hex[:12]}"
        now = datetime.utcnow()

        agent = EdgeAgent(
            agent_id=agent_id, tenant_id=tenant_id, websocket=websocket,
            connected_at=now, last_heartbeat=now, hostname=hostname,
            version=version, capabilities=capabilities or [],
        )

        self._agents[agent_id] = agent
        if tenant_id not in self._tenant_agents:
            self._tenant_agents[tenant_id] = set()
        self._tenant_agents[tenant_id].add(agent_id)

        logger.info("edge_agent_registered", agent_id=agent_id, tenant_id=tenant_id,
                   hostname=hostname, total_agents=self.connected_count)
        return agent

    def unregister_agent(self, agent_id: str):
        if agent_id not in self._agents:
            return
        agent = self._agents.pop(agent_id)
        if agent.tenant_id in self._tenant_agents:
            self._tenant_agents[agent.tenant_id].discard(agent_id)
        logger.info("edge_agent_unregistered", agent_id=agent_id, tenant_id=agent.tenant_id)

    def update_heartbeat(self, agent_id: str):
        if agent_id in self._agents:
            self._agents[agent_id].last_heartbeat = datetime.utcnow()

    async def handle_log_batch(self, agent_id: str, batch: dict, event_bus=None) -> dict:
        agent = self._agents.get(agent_id)
        if not agent:
            return {"error": "unknown_agent"}

        events = batch.get("events", [])
        batch_id = batch.get("batch_id", str(uuid4()))

        logger.info("edge_log_batch_received", agent_id=agent_id,
                   tenant_id=agent.tenant_id, batch_id=batch_id, event_count=len(events))

        # Publish each event to the event bus for processing by the swarm
        published = 0
        for event in events:
            try:
                from uuid import uuid4 as make_uuid
                event_id = str(make_uuid())
                incident_id = str(make_uuid())
                
                event_dict = {
                    "id": event_id,
                    "event_type": event.get("event_type", "unknown"),
                    "source": event.get("source", agent.hostname),
                    "source_type": event.get("source_type", "edge_agent"),
                    "severity": event.get("severity", "LOW"),
                    "timestamp": event.get("timestamp", datetime.utcnow().isoformat()),
                    "entities": event.get("entities", []),
                    "data": event.get("raw", event),
                    "tenant_id": agent.tenant_id,
                    "incident_id": incident_id,
                    "edge_agent_id": agent_id,
                }
                
                if event_bus:
                    await event_bus.publish_event(event_dict)
                    published += 1
                    logger.debug("edge_event_published", event_id=event_id, 
                               event_type=event_dict["event_type"])
            except Exception as e:
                logger.error("edge_event_publish_failed", error=str(e))

        return {"type": "batch_ack", "batch_id": batch_id,
                "accepted": len(events), "timestamp": datetime.utcnow().isoformat()}

    def create_signed_action(self, tenant_id: str, incident_id: str, action_type: str,
                            target: str, parameters: dict, ttl_seconds: int = 60) -> SignedAction:
        action = SignedAction(
            action_id=str(uuid4()), tenant_id=tenant_id, incident_id=incident_id,
            action_type=action_type, target=target, parameters=parameters,
            expires_at=(datetime.utcnow() + timedelta(seconds=ttl_seconds)).isoformat(),
            nonce=secrets.token_hex(16),
        )
        action.sign(self._action_secret)
        self._pending_actions[action.action_id] = action
        logger.info("edge_action_created", action_id=action.action_id,
                   tenant_id=tenant_id, action_type=action_type, target=target)
        return action

    async def send_action_to_agent(self, agent_id: str, action: SignedAction) -> bool:
        agent = self._agents.get(agent_id)
        if not agent:
            return False
        try:
            await agent.websocket.send_json({"type": "action_request", "action": action.to_dict()})
            logger.info("edge_action_sent", agent_id=agent_id, action_id=action.action_id)
            return True
        except Exception as e:
            logger.error("edge_action_send_error", agent_id=agent_id, error=str(e))
            return False

    async def broadcast_action_to_tenant(self, tenant_id: str, action: SignedAction) -> int:
        agents = self.get_agents_for_tenant(tenant_id)
        sent = 0
        for agent in agents:
            if await self.send_action_to_agent(agent.agent_id, action):
                sent += 1
        return sent

    def handle_action_result(self, agent_id: str, result: dict) -> dict:
        action_id = result.get("action_id")
        success = result.get("success", False)
        logger.info("edge_action_result", agent_id=agent_id,
                   action_id=action_id, success=success, message=result.get("message", ""))
        self._pending_actions.pop(action_id, None)
        return {"type": "action_result_ack", "action_id": action_id}


edge_gateway = EdgeGateway()


async def edge_websocket_endpoint(websocket: WebSocket, api_key: str = Query(None), event_bus=None):
    """WebSocket endpoint for Edge Agent connections."""
    tenant = await edge_gateway.authenticate(api_key)
    if not tenant:
        await websocket.close(code=4001, reason="Authentication required")
        logger.warning("edge_auth_failed", reason="invalid_api_key")
        return

    tenant_id = tenant["tenant_id"]
    await websocket.accept()
    agent = None

    try:
        data = await asyncio.wait_for(websocket.receive_json(), timeout=10.0)

        if data.get("type") != "register":
            await websocket.close(code=4002, reason="Expected register message")
            return

        agent = await edge_gateway.register_agent(
            websocket=websocket, tenant_id=tenant_id,
            hostname=data.get("hostname", "unknown"),
            version=data.get("version", "unknown"),
            capabilities=data.get("capabilities", []),
        )

        await websocket.send_json({
            "type": "registered", "agent_id": agent.agent_id,
            "tenant_id": tenant_id, "server_time": datetime.utcnow().isoformat(),
        })

        while True:
            msg = await websocket.receive_json()
            msg_type = msg.get("type")

            if msg_type == "heartbeat":
                edge_gateway.update_heartbeat(agent.agent_id)
                await websocket.send_json({"type": "heartbeat_ack", "server_time": datetime.utcnow().isoformat()})
            elif msg_type == "log_batch":
                ack = await edge_gateway.handle_log_batch(agent.agent_id, msg, event_bus)
                await websocket.send_json(ack)
            elif msg_type == "action_result":
                ack = edge_gateway.handle_action_result(agent.agent_id, msg)
                await websocket.send_json(ack)
            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})
            else:
                logger.warning("edge_unknown_message", agent_id=agent.agent_id, msg_type=msg_type)

    except asyncio.TimeoutError:
        logger.warning("edge_registration_timeout")
        await websocket.close(code=4003, reason="Registration timeout")
    except WebSocketDisconnect:
        logger.info("edge_agent_disconnected", agent_id=agent.agent_id if agent else "unknown")
    except Exception as e:
        logger.error("edge_websocket_error", error=str(e))
    finally:
        if agent:
            edge_gateway.unregister_agent(agent.agent_id)
