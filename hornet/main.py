"""HORNET - Autonomous SOC Swarm Main Application"""
from contextlib import asynccontextmanager
from typing import AsyncIterator
import structlog

from pydantic import BaseModel
from fastapi import FastAPI, Request, WebSocket, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from hornet.config import get_settings
from hornet.api.routes import events, incidents, health, config, webhooks, dashboard, campaigns, reports
from hornet.event_bus import EventBus
from hornet.coordinator import Coordinator, AgentRegistry
from hornet.websocket import websocket_endpoint, ws_manager
from hornet.edge_gateway import edge_websocket_endpoint, edge_gateway
from hornet.metrics import metrics_endpoint
from hornet.middleware import (
    RateLimitMiddleware,
    RequestLoggingMiddleware,
    get_current_tenant,
    get_optional_tenant,
)
from hornet.observability import init_observability, instrument_app

logger = structlog.get_logger()
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Initialize observability
    init_observability(
        service_name="hornet",
        environment=settings.ENVIRONMENT,
        log_level=settings.LOG_LEVEL,
    )

    logger.info("hornet_starting", version=settings.APP_VERSION)

    # Initialize event bus
    app.state.event_bus = EventBus()
    await app.state.event_bus.connect()

    # Initialize agent registry with all agents
    app.state.agent_registry = AgentRegistry.create_default()
    logger.info("agents_registered", count=len(app.state.agent_registry.get_all()))

    # Initialize coordinator
    app.state.coordinator = Coordinator(
        event_bus=app.state.event_bus,
        agent_registry=app.state.agent_registry,
    )

    # 🐝 Start Event Dispatcher - connects events to agent swarm
    from hornet.dispatcher import start_dispatcher
    app.state.dispatcher = await start_dispatcher(
        event_bus=app.state.event_bus,
        coordinator=app.state.coordinator,
    )
    logger.info("dispatcher_started", stats=app.state.dispatcher.stats)

    # Start retry queue processor
    from hornet.retry_queue import retry_queue
    import asyncio
    retry_task = asyncio.create_task(retry_queue.start_processor(interval_seconds=30))

    logger.info("hornet_ready", agents=len(app.state.agent_registry.get_all()))

    yield

    logger.info("hornet_shutting_down")
    
    # Stop dispatcher
    if hasattr(app.state, 'dispatcher'):
        await app.state.dispatcher.stop()
    
    retry_queue.stop_processor()
    await app.state.event_bus.disconnect()


app = FastAPI(
    title="HORNET",
    description="Autonomous SOC Swarm - 56-Agent Security Operations Center",
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# Middleware (order matters - last added is first executed)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Instrument with OpenTelemetry
instrument_app(app)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("unhandled_exception", path=request.url.path, error=str(exc), exc_info=True)
    return JSONResponse(status_code=500, content={"error": "internal_server_error", "request_id": getattr(request.state, "request_id", None)})


# API routes
app.include_router(health.router, prefix="/api/v1/health", tags=["Health"])
app.include_router(events.router, prefix="/api/v1/events", tags=["Events"])
app.include_router(incidents.router, prefix="/api/v1/incidents", tags=["Incidents"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["Reports"])
app.include_router(campaigns.router, prefix="/api/v1/campaigns", tags=["Campaigns"])
app.include_router(config.router, prefix="/api/v1/config", tags=["Configuration"])
app.include_router(webhooks.router, prefix="/api/v1/webhooks", tags=["Webhooks"])

# Dashboard
app.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])


# WebSocket endpoint
@app.websocket("/api/v1/ws/{tenant_id}")
async def websocket_route(websocket: WebSocket, tenant_id: str, api_key: str = None):
    # Get api_key from query params if not passed
    if not api_key:
        api_key = websocket.query_params.get("api_key")
    await websocket_endpoint(websocket, tenant_id, api_key)


# Edge Agent WebSocket endpoint
@app.websocket("/api/v1/edge/connect")
async def edge_websocket_route(websocket: WebSocket, api_key: str = Query(None)):
    await edge_websocket_endpoint(websocket, api_key, event_bus=app.state.event_bus)


# Edge Gateway status endpoint
@app.get("/api/v1/edge/status")
async def edge_status(tenant: dict = Depends(get_current_tenant)):
    agents = edge_gateway.get_agents_for_tenant(tenant["tenant_id"])
    return {
        "connected_agents": len(agents),
        "agents": [{
            "agent_id": a.agent_id, "hostname": a.hostname, "version": a.version,
            "connected_at": a.connected_at.isoformat(),
            "last_heartbeat": a.last_heartbeat.isoformat(), "capabilities": a.capabilities,
        } for a in agents],
    }


# Send action to Edge Agents
class EdgeActionRequest(BaseModel):
    incident_id: str
    action_type: str
    target: str
    parameters: dict = {}


@app.post("/api/v1/edge/action")
async def send_edge_action(
    action_req: EdgeActionRequest,
    tenant: dict = Depends(get_current_tenant),
):
    """Send a signed action to all Edge Agents for this tenant."""
    action = edge_gateway.create_signed_action(
        tenant_id=tenant["tenant_id"],
        incident_id=action_req.incident_id,
        action_type=action_req.action_type,
        target=action_req.target,
        parameters=action_req.parameters,
    )
    sent = await edge_gateway.broadcast_action_to_tenant(tenant["tenant_id"], action)
    return {
        "action_id": action.action_id,
        "sent_to_agents": sent,
        "expires_at": action.expires_at,
    }


# 🐝 Dispatcher status endpoint
@app.get("/api/v1/dispatcher/status")
async def dispatcher_status():
    """Get Event Dispatcher statistics."""
    if hasattr(app.state, 'dispatcher'):
        stats = app.state.dispatcher.stats
        # Add queue depth from event bus
        try:
            stats["queue_depth"] = await app.state.event_bus.get_queue_depth()
            stats["pending_acks"] = await app.state.event_bus.get_pending_count()
        except Exception:
            pass
        return stats
    return {"error": "dispatcher_not_initialized"}


@app.get("/metrics")
async def get_metrics():
    content, content_type = await metrics_endpoint()
    return JSONResponse(content=content.decode(), media_type=content_type)


# Root endpoint
@app.get("/")
async def root():
    return {
        "name": "HORNET",
        "version": settings.APP_VERSION,
        "status": "operational",
        "dashboard": "/dashboard",
        "docs": "/docs",
        "health": "/api/v1/health",
        "dispatcher": "/api/v1/dispatcher/status",
    }


# DLQ management endpoints
@app.get("/api/v1/dlq")
async def get_dlq(tenant: dict = Depends(get_current_tenant)):
    from hornet.retry_queue import retry_queue
    items = await retry_queue.get_dlq_items(tenant["tenant_id"])
    return {"items": [{"id": str(i.id), "type": i.item_type, "target": i.target, "attempts": i.attempt_count, "errors": i.error_history} for i in items]}


@app.post("/api/v1/dlq/{item_id}/replay")
async def replay_dlq_item(item_id: str, tenant: dict = Depends(get_current_tenant)):
    from hornet.retry_queue import retry_queue
    success = await retry_queue.replay_dlq_item(item_id)
    return {"success": success}
