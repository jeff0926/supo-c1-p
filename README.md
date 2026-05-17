# OmniClip

AI video repurposing platform: ingests long-form video, finds viral hooks via LLM, reframes to 9:16 with face tracking, and burns in kinetic captions.

## Stack

- **Backend:** Python 3.11+, FastAPI, Celery + Redis, SQLAlchemy
- **Frontend:** React 18 + TypeScript + Vite + Tailwind
- **AI/ML:** OpenAI Whisper, Anthropic Claude, Google MediaPipe
- **Media:** FFmpeg (cropping, scaling, subtitle burn-in)

## Pipeline

```
Long-form video
  └─> Audio extraction (FFmpeg, 16kHz mono WAV)
      └─> Transcription (Whisper, word-level timestamps)
          └─> Semantic curation (Claude, viral hook detection)
              └─> Reframing (MediaPipe face tracking, smoothed crop)
                  └─> Captioning (.ass kinetic subtitles)
                      └─> Render (FFmpeg, single-pass crop+scale+burn)
                          └─> 9:16 vertical clips
```

## Quick start

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # then set ANTHROPIC_API_KEY
uvicorn app.main:app --reload --port 8000
# in a separate terminal:
celery -A app.workers.celery_app worker --loglevel=info
```

You also need a running Redis instance (default `redis://localhost:6379/0`) and FFmpeg on PATH.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The dev server proxies `/api` to `http://localhost:8000`.

## Layout

```
backend/
  app/
    api/         FastAPI routers (thin)
    services/    Pipeline subsystems (1-6)
    workers/     Celery task definitions
    models.py    SQLAlchemy ORM
    schemas.py   Pydantic payloads
    config.py    Settings
    main.py      App entry
frontend/
  src/
    components/  Functional UI components
    hooks/       State + polling hooks
    api.ts       Typed API client
    types.ts     Shared interfaces
```

## Milestones

- [x] M1: Whisper word-level timestamp extraction
- [x] M2: Claude JSON-enforced semantic curation
- [x] M3: MediaPipe face tracking with rolling-average smoothing
- [x] M4: Word-level JSON → .ass kinetic captions
- [x] M5: Async FastAPI workflow + React dashboard
