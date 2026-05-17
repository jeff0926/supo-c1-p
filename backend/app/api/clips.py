from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Clip
from app.schemas import ClipOut

router = APIRouter(prefix="/clips", tags=["clips"])


@router.get("/{clip_id}", response_model=ClipOut)
def get_clip(clip_id: int, db: Session = Depends(get_db)) -> ClipOut:
    clip = db.get(Clip, clip_id)
    if clip is None:
        raise HTTPException(404, "Clip not found")
    out = ClipOut.model_validate(clip)
    if clip.rendered and clip.output_path:
        out.output_url = f"/api/clips/{clip.id}/download"
    return out


@router.get("/{clip_id}/download")
def download_clip(clip_id: int, db: Session = Depends(get_db)) -> FileResponse:
    clip = db.get(Clip, clip_id)
    if clip is None or not clip.output_path:
        raise HTTPException(404, "Clip not found or not rendered")
    path = Path(clip.output_path)
    if not path.exists():
        raise HTTPException(404, "Rendered file missing on disk")
    return FileResponse(
        path,
        media_type="video/mp4",
        filename=f"{clip.title[:60].replace(' ', '_')}_{clip.id}.mp4",
    )
