# OmniClip — Claude Code Guide

AI video repurposing pipeline. Long-form video in, viral 9:16 short clips out.

## Architecture philosophy

- **KISS:** Deterministic Python + FFmpeg over distributed frameworks.
- **Decoupled processing:** Heavy work runs in Celery workers, not request handlers.
- **Thin controllers:** API routes delegate to `app/services/*` modules.

## Stack

- Backend: Python 3.11+, FastAPI, Celery+Redis, SQLAlchemy, FFmpeg, MoviePy/OpenCV
- Frontend: React 18, TypeScript (strict, no `any`), Tailwind, Vite
- AI/ML: Whisper (transcription), Anthropic Claude (curation), MediaPipe (face tracking)

## Subsystem map

| # | Module | Input | Output |
|---|---|---|---|
| 1 | `services/ingestion.py` | video file/URL | 16kHz mono WAV |
| 2 | `services/transcription.py` | WAV | word-level timestamp JSON |
| 3 | `services/curation.py` | transcript | clip candidates with virality scores |
| 4 | `services/reframing.py` | video segment | smoothed X-axis crop coords |
| 5 | `services/captioning.py` | word JSON | `.ass` subtitle file |
| 6 | `services/rendering.py` | all of the above | final 9:16 MP4 |

## Commands

### Backend
```bash
pip install -r backend/requirements.txt
uvicorn app.main:app --reload --port 8000        # from backend/
celery -A app.workers.celery_app worker --loglevel=info
pytest                                            # from backend/
```

### Frontend
```bash
cd frontend
npm install
npm run dev
npm run build
npm run lint
```

## Code style

### Backend
- Explicit type hints on every function signature.
- Never swallow exceptions — wrap each pipeline stage in `try/except` with stack-trace logging.
- Business logic lives in `services/`, never in route handlers.

### Frontend
- Functional components + hooks only.
- `noImplicitAny: true`. Define interfaces for every API payload.
- Separate UI presentation from video playback/render state.

## Conventions

- LLM provider: Anthropic Claude via `anthropic` SDK. Default model: `claude-sonnet-4-6`.
- Storage: SQLite by default (`omniclip.db`), Postgres-compatible via `DATABASE_URL`.
- Media files: `MEDIA_ROOT` (default `./media/`), organized as `media/{job_id}/{stage}.ext`.
- Word-level JSON shape: `{ "text": str, "words": [{ "word": str, "start": float, "end": float }] }`.
- Clip shape: `{ "title": str, "start_time": float, "end_time": float, "virality_score": int, "reasoning": str }`.

## Don'ts

- Don't put FFmpeg subprocess calls or ML model loads in route handlers.
- Don't return raw model output to the frontend — always validate against Pydantic schemas first.
- Don't block the event loop with sync FFmpeg or Whisper calls — enqueue to Celery.
