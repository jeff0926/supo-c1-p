from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Job
from app.schemas import ClipOut, JobOut

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _variant_to_out(variant):
    from app.schemas import VariantOut
    out = VariantOut.model_validate(variant)
    if variant.output_path:
        out.output_url = f"/api/variants/{variant.id}/download"
    return out


def _clip_to_out(clip) -> ClipOut:
    out = ClipOut.model_validate(clip)
    if clip.rendered and clip.output_path:
        out.output_url = f"/api/clips/{clip.id}/download"
    out.variants = [_variant_to_out(v) for v in clip.variants]
    return out


def _job_to_out(job: Job) -> JobOut:
    data = JobOut.model_validate(job)
    data.clips = [_clip_to_out(c) for c in job.clips]
    data.has_transcript = bool(job.transcript_path and Path(job.transcript_path).exists())
    return data


@router.get("", response_model=list[JobOut])
def list_jobs(db: Session = Depends(get_db)) -> list[JobOut]:
    jobs = db.query(Job).order_by(Job.created_at.desc()).all()
    return [_job_to_out(j) for j in jobs]


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: int, db: Session = Depends(get_db)) -> JobOut:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(404, "Job not found")
    return _job_to_out(job)


@router.get("/{job_id}/transcript")
def download_transcript(job_id: int, db: Session = Depends(get_db)) -> FileResponse:
    job = db.get(Job, job_id)
    if job is None or not job.transcript_path:
        raise HTTPException(404, "Transcript not found")
    path = Path(job.transcript_path)
    if not path.exists():
        raise HTTPException(404, "Transcript file missing on disk")
    return FileResponse(
        path,
        media_type="application/json",
        filename=f"transcript_job_{job_id}.json",
    )
