"""HORNET Health API Routes"""
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, Request
from hornet.config import get_settings

router = APIRouter()
settings = get_settings()

@router.get("")
async def health_check(request: Request) -> Dict[str, Any]:
    event_bus = request.app.state.event_bus
    redis_healthy = False
    try:
        await event_bus._redis.ping()
        redis_healthy = True
    except Exception:
        pass
    
    queue_depth = 0
    try:
        queue_depth = await event_bus.get_queue_depth()
    except Exception:
        pass
    
    return {
        "status": "healthy" if redis_healthy else "degraded",
        "version": settings.APP_VERSION,
        "timestamp": datetime.utcnow().isoformat(),
        "components": {"redis": "healthy" if redis_healthy else "unhealthy"},
        "metrics": {"queue_depth": queue_depth},
    }

@router.get("/agents")
async def agent_health(request: Request) -> Dict[str, Any]:
    registry = request.app.state.agent_registry
    agents = registry.get_all()
    return {
        "total_agents": len(agents),
        "agents": {name: {"status": "ready", "model": agent.model} for name, agent in agents.items()},
    }

@router.get("/ready")
async def readiness_check() -> Dict[str, Any]:
    return {"ready": True}

@router.get("/live")
async def liveness_check() -> Dict[str, Any]:
    return {"live": True}
