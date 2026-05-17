"""Subsystem 2: Whisper transcription with word-level timestamps."""
from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.config import settings
from app.schemas import Transcript, WordTimestamp

logger = logging.getLogger(__name__)


class TranscriptionError(RuntimeError):
    pass


@lru_cache(maxsize=1)
def _load_model(model_name: str) -> Any:
    try:
        import whisper
    except ImportError as exc:
        raise TranscriptionError("openai-whisper package not installed") from exc
    logger.info("Loading Whisper model: %s", model_name)
    return whisper.load_model(model_name)


def transcribe(audio_path: Path, output_json: Path | None = None) -> Transcript:
    if not audio_path.exists():
        raise TranscriptionError(f"Audio file not found: {audio_path}")

    model = _load_model(settings.whisper_model)

    try:
        result = model.transcribe(
            str(audio_path),
            word_timestamps=True,
            verbose=False,
        )
    except Exception as exc:
        raise TranscriptionError(f"Whisper transcription failed: {exc}") from exc

    words: list[WordTimestamp] = []
    for segment in result.get("segments", []):
        for w in segment.get("words", []) or []:
            token = (w.get("word") or "").strip()
            if not token:
                continue
            words.append(
                WordTimestamp(
                    word=token,
                    start=float(w.get("start", 0.0)),
                    end=float(w.get("end", 0.0)),
                )
            )

    transcript = Transcript(text=result.get("text", "").strip(), words=words)

    if output_json is not None:
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(transcript.model_dump_json(indent=2), encoding="utf-8")

    return transcript


def load_transcript(path: Path) -> Transcript:
    data = json.loads(path.read_text(encoding="utf-8"))
    return Transcript.model_validate(data)
