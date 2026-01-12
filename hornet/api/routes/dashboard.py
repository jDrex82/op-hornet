"""HORNET Dashboard Routes"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, FileResponse
from pathlib import Path

router = APIRouter()

DASHBOARD_PATH = Path(__file__).parent.parent.parent / "dashboard" / "index.html"

@router.get("", response_class=HTMLResponse)
async def serve_dashboard():
    """Serve the dashboard HTML."""
    if DASHBOARD_PATH.exists():
        return FileResponse(DASHBOARD_PATH)
    return HTMLResponse("<h1>Dashboard not found</h1>", status_code=404)
