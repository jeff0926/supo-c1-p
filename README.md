# supo-c1-p — OmniClip

AI video repurposing platform built in the **`supo-c1-p`** repository. Ingests long-form video, finds viral hooks via LLM, reframes to 9:16 with face tracking, and burns in kinetic captions.

> **Design conversation:** The blueprint behind this build was iterated in a Gemini chat — see <https://g.co/gemini/share/fab1b5fb9281>.

## Stack

- **Backend:** Python 3.11+, FastAPI, Celery + Redis, SQLAlchemy
- **Frontend:** React 18 + TypeScript (strict, no `any`) + Vite + Tailwind
- **AI/ML:** OpenAI Whisper (transcription), Anthropic Claude `claude-sonnet-4-6` (curation), Google MediaPipe (face tracking)
- **Media:** FFmpeg (cropping, scaling, subtitle burn-in)

## Pipeline

```
Long-form video
  └─> Audio extraction (FFmpeg, 16kHz mono WAV)
      └─> Transcription (Whisper, word-level timestamps)
          └─> Semantic curation (Claude, viral hook detection, JSON-enforced)
              └─> Reframing (MediaPipe face tracking, 24-frame rolling avg)
                  └─> Captioning (.ass kinetic subtitles, neon-yellow active word)
                      └─> Render (FFmpeg, single-pass crop + scale + burn)
                          └─> 9:16 vertical clips
```

## Quick start

### Docker (easiest)

```bash
cp .env.example .env          # then set ANTHROPIC_API_KEY
docker compose up
```

- Backend API: <http://localhost:8000> (`/docs` for Swagger)
- Frontend:   <http://localhost:5173>

### Manual

**Backend** (requires FFmpeg on PATH and a running Redis):

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then set ANTHROPIC_API_KEY
uvicorn app.main:app --reload --port 8000
# in a separate terminal:
celery -A app.workers.celery_app worker --loglevel=info
```

**Frontend:**

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server proxies `/api` to `http://localhost:8000`.

## Layout

```
supo-c1-p/
├── backend/
│   ├── app/
│   │   ├── api/           # FastAPI routers (thin)
│   │   │   ├── videos.py  # upload, list
│   │   │   ├── jobs.py    # status polling
│   │   │   └── clips.py   # download rendered clips
│   │   ├── services/      # Pipeline subsystems 1-6
│   │   │   ├── ingestion.py     # FFmpeg audio extraction
│   │   │   ├── transcription.py # Whisper word-level
│   │   │   ├── curation.py      # Claude semantic curation
│   │   │   ├── reframing.py     # MediaPipe + smoothing
│   │   │   ├── captioning.py    # .ass kinetic captions
│   │   │   └── rendering.py     # FFmpeg single-pass render
│   │   ├── workers/       # Celery orchestration
│   │   ├── models.py      # SQLAlchemy ORM (Video, Job, Clip)
│   │   ├── schemas.py     # Pydantic v2 payloads
│   │   ├── config.py      # Settings
│   │   └── main.py        # App entry
│   ├── scripts/
│   │   └── transcribe_cli.py    # Milestone 1 CLI
│   ├── tests/             # 9 unit tests, no ML deps required
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── components/    # VideoUploader, JobList, ClipGrid, ClipPreview
│       ├── hooks/         # useJobs (auto-polling)
│       ├── api.ts         # Typed API client
│       └── types.ts       # Shared interfaces
├── docker-compose.yml     # backend + worker + redis + frontend
├── CLAUDE.md              # Guide for Claude Code on this repo
└── README.md
```

## API

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/videos` | Upload `.mp4` / `.mov` / `.mkv` / `.webm`, kicks off pipeline |
| `GET`  | `/api/videos` | List all uploaded videos |
| `GET`  | `/api/jobs` | List all jobs with current status + clips |
| `GET`  | `/api/jobs/{id}` | Single job detail |
| `GET`  | `/api/clips/{id}` | Clip metadata |
| `GET`  | `/api/clips/{id}/download` | Stream rendered MP4 |
| `GET`  | `/api/health` | Health check |

## Testing

```bash
cd backend && pytest
```

9 tests cover the deterministic math (caption phrasing, curation chunking/parsing/overlap dedup, MediaPipe-track smoothing/clamping). Heavy ML deps are lazy-imported so these run without `whisper`, `mediapipe`, or `cv2` installed.

## Milestones

- [x] **M1:** FFmpeg + Whisper CLI → word-level timestamp JSON (`backend/scripts/transcribe_cli.py`)
- [x] **M2:** Claude JSON-enforced semantic curation with word-boundary snapping
- [x] **M3:** MediaPipe face tracking with 24-frame rolling-average smoothing
- [x] **M4:** Word-level JSON → kinetic `.ass` captions with per-word highlighting
- [x] **M5:** Async FastAPI + Celery workflow + React dashboard

## Configuration

Environment variables (see `.env.example`):

| Var | Default | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | _(required)_ | Claude API access |
| `CLAUDE_MODEL` | `claude-sonnet-4-6` | Curation model |
| `WHISPER_MODEL` | `base` | `tiny`/`base`/`small`/`medium`/`large` |
| `REDIS_URL` | `redis://localhost:6379/0` | Celery broker |
| `DATABASE_URL` | `sqlite:///./omniclip.db` | SQLite or Postgres |
| `MEDIA_ROOT` | `./media` | Where uploads + renders are stored |

## References

- Design conversation (Gemini): <https://g.co/gemini/share/fab1b5fb9281>
- Repository: `jeff0926/supo-c1-p`
- Working branch: `claude/new-session-aK45l`
