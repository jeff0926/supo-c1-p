from __future__ import annotations

import logging
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Job, JobStatus, Video
from app.schemas import JobOut, VideoOut
from app.services.ingestion import probe_duration
from app.workers.tasks import process_video

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/videos", tags=["videos"])

ALLOWED_SUFFIXES = {".mp4", ".mov", ".mkv", ".webm", ".m4v"}


@router.post("", response_model=JobOut, status_code=201)
async def upload_video(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> JobOut:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(400, f"Unsupported file type: {suffix}")

    upload_id = uuid.uuid4().hex[:12]
    dest_dir = settings.media_path / "uploads"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / f"{upload_id}{suffix}"

    try:
        with dest_path.open("wb") as out:
            shutil.copyfileobj(file.file, out)
    except Exception as exc:
        logger.exception("Failed to persist upload")
        raise HTTPException(500, f"Failed to save upload: {exc}") from exc
    finally:
        await file.close()

    try:
        duration = probe_duration(dest_path)
    except Exception:
        logger.warning("ffprobe failed for %s; continuing without duration", dest_path)
        duration = None

    video = Video(
        filename=file.filename or dest_path.name,
        source_path=str(dest_path),
        duration_seconds=duration,
    )
    db.add(video)
    db.flush()

    job = Job(video_id=video.id, status=JobStatus.PENDING)
    db.add(job)
    db.commit()
    db.refresh(job)

    process_video.delay(job.id)
    return JobOut.model_validate(job)


@router.get("", response_model=list[VideoOut])
def list_videos(db: Session = Depends(get_db)) -> list[VideoOut]:
    videos = db.query(Video).order_by(Video.created_at.desc()).all()
    return [VideoOut.model_validate(v) for v in videos]
