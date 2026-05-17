"""Milestone 1 CLI: FFmpeg + Whisper -> word-level timestamp JSON.

Usage:
    python -m scripts.transcribe_cli input.mp4 [--out transcript.json]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.services.ingestion import extract_audio
from app.services.transcription import transcribe


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract word-level transcript from a video.")
    parser.add_argument("video", type=Path)
    parser.add_argument("--out", type=Path, default=Path("transcript.json"))
    parser.add_argument("--tmp", type=Path, default=Path("audio.wav"))
    args = parser.parse_args()

    if not args.video.exists():
        print(f"Video not found: {args.video}", file=sys.stderr)
        return 1

    print(f"[1/2] Extracting audio -> {args.tmp}")
    extract_audio(args.video, args.tmp)

    print(f"[2/2] Transcribing -> {args.out}")
    transcript = transcribe(args.tmp, args.out)
    print(f"Wrote {len(transcript.words)} word timestamps")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
