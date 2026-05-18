"""Template engine + per-clip variant renderer.

Each template applies a materially different visual style (font, colors, caption
position, crop offset, sharpening). Outputs are written to
`media/job_{id}/variants/{template_id}/clip_{clip_id}_{uuid}.mp4`.

For traceability, every variant embeds a unique UUID in the MP4's `comment`
metadata tag — this gives each variant a distinct, labeled MD5 even when two
templates happen to produce visually similar output.
"""
from __future__ import annotations

import hashlib
import logging
import shutil
import subprocess
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from app.config import settings
from app.schemas import WordTimestamp

if TYPE_CHECKING:
    from app.services.reframing import CropTrack

logger = logging.getLogger(__name__)


class PublishingError(RuntimeError):
    pass


@dataclass(frozen=True)
class Template:
    id: str
    name: str
    description: str
    font: str
    font_size: int
    primary_color: str          # ASS BGR &HAABBGGRR&
    highlight_color: str
    outline_color: str
    outline_width: int
    alignment: int               # ASS alignment code (1-9)
    margin_v: int                # vertical margin from edge
    caption_y: int               # absolute Y for \pos override
    # Approximate per-character width as a fraction of font_size. Heavy/black
    # weights run ~0.65; narrow weights like Impact ~0.50; regular sans ~0.55.
    char_width_ratio: float = 0.58
    crop_offset_ratio: float = 0.0  # shift crop horizontally by this fraction of width
    extra_video_filters: tuple[str, ...] = field(default_factory=tuple)


SIDE_MARGIN_PX = 40


def _max_chars_for_template(template: Template) -> int:
    usable = settings.output_width - 2 * SIDE_MARGIN_PX
    avg_char_px = template.font_size * template.char_width_ratio
    return max(6, int(usable / avg_char_px))


class TemplateEngine:
    """Stateless registry of available templates."""

    _TEMPLATES: dict[str, Template] = {
        "kinetic_yellow": Template(
            id="kinetic_yellow",
            name="Kinetic Yellow",
            description="Default heavy sans, neon-yellow active word, lower-middle.",
            font="Montserrat Black",
            font_size=72,
            primary_color="&H00FFFFFF&",
            highlight_color="&H0000FFFF&",
            outline_color="&H00000000&",
            outline_width=3,
            alignment=5,
            margin_v=0,
            caption_y=1400,
            char_width_ratio=0.62,
        ),
        "kinetic_neon": Template(
            id="kinetic_neon",
            name="Kinetic Neon",
            description="Hot-pink active word with cyan outline, centered.",
            font="Impact",
            font_size=80,
            primary_color="&H00F0F0F0&",
            highlight_color="&H00C71585&",
            outline_color="&H00FFFF00&",
            outline_width=4,
            alignment=5,
            margin_v=0,
            caption_y=960,
            char_width_ratio=0.48,
        ),
        "kinetic_minimal": Template(
            id="kinetic_minimal",
            name="Kinetic Minimal",
            description="Small white captions, top placement, no shouty styling.",
            font="Arial",
            font_size=52,
            primary_color="&H00FFFFFF&",
            highlight_color="&H00FFFFFF&",
            outline_color="&H00202020&",
            outline_width=1,
            alignment=5,
            margin_v=0,
            caption_y=300,
            char_width_ratio=0.55,
        ),
        "kinetic_bold": Template(
            id="kinetic_bold",
            name="Kinetic Bold",
            description="Massive all-caps text, dropped low with heavy outline.",
            font="Arial Black",
            font_size=96,
            primary_color="&H00FFFFFF&",
            highlight_color="&H0000A5FF&",
            outline_color="&H00000000&",
            outline_width=5,
            alignment=5,
            margin_v=0,
            caption_y=1500,
            char_width_ratio=0.66,
            extra_video_filters=("unsharp=5:5:0.8:5:5:0.0",),
        ),
    }

    @classmethod
    def list_templates(cls) -> list[Template]:
        return list(cls._TEMPLATES.values())

    @classmethod
    def get(cls, template_id: str) -> Template:
        try:
            return cls._TEMPLATES[template_id]
        except KeyError as exc:
            raise PublishingError(f"Unknown template: {template_id}") from exc


