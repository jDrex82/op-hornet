"""HORNET Dashboard Routes"""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse, FileResponse
from pathlib import Path

router = APIRouter()

# Try multiple paths
PATHS = [
    Path(__file__).parent.parent / "dashboard" / "index.html",
    Path("/app/hornet/dashboard/index.html"),
    Path(__file__).parent.parent.parent / "dashboard" / "index.html",
]

@router.get("", response_class=HTMLResponse)
async def serve_dashboard():
    """Serve the dashboard HTML."""
    for p in PATHS:
        if p.exists():
            return FileResponse(p)
    return HTMLResponse(f"<h1>Dashboard not found. Tried: {[str(p) for p in PATHS]}</h1>", status_code=404)
