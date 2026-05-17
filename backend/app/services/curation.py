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
transcription block. Pinpoint self-contained viral clip candidates that contain:
  1. A compelling initial hook within the first 3 seconds.
  2. A substantive core point.
  3. A clean contextual exit (no mid-sentence cuts).

Each clip should be 15-90 seconds long. Ensure chosen timestamps align exactly with
the word boundaries provided.

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


def curate(transcript: Transcript) -> list[ClipCandidate]:
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
        for clip in result.clips:
            clip.start_time = _snap_to_word_boundary(transcript.words, clip.start_time, "start")
            clip.end_time = _snap_to_word_boundary(transcript.words, clip.end_time, "end")
            if clip.end_time <= clip.start_time:
                continue
            all_clips.append(clip)

    return _dedupe_overlapping(all_clips)


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
