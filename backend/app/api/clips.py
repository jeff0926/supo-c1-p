from __future__ import annotations

import json
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Clip, Variant, VariantStatus
from app.schemas import (
    BatchRenderRequest,
    BatchRenderResponse,
    ClipOut,
    ClipTrimRequest,
    TemplateInfo,
    VariantOut,
    WordTimestamp,
)
from app.services.publishing import TemplateEngine
from app.workers.tasks import render_variants_task, rerender_clip_task

router = APIRouter(tags=["clips"])

clips_router = APIRouter(prefix="/clips")
templates_router = APIRouter(prefix="/templates")
variants_router = APIRouter(prefix="/variants")


def _variant_to_out(variant: Variant) -> VariantOut:
    out = VariantOut.model_validate(variant)
    if variant.output_path:
        out.output_url = f"/api/variants/{variant.id}/download"
    return out


def _hydrate_clip(clip: Clip) -> ClipOut:
    out = ClipOut.model_validate(clip)
    if clip.rendered and clip.output_path:
        out.output_url = f"/api/clips/{clip.id}/download"
    out.variants = [_variant_to_out(v) for v in clip.variants]
    transcript_path = clip.job.transcript_path
    if transcript_path and Path(transcript_path).exists():
        try:
            data = json.loads(Path(transcript_path).read_text(encoding="utf-8"))
            out.words = [
                WordTimestamp(**w)
                for w in data.get("words", [])
                if w.get("end", 0) > clip.start_time and w.get("start", 0) < clip.end_time
            ]
        except (OSError, json.JSONDecodeError):
            out.words = []
    return out


@clips_router.get("/{clip_id}", response_model=ClipOut)
def get_clip(clip_id: int, db: Session = Depends(get_db)) -> ClipOut:
    clip = db.get(Clip, clip_id)
    if clip is None:
        raise HTTPException(404, "Clip not found")
    return _hydrate_clip(clip)


@clips_router.post("/{clip_id}/trim", response_model=ClipOut)
def trim_clip(
    clip_id: int,
    payload: ClipTrimRequest,
    db: Session = Depends(get_db),
) -> ClipOut:
    """Update a clip's time range and trigger a background re-render."""
    clip = db.get(Clip, clip_id)
    if clip is None:
        raise HTTPException(404, "Clip not found")
    if payload.end_time <= payload.start_time:
        raise HTTPException(400, "end_time must be greater than start_time")

    clip.start_time = payload.start_time
    clip.end_time = payload.end_time
    clip.rendered = False
    clip.output_path = None
    db.commit()
    db.refresh(clip)

    rerender_clip_task.delay(clip.id)
    return _hydrate_clip(clip)


@clips_router.get("/{clip_id}/download")
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


@clips_router.get("/{clip_id}/transcript")
def download_clip_transcript(clip_id: int, db: Session = Depends(get_db)) -> JSONResponse:
    """Return the slice of the parent job's transcript covering this clip."""
    clip = db.get(Clip, clip_id)
    if clip is None:
        raise HTTPException(404, "Clip not found")
    transcript_path = clip.job.transcript_path
    if not transcript_path or not Path(transcript_path).exists():
        raise HTTPException(404, "Transcript not available for this clip")

    full = json.loads(Path(transcript_path).read_text(encoding="utf-8"))
    words_in_range = [
        w for w in full.get("words", [])
        if w["end"] > clip.start_time and w["start"] < clip.end_time
    ]
    payload = {
        "clip_id": clip.id,
        "title": clip.title,
        "start_time": clip.start_time,
        "end_time": clip.end_time,
        "text": " ".join(w["word"] for w in words_in_range).strip(),
        "words": words_in_range,
    }
    safe_title = clip.title[:50].replace(" ", "_").replace("/", "_")
    return JSONResponse(
        content=payload,
        headers={
            "Content-Disposition": f'attachment; filename="transcript_{safe_title}_{clip.id}.json"'
        },
    )


@clips_router.post("/batch-render", response_model=BatchRenderResponse, status_code=202)
def batch_render(
    payload: BatchRenderRequest,
    db: Session = Depends(get_db),
) -> BatchRenderResponse:
    """Enqueue a variant render for every (clip_id, template_id) combination."""
    for tid in payload.template_ids:
        TemplateEngine.get(tid)  # validates; raises PublishingError if unknown

    clips = db.query(Clip).filter(Clip.id.in_(payload.clip_ids)).all()
    if len(clips) != len(set(payload.clip_ids)):
        raise HTTPException(404, "One or more clips not found")

    new_ids: list[int] = []
    for clip in clips:
        for tid in payload.template_ids:
            variant = Variant(
                clip_id=clip.id,
                template_id=tid,
                status=VariantStatus.PENDING,
                variant_uuid=str(uuid.uuid4()),
            )
            db.add(variant)
            db.flush()
            new_ids.append(variant.id)
    db.commit()

    for vid in new_ids:
        render_variants_task.delay(vid)

    return BatchRenderResponse(variant_ids=new_ids)


@templates_router.get("", response_model=list[TemplateInfo])
def list_templates() -> list[TemplateInfo]:
    return [
        TemplateInfo(id=t.id, name=t.name, description=t.description)
        for t in TemplateEngine.list_templates()
    ]


@variants_router.get("/{variant_id}", response_model=VariantOut)
def get_variant(variant_id: int, db: Session = Depends(get_db)) -> VariantOut:
    variant = db.get(Variant, variant_id)
    if variant is None:
        raise HTTPException(404, "Variant not found")
    return _variant_to_out(variant)


@variants_router.get("/{variant_id}/download")
def download_variant(variant_id: int, db: Session = Depends(get_db)) -> FileResponse:
    variant = db.get(Variant, variant_id)
    if variant is None or not variant.output_path:
        raise HTTPException(404, "Variant not rendered yet")
    path = Path(variant.output_path)
    if not path.exists():
        raise HTTPException(404, "Variant file missing on disk")
    return FileResponse(
        path,
        media_type="video/mp4",
        filename=f"variant_{variant.template_id}_{variant.id}.mp4",
    )


router.include_router(clips_router)
router.include_router(templates_router)
router.include_router(variants_router)
