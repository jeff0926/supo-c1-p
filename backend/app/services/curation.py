"""Subsystem 3: LLM semantic curation via Anthropic Claude.

Chunks the transcript into overlapping windows, asks Claude to pull viral
hook candidates as strict JSON, then snaps timestamps to true word boundaries.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from app.config import settings
from app.schemas import ClipCandidate, CurationResult, Transcript, WordTimestamp

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are a viral short-form video curator. Examine the provided
transcription block and pinpoint the most engaging clip candidates.

Each clip must:
  1. Open with a compelling hook (intriguing claim, question, or stat).
  2. Contain a substantive core point or insight.
  3. End on a clean sentence boundary (no mid-sentence cuts).

Target length: 8-90 seconds. Shorter is fine if the segment is self-contained.
If the transcript is short, return at least one clip covering the strongest portion
of the whole transcript rather than returning an empty list — unless the audio
contains no intelligible speech at all.

Ensure chosen timestamps align exactly with the word boundaries provided.

Respond with strict JSON only — no prose, no markdown fences — matching this shape:
{
  "clips": [
    {
      "title": "short punchy hook title",
      "start_time": 0.12,
      "end_time": 62.45,
      "virality_score": 96,
      "reasoning": "why this segment will perform"
    }
  ]
}
If no clips meet the bar, return {"clips": []}."""


class CurationError(RuntimeError):
    pass


def _chunk_words(
    words: list[WordTimestamp],
    chunk_seconds: int,
    overlap_seconds: int,
) -> list[list[WordTimestamp]]:
    if not words:
        return []
    chunks: list[list[WordTimestamp]] = []
    cursor = 0.0
    end = words[-1].end
    while cursor < end:
        chunk_end = cursor + chunk_seconds
        chunk = [w for w in words if w.start >= cursor and w.start < chunk_end]
        if chunk:
            chunks.append(chunk)
        cursor += chunk_seconds - overlap_seconds
    return chunks


def _chunk_to_prompt(chunk: list[WordTimestamp]) -> str:
    lines = [f"[{w.start:.2f}-{w.end:.2f}] {w.word}" for w in chunk]
    return "\n".join(lines)


def _snap_to_word_boundary(words: list[WordTimestamp], t: float, kind: str) -> float:
    if not words:
        return t
    if kind == "start":
        candidates = [w for w in words if w.start >= t - 0.5]
        return candidates[0].start if candidates else words[0].start
    candidates = [w for w in words if w.end <= t + 0.5]
    return candidates[-1].end if candidates else words[-1].end


def _parse_response(text: str) -> CurationResult:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()
    try:
        data: Any = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise CurationError(f"Claude returned non-JSON: {text[:200]}") from exc
    return CurationResult.model_validate(data)


def curate(transcript: Transcript, use_llm: bool = True) -> list[ClipCandidate]:
    """Pick clip candidates from a transcript.

    When `use_llm` is True (default), uses Claude for semantic curation.
    When False, falls back to a deterministic pause-based segmenter — useful for
    local development without API calls.
    """
    if not use_llm:
        logger.info("LLM disabled; using deterministic pause-based curation")
        return deterministic_segmentation(transcript)

    if not settings.anthropic_api_key:
        raise CurationError("ANTHROPIC_API_KEY is not configured")

    from anthropic import Anthropic

    client = Anthropic(api_key=settings.anthropic_api_key)

    chunks = _chunk_words(
        transcript.words,
        chunk_seconds=settings.chunk_seconds,
        overlap_seconds=settings.chunk_overlap_seconds,
    )
    logger.info("Curating %d transcript chunks", len(chunks))

    all_clips: list[ClipCandidate] = []
    for idx, chunk in enumerate(chunks):
        try:
            response = client.messages.create(
                model=settings.claude_model,
                max_tokens=2048,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": _chunk_to_prompt(chunk)}],
            )
        except Exception as exc:
            logger.exception("Claude call failed on chunk %d", idx)
            raise CurationError(f"Claude API failure on chunk {idx}: {exc}") from exc

        body = "".join(
            block.text for block in response.content if getattr(block, "type", "") == "text"
        )
        result = _parse_response(body)
        if not result.clips:
            logger.info("Claude returned 0 clips for chunk %d. Raw response: %s", idx, body[:500])
        for clip in result.clips:
            clip.start_time = _snap_to_word_boundary(transcript.words, clip.start_time, "start")
            clip.end_time = _snap_to_word_boundary(transcript.words, clip.end_time, "end")
            if clip.end_time <= clip.start_time:
                logger.warning(
                    "Dropping clip after word-boundary snap (start=%.2f end=%.2f title=%s)",
                    clip.start_time, clip.end_time, clip.title,
                )
                continue
            all_clips.append(clip)

    return _dedupe_overlapping(all_clips)


def deterministic_segmentation(
    transcript: Transcript,
    target_seconds: float = 45.0,
    pause_threshold: float = 0.8,
    min_seconds: float = 8.0,
) -> list[ClipCandidate]:
    """Pure-Python clip detector — no LLM required.

    Walks the word-level transcript and starts a new clip whenever the gap
    between consecutive words exceeds `pause_threshold`. Clips are merged
    until they reach roughly `target_seconds` so we don't emit hundreds of
    micro-fragments. Used when `use_llm=False`.
    """
    if not transcript.words:
        return []

    words = transcript.words
    candidates: list[ClipCandidate] = []
    current_start = words[0].start
    current_text: list[str] = [words[0].word]
    current_end = words[0].end

    for prev, nxt in zip(words, words[1:]):
        gap = nxt.start - prev.end
        elapsed = prev.end - current_start
        is_natural_break = gap > pause_threshold
        is_long_enough = elapsed >= target_seconds

        if is_natural_break and elapsed >= min_seconds:
            candidates.append(_make_candidate(current_start, prev.end, current_text))
            current_start = nxt.start
            current_text = [nxt.word]
            current_end = nxt.end
        elif is_long_enough and is_natural_break:
            candidates.append(_make_candidate(current_start, prev.end, current_text))
            current_start = nxt.start
            current_text = [nxt.word]
            current_end = nxt.end
        else:
            current_text.append(nxt.word)
            current_end = nxt.end

    if current_end - current_start >= min_seconds:
        candidates.append(_make_candidate(current_start, current_end, current_text))

    logger.info("Deterministic segmenter produced %d candidates", len(candidates))
    return candidates


def _make_candidate(start: float, end: float, words: list[str]) -> ClipCandidate:
    text = " ".join(words).strip()
    title = (text[:60] + "…") if len(text) > 60 else text
    return ClipCandidate(
        title=title or f"Segment {start:.1f}-{end:.1f}",
        start_time=float(start),
        end_time=float(end),
        virality_score=50,
        reasoning="Deterministic pause-based segmentation (LLM curation disabled).",
    )


def _dedupe_overlapping(clips: list[ClipCandidate]) -> list[ClipCandidate]:
    clips_sorted = sorted(clips, key=lambda c: c.virality_score, reverse=True)
    kept: list[ClipCandidate] = []
    for clip in clips_sorted:
        overlap = any(
            not (clip.end_time <= k.start_time or clip.start_time >= k.end_time)
            for k in kept
        )
        if not overlap:
            kept.append(clip)
    return sorted(kept, key=lambda c: c.start_time)
