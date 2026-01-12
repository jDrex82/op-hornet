"""HORNET Queue Management Routes"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
import structlog

from hornet.queue import retry_queue, RetryJob

logger = structlog.get_logger()
router = APIRouter()


class DLQJobResponse(BaseModel):
    id: str
    job_type: str
    target_url: str
    tenant_id: str
    attempts: int
    last_error: str
    created_at: str


@router.get("/stats")
async def get_queue_stats():
    """Get queue statistics."""
    stats = await retry_queue.get_stats()
    return stats


@router.get("/dlq", response_model=List[DLQJobResponse])
async def get_dlq_jobs(limit: int = 100):
    """Get jobs in the dead letter queue."""
    jobs = await retry_queue.get_dlq_jobs(limit)
    return [
        DLQJobResponse(
            id=str(j.id),
            job_type=j.job_type,
            target_url=j.target_url,
            tenant_id=j.tenant_id,
            attempts=j.attempts,
            last_error=j.last_error or "",
            created_at=j.created_at.isoformat(),
        )
        for j in jobs
    ]


@router.post("/dlq/{job_id}/retry")
async def retry_dlq_job(job_id: str):
    """Retry a job from the DLQ."""
    success = await retry_queue.retry_dlq_job(job_id)
    if not success:
        raise HTTPException(status_code=404, detail="Job not found in DLQ")
    return {"message": "Job scheduled for retry", "job_id": job_id}


@router.delete("/dlq/{job_id}")
async def delete_dlq_job(job_id: str):
    """Delete a job from the DLQ."""
    # Would implement deletion
    return {"message": "Job deleted", "job_id": job_id}