def build_ass_for_template(
    words: list[WordTimestamp],
    clip_start: float,
    clip_end: float,
    template: Template,
    output_path: Path,
) -> Path:
    """Generate a per-template .ass file with the template's typography rules."""
    in_range = [w for w in words if w.end > clip_start and w.start < clip_end]
    max_chars = _max_chars_for_template(template)
    phrases = _group_phrases(in_range, max_chars=max_chars)

    header = (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        f"PlayResX: {settings.output_width}\n"
        f"PlayResY: {settings.output_height}\n"
        "ScaledBorderAndShadow: yes\n"
        "WrapStyle: 0\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Default,{template.font},{template.font_size},{template.primary_color},{template.primary_color},{template.outline_color},{template.outline_color},-1,0,0,0,100,100,0,0,1,{template.outline_width},0,{template.alignment},{SIDE_MARGIN_PX},{SIDE_MARGIN_PX},{template.margin_v},1\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        f.write(header)
        for phrase in phrases:
            for line in _phrase_dialogue_lines(phrase, clip_start, template):
                f.write(line + "\n")
    return output_path


def _group_phrases(
    words: list[WordTimestamp],
    max_chars: int,
    max_gap: float = 0.6,
) -> list[list[WordTimestamp]]:
    phrases: list[list[WordTimestamp]] = []
    current: list[WordTimestamp] = []
    char_count = 0
    for w in words:
        if current:
            gap = w.start - current[-1].end
            would_overflow = char_count + len(w.word) + 1 > max_chars
            if gap > max_gap or would_overflow:
                phrases.append(current)
                current = []
                char_count = 0
        current.append(w)
        char_count += len(w.word) + 1
    if current:
        phrases.append(current)
    return phrases


def _format_time(seconds: float) -> str:
    seconds = max(0.0, seconds)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds - (h * 3600 + m * 60)
    return f"{h:d}:{m:02d}:{s:05.2f}"


def _phrase_dialogue_lines(
    phrase: list[WordTimestamp], clip_start: float, template: Template
) -> list[str]:
    if not phrase:
        return []
    lines: list[str] = []
    phrase_end = phrase[-1].end
    pos_x = settings.output_width // 2
    for i, active in enumerate(phrase):
        parts: list[str] = []
        for j, w in enumerate(phrase):
            token = w.word.upper().strip()
            if not token:
                continue
            if j == i:
                parts.append(
                    f"{{\\c{template.highlight_color}}}{token}{{\\c{template.primary_color}}}"
                )
            else:
                parts.append(token)
        text = " ".join(parts)
        seg_start = max(0.0, active.start - clip_start)
        seg_end = (
            max(seg_start, phrase[i + 1].start - clip_start)
            if i + 1 < len(phrase)
            else max(seg_start, phrase_end - clip_start)
        )
        override = f"{{\\pos({pos_x},{template.caption_y})}}"
        lines.append(
            f"Dialogue: 0,{_format_time(seg_start)},{_format_time(seg_end)},"
            f"Default,,0,0,0,,{override}{text}"
        )
    return lines


class VariantRenderer:
    """Stateless service that renders one (clip, template) variant.

    Compiles an FFmpeg complex-filter command from a `CropTrack` and a
    `Template`, embeds a unique variant UUID in the MP4 metadata, and writes
    output under `media/job_{job_id}/variants/{template_id}/`.
    """

    @staticmethod
    def output_dir(job_id: int, template_id: str) -> Path:
        path = settings.media_path / f"job_{job_id}" / "variants" / template_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    def render(
        *,
        source_video: Path,
        crop_track: "CropTrack",
        words: list[WordTimestamp],
        clip_id: int,
        job_id: int,
        start_time: float,
        end_time: float,
        template: Template,
    ) -> tuple[Path, str, str]:
        """Render a single variant. Returns (output_path, variant_uuid, md5_hex)."""
        if shutil.which("ffmpeg") is None:
            raise PublishingError("ffmpeg not found on PATH")
        if not source_video.exists():
            raise PublishingError(f"Source video missing: {source_video}")

        variant_uuid = str(uuid.uuid4())
        out_dir = VariantRenderer.output_dir(job_id, template.id)
        output_path = out_dir / f"clip_{clip_id}_{variant_uuid[:8]}.mp4"

        from app.services.reframing import average_crop_x

        crop_x = average_crop_x(crop_track)
        crop_w = crop_track.crop_width
        crop_h = crop_track.height

        # Apply per-template crop offset (clamped so we never leave the frame).
        offset_pixels = int(template.crop_offset_ratio * crop_track.width)
        crop_x = max(0, min(crop_track.width - crop_w, crop_x + offset_pixels))

        subtitle_path = out_dir / f"clip_{clip_id}_{variant_uuid[:8]}.ass"
        build_ass_for_template(words, start_time, end_time, template, subtitle_path)
        sub_arg = str(subtitle_path).replace("\\", "/").replace(":", "\\:")

        filters: list[str] = [
            f"crop={crop_w}:{crop_h}:{crop_x}:0",
            f"scale={settings.output_width}:{settings.output_height}",
            *template.extra_video_filters,
            f"subtitles='{sub_arg}'",
        ]
        vf = ",".join(filters)

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
            # Embed identifying metadata so the resulting MP4 carries a stable,
            # auditable variant identifier. Different variant_uuids -> different
            # bytes in the MOOV box -> different MD5s, with the change being
            # visible and labeled rather than hidden.
            "-metadata", f"comment=variant_uuid={variant_uuid};template={template.id}",
            "-metadata", f"title=variant_{template.id}_{variant_uuid[:8]}",
            str(output_path),
        ]

        logger.info(
            "Rendering variant clip=%d template=%s uuid=%s", clip_id, template.id, variant_uuid
        )
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
            logger.debug("ffmpeg variant stderr tail: %s", proc.stderr[-300:])
        except subprocess.CalledProcessError as exc:
            raise PublishingError(f"ffmpeg variant render failed: {exc.stderr[-1000:]}") from exc

        if not output_path.exists() or output_path.stat().st_size == 0:
            raise PublishingError(f"Variant produced no output at {output_path}")

        md5 = hashlib.md5(output_path.read_bytes()).hexdigest()
        return output_path, variant_uuid, md5
