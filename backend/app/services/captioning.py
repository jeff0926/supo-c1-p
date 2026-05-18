"""Subsystem 5: Word-level JSON -> Advanced SubStation Alpha (.ass) kinetic captions.

Per-word highlighting: spoken word renders in neon yellow, neighboring words in
white with bold black outline. Centered in the lower-middle safe area for 9:16.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

from app.config import settings
from app.schemas import WordTimestamp

HIGHLIGHT_COLOR = "&H0000FFFF&"  # neon yellow (ASS BGR)
DEFAULT_COLOR = "&H00FFFFFF&"    # white
OUTLINE_COLOR = "&H00000000&"    # black

DEFAULT_FONT_SIZE = 72
DEFAULT_CHAR_WIDTH_RATIO = 0.62  # Montserrat Black is heavy/wide
SIDE_MARGIN = 40                  # px of safe area on each side


def _max_chars_for(font_size: int, char_width_ratio: float) -> int:
    """How many characters fit on one line at the given font size."""
    usable = settings.output_width - 2 * SIDE_MARGIN
    avg_char_px = font_size * char_width_ratio
    return max(6, int(usable / avg_char_px))


def _format_time(seconds: float) -> str:
    seconds = max(0.0, seconds)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds - (h * 3600 + m * 60)
    return f"{h:d}:{m:02d}:{s:05.2f}"


def _ass_header(width: int, height: int) -> str:
    return f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
ScaledBorderAndShadow: yes
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Montserrat Black,{DEFAULT_FONT_SIZE},{DEFAULT_COLOR},{DEFAULT_COLOR},{OUTLINE_COLOR},{OUTLINE_COLOR},-1,0,0,0,100,100,0,0,1,3,0,5,{SIDE_MARGIN},{SIDE_MARGIN},0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def _group_into_phrases(
    words: list[WordTimestamp],
    max_chars: int | None = None,
    max_gap: float = 0.6,
) -> list[list[WordTimestamp]]:
    """Group words into short readable phrases the viewer can track."""
    if max_chars is None:
        max_chars = _max_chars_for(DEFAULT_FONT_SIZE, DEFAULT_CHAR_WIDTH_RATIO)
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


def _phrase_to_events(
    phrase: list[WordTimestamp],
    clip_start: float,
    position_y: int,
) -> Iterable[str]:
    """Emit one Dialogue line per spoken word, highlighting that word."""
    if not phrase:
        return
    phrase_end = phrase[-1].end
    for i, active in enumerate(phrase):
        parts: list[str] = []
        for j, w in enumerate(phrase):
            token = w.word.upper().strip()
            if not token:
                continue
            if j == i:
                parts.append(f"{{\\c{HIGHLIGHT_COLOR}}}{token}{{\\c{DEFAULT_COLOR}}}")
            else:
                parts.append(token)
        text = " ".join(parts)
        seg_start = max(0.0, active.start - clip_start)
        if i + 1 < len(phrase):
            seg_end = max(seg_start, phrase[i + 1].start - clip_start)
        else:
            seg_end = max(seg_start, phrase_end - clip_start)
        # Use the lower-middle safe-area override on each line.
        override = f"{{\\pos({settings.output_width // 2},{position_y})}}"
        yield (
            f"Dialogue: 0,{_format_time(seg_start)},{_format_time(seg_end)},"
            f"Default,,0,0,0,,{override}{text}"
        )


def build_ass(
    words: list[WordTimestamp],
    clip_start: float,
    clip_end: float,
    output_path: Path,
    position_y: int = 1400,
) -> Path:
    """Write an .ass file covering words in [clip_start, clip_end]."""
    in_range = [w for w in words if w.end > clip_start and w.start < clip_end]
    phrases = _group_into_phrases(in_range)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        f.write(_ass_header(settings.output_width, settings.output_height))
        for phrase in phrases:
            for line in _phrase_to_events(phrase, clip_start=clip_start, position_y=position_y):
                f.write(line + "\n")
    return output_path
