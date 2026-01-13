"""HORNET Dashboard Routes"""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse, FileResponse
from pathlib import Path

router = APIRouter()

# Dashboard HTML paths
DASHBOARD_PATHS = [
    Path(__file__).parent.parent.parent / "dashboard" / "index.html",
    Path("/app/hornet/dashboard/index.html"),
]

# Static files paths
STATIC_PATHS = [
    Path(__file__).parent.parent.parent / "dashboard" / "static",
    Path("/app/hornet/dashboard/static"),
]

@router.get("", response_class=HTMLResponse)
async def serve_dashboard():
    """Serve the dashboard HTML."""
    for p in DASHBOARD_PATHS:
        if p.exists():
            return FileResponse(p)
    return HTMLResponse(f"<h1>Dashboard not found</h1>", status_code=404)

@router.get("/static/{filename}")
async def serve_static(filename: str):
    """Serve static files (logo, etc.)."""
    for static_dir in STATIC_PATHS:
        file_path = static_dir / filename
        if file_path.exists():
            return FileResponse(file_path)
    return HTMLResponse(f"<h1>File not found: {filename}</h1>", status_code=404)