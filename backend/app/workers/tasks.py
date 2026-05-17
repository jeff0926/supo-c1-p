"""End-to-end pipeline orchestration: ingest -> transcribe -> curate -> reframe
-> caption -> render. One Celery task per video; renders run inline per clip
so we keep one job_dir per pipeline run.
"""
from __future__ import annotations

import logging
from pathlib import Path

from app.config import settings
from app.database import SessionLocal
from app.models import Clip, Job, JobStatus
from app.services import captioning, curation, ingestion, reframing, rendering, transcription
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


def _job_dir(job_id: int) -> Path:
    p = settings.media_path / f"job_{job_id}"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _set_status(job_id: int, status: JobStatus, error: str | None = None) -> None:
    with SessionLocal() as db:
        job = db.get(Job, job_id)
        if job is None:
            return
        job.status = status
        if error is not None:
            job.error_message = error
        db.commit()


@celery_app.task(name="omniclip.process_video")
def process_video(job_id: int) -> dict:
    logger.info("Starting pipeline for job %d", job_id)
    work_dir = _job_dir(job_id)

    with SessionLocal() as db:
        job = db.get(Job, job_id)
        if job is None:
            raise RuntimeError(f"Job {job_id} not found")
        source_path = Path(job.video.source_path)

    try:
        # Subsystem 1: audio extraction
        _set_status(job_id, JobStatus.EXTRACTING_AUDIO)
        audio_path = work_dir / "audio.wav"
        ingestion.extract_audio(source_path, audio_path)

        # Subsystem 2: transcription
        _set_status(job_id, JobStatus.TRANSCRIBING)
        transcript_path = work_dir / "transcript.json"
        transcript = transcription.transcribe(audio_path, transcript_path)
        with SessionLocal() as db:
            job = db.get(Job, job_id)
            job.transcript_path = str(transcript_path)
            db.commit()

        # Subsystem 3: curation
        _set_status(job_id, JobStatus.CURATING)
        candidates = curation.curate(transcript)
        logger.info("Curated %d clip candidates for job %d", len(candidates), job_id)

        clip_ids: list[int] = []
        with SessionLocal() as db:
            for c in candidates:
                clip = Clip(
                    job_id=job_id,
                    title=c.title,
                    start_time=c.start_time,
                    end_time=c.end_time,
                    virality_score=c.virality_score,
                    reasoning=c.reasoning,
                )
                db.add(clip)
                db.flush()
                clip_ids.append(clip.id)
            db.commit()

        # Subsystems 4-6: per-clip reframe, caption, render
        for clip_id in clip_ids:
            with SessionLocal() as db:
                clip = db.get(Clip, clip_id)
                start, end = clip.start_time, clip.end_time
                title = clip.title

            _set_status(job_id, JobStatus.REFRAMING)
            crop_track = reframing.compute_crop_track(source_path, start, end)

            _set_status(job_id, JobStatus.CAPTIONING)
            sub_path = work_dir / f"clip_{clip_id}.ass"
            captioning.build_ass(transcript.words, start, end, sub_path)

            _set_status(job_id, JobStatus.RENDERING)
            out_path = work_dir / f"clip_{clip_id}.mp4"
            rendering.render_clip(source_path, crop_track, sub_path, start, end, out_path)

            with SessionLocal() as db:
                clip = db.get(Clip, clip_id)
                clip.output_path = str(out_path)
                clip.rendered = True
                db.commit()
            logger.info("Rendered clip %d (%s) for job %d", clip_id, title, job_id)

        _set_status(job_id, JobStatus.COMPLETED)
        return {"job_id": job_id, "clips": len(clip_ids)}

    except Exception as exc:
        logger.exception("Pipeline failed for job %d", job_id)
        _set_status(job_id, JobStatus.FAILED, error=str(exc))
        raise
