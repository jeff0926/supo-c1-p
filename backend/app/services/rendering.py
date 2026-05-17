"""Subsystem 6: Single-pass FFmpeg render — crop, scale, burn subtitles."""
from __future__ import annotations

import logging
import shlex
import shutil
import subprocess
from pathlib import Path

from app.config import settings
from app.services.reframing import CropTrack, average_crop_x

logger = logging.getLogger(__name__)


class RenderError(RuntimeError):
    pass


def render_clip(
    source_video: Path,
    crop_track: CropTrack,
    subtitle_path: Path,
    start_time: float,
    end_time: float,
    output_path: Path,
) -> Path:
    if shutil.which("ffmpeg") is None:
        raise RenderError("ffmpeg not found on PATH")
    if not source_video.exists():
        raise RenderError(f"Source video missing: {source_video}")
    if not subtitle_path.exists():
        raise RenderError(f"Subtitle file missing: {subtitle_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    crop_x = average_crop_x(crop_track)
    crop_w = crop_track.crop_width
    crop_h = crop_track.height

    # FFmpeg's subtitles filter requires an escaped path on some platforms.
    sub_arg = str(subtitle_path).replace("\\", "/").replace(":", "\\:")

    vf = (
        f"crop={crop_w}:{crop_h}:{crop_x}:0,"
        f"scale={settings.output_width}:{settings.output_height},"
        f"subtitles='{sub_arg}'"
    )

    cmd = [
        "ffmpeg",
        "-y",
        "-ss", f"{start_time:.3f}",
        "-to", f"{end_time:.3f}",
        "-i", str(source_video),
        "-vf", vf,
        "-c:v", "libx264",
        "-crf", "18",
        "-preset", "fast",
        "-c:a", "aac",
        "-b:a", "192k",
        str(output_path),
    ]
    logger.info("Rendering clip: %s", shlex.join(cmd))

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
        logger.debug("ffmpeg stderr tail: %s", proc.stderr[-500:])
    except subprocess.CalledProcessError as exc:
        raise RenderError(f"ffmpeg render failed: {exc.stderr[-1000:]}") from exc

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise RenderError(f"Render produced no output at {output_path}")
    return output_path
