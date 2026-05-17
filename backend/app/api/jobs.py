from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Job
from app.schemas import ClipOut, JobOut

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _clip_to_out(clip) -> ClipOut:
    out = ClipOut.model_validate(clip)
    if clip.rendered and clip.output_path:
        out.output_url = f"/api/clips/{clip.id}/download"
    return out


@router.get("", response_model=list[JobOut])
def list_jobs(db: Session = Depends(get_db)) -> list[JobOut]:
    jobs = db.query(Job).order_by(Job.created_at.desc()).all()
    result: list[JobOut] = []
    for job in jobs:
        data = JobOut.model_validate(job)
        data.clips = [_clip_to_out(c) for c in job.clips]
        result.append(data)
    return result


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: int, db: Session = Depends(get_db)) -> JobOut:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(404, "Job not found")
    data = JobOut.model_validate(job)
    data.clips = [_clip_to_out(c) for c in job.clips]
    return data
