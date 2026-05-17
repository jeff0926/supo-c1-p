"""Subsystem 1: Ingestion & Audio Extraction.

Runs FFmpeg to strip the source video down to a 16kHz mono PCM WAV optimized
for Whisper.
"""
from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


class IngestionError(RuntimeError):
    pass


def extract_audio(video_path: Path, output_wav: Path) -> Path:
    if not video_path.exists():
        raise IngestionError(f"Source video not found: {video_path}")
    if shutil.which("ffmpeg") is None:
        raise IngestionError("ffmpeg not found on PATH")

    output_wav.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg",
        "-y",
        "-i", str(video_path),
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        str(output_wav),
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
        logger.debug("ffmpeg audio extract stderr: %s", proc.stderr[-500:])
    except subprocess.CalledProcessError as exc:
        raise IngestionError(f"ffmpeg audio extraction failed: {exc.stderr}") from exc

    if not output_wav.exists() or output_wav.stat().st_size == 0:
        raise IngestionError(f"Audio extraction produced no output at {output_wav}")
    return output_wav


def probe_duration(video_path: Path) -> float:
    if shutil.which("ffprobe") is None:
        raise IngestionError("ffprobe not found on PATH")
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(video_path),
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(proc.stdout.strip())
    except (subprocess.CalledProcessError, ValueError) as exc:
        raise IngestionError(f"ffprobe failed for {video_path}: {exc}") from exc
