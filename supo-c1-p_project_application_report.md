# supo-c1-p — Project & Application Report

> **OmniClip**: AI-driven long-form-to-short-form video repurposing platform
> **Repository:** `jeff0926/supo-c1-p`
> **Branch:** `claude/new-session-aK45l`
> **Design conversation (Gemini):** <https://g.co/gemini/share/fab1b5fb9281>

---

## 1. Executive summary

`supo-c1-p` ("OmniClip") is a self-hosted, end-to-end pipeline that takes a long-form video — a podcast episode, a lecture, a sales call, a keynote — and automatically produces a deck of vertical 9:16 short-form clips ready for TikTok, Instagram Reels, and YouTube Shorts.

It combines four AI/ML systems behind a single API and dashboard:

1. **OpenAI Whisper** transcribes the audio with word-level precision.
2. **Anthropic Claude (`claude-sonnet-4-6`)** reads the transcript and pinpoints the segments most likely to go viral — segments with a hook, a payoff, and a clean exit.
3. **Google MediaPipe** tracks the speaker's face across each chosen segment.
4. **FFmpeg** crops, reframes, scales to 9:16, and burns in animated word-by-word captions in a single render pass.

The result: a creator uploads a 60-minute video and a few minutes later has 5–15 captioned, framed, ready-to-publish short-form clips ranked by predicted virality.

---

## 2. What we built

### 2.1 Architecture

A six-stage pipeline orchestrated asynchronously, with each stage encapsulated in its own service module:

```
┌─────────────────────┐
│  Long-form video    │  (mp4 / mov / mkv / webm)
└──────────┬──────────┘
           │
           ▼  Subsystem 1: Ingestion & audio extraction
┌─────────────────────┐
│  16 kHz mono WAV    │  via FFmpeg
└──────────┬──────────┘
           ▼  Subsystem 2: Whisper transcription
┌─────────────────────┐
│  Word-level         │
│  timestamp JSON     │
└──────────┬──────────┘
           ▼  Subsystem 3: Claude semantic curation
┌─────────────────────┐
│  Ranked viral hook  │
│  candidates (JSON)  │
└──────────┬──────────┘
           ▼  Subsystem 4: MediaPipe face tracking
┌─────────────────────┐
│  Smoothed X-axis    │
│  crop coordinates   │
└──────────┬──────────┘
           ▼  Subsystem 5: SubStation Alpha captioning
┌─────────────────────┐
│  .ass subtitle file │
│  per clip           │
└──────────┬──────────┘
           ▼  Subsystem 6: FFmpeg single-pass render
┌─────────────────────┐
│  Final 9:16 MP4s    │
└─────────────────────┘
```

### 2.2 Stack

| Layer | Technology |
|---|---|
| Backend API | FastAPI (Python 3.11) |
| Async work queue | Celery + Redis |
| Persistence | SQLAlchemy + SQLite (Postgres-ready via `DATABASE_URL`) |
| Frontend | React 18 + TypeScript (strict, `noImplicitAny`) + Vite + Tailwind CSS |
| Transcription | OpenAI Whisper (local model: `tiny` / `base` / `small` / `medium` / `large`) |
| Curation LLM | Anthropic Claude `claude-sonnet-4-6` |
| Face tracking | Google MediaPipe Face Detection |
| Computer vision | OpenCV |
| Media processing | FFmpeg + ffprobe |
| Subtitle format | Advanced SubStation Alpha (`.ass`) |
| Containerization | Docker + Docker Compose |

### 2.3 Repository layout

```
supo-c1-p/
├── backend/
│   ├── app/
│   │   ├── api/                  Thin FastAPI routers
│   │   │   ├── videos.py         Upload + list videos
│   │   │   ├── jobs.py           Job status + clips
│   │   │   └── clips.py          Clip metadata + MP4 download
│   │   ├── services/             Six pipeline subsystems
│   │   │   ├── ingestion.py      FFmpeg audio extraction (Subsystem 1)
│   │   │   ├── transcription.py  Whisper word-level timestamps (2)
│   │   │   ├── curation.py       Claude semantic curation (3)
│   │   │   ├── reframing.py      MediaPipe face tracking + smoothing (4)
│   │   │   ├── captioning.py     Word JSON -> .ass kinetic captions (5)
│   │   │   └── rendering.py      Single-pass FFmpeg render (6)
│   │   ├── workers/              Celery task orchestrating all six stages
│   │   ├── models.py             SQLAlchemy ORM (Video, Job, Clip)
│   │   ├── schemas.py            Pydantic v2 payload schemas
│   │   ├── config.py             Environment-driven settings
│   │   ├── database.py           DB init + session factory
│   │   └── main.py               FastAPI app entry
│   ├── scripts/
│   │   └── transcribe_cli.py     Standalone CLI for Milestone 1
│   ├── tests/                    Nine unit tests, no ML deps required
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── components/           VideoUploader, JobList, ClipGrid, ClipPreview
│       ├── hooks/                useJobs (auto-polling)
│       ├── api.ts                Typed API client
│       └── types.ts              Shared interfaces
├── docker-compose.yml            Redis + backend + worker + frontend
├── README.md
├── CLAUDE.md                     Guide for Claude Code
└── supo-c1-p_project_application_report.md
```

---

## 3. Features

### 3.1 Pipeline features

| Subsystem | Key features |
|---|---|
| **1 — Ingestion** | Multipart file uploads via REST. FFprobe-based duration detection. Extracts audio with the exact codec / sample rate Whisper prefers (16 kHz, mono, PCM s16le). |
| **2 — Transcription** | Whisper invoked with `word_timestamps=True` so every word has a `start`/`end`. Output is persisted as JSON for downstream stages and audit. Model size is configurable. |
| **3 — Curation** | Transcript chunked into 2–3-minute overlapping blocks so the LLM never loses local context. Strict JSON-only system prompt with shape validation via Pydantic. Returned timestamps are **snapped to true word boundaries** so renders never start/end mid-word. Overlapping candidates are de-duplicated, keeping the higher virality score. |
| **4 — Reframing** | Segment sampled at 5 fps, MediaPipe Face Detection picks the dominant face per frame, and a 24-frame rolling linear average smooths out jitter. Crop center is clamped so the 9:16 window never leaves the source frame. Falls back to last known center on detection gaps. |
| **5 — Captioning** | Word-level JSON converted to Advanced SubStation Alpha (`.ass`). Words grouped into readable phrases (≤40 chars, gap-aware). The currently spoken word renders in neon yellow (`#FFFF00`); neighbors in white with 3-px black outline. Text positioned in the lower-middle safe area (y=1400 on 1080×1920) to clear platform UI chrome. Typography defaults to heavy blocky sans-serif (Montserrat Black). |
| **6 — Rendering** | Single FFmpeg pass does the cropping, scaling to 1080×1920, and subtitle burn-in. Outputs H.264/AAC MP4 at CRF 18 with `fast` preset — high quality, fast encode. |

### 3.2 Application features

- **Drag/click upload** of `.mp4` / `.mov` / `.mkv` / `.webm` with type validation.
- **Async processing**: API returns immediately; heavy work runs in a Celery worker pool. Multiple jobs can run in parallel by scaling worker replicas.
- **Live job dashboard** with status badges for every pipeline stage (Extracting Audio → Transcribing → Finding Viral Hooks → Tracking Faces → Building Captions → Rendering → Completed).
- **Adaptive polling**: dashboard polls every 2 seconds while a job is active, every 8 seconds when everything is idle.
- **Per-clip preview cards** showing the predicted virality score (0–100), AI-written title, time range, reasoning ("Strong hook within first 3 seconds…"), and an inline 9:16 video player.
- **One-click download** of any rendered clip as a publish-ready MP4.
- **Full error surfacing**: pipeline exceptions are persisted on the Job and shown in the UI rather than swallowed.

### 3.3 Engineering features

- **Strict typing everywhere**: Python type hints on every function; TypeScript with `noImplicitAny: true` and an ESLint rule that errors on `any`.
- **Thin controllers**: API routes contain no business logic — every pipeline operation lives in `app/services/`.
- **Lazy heavy imports**: `cv2`, `mediapipe`, and `anthropic` import inside their consumer functions so the FastAPI app and the test suite boot in environments without those packages installed.
- **Pydantic v2 schemas** at every boundary — no raw model output is returned to the frontend untyped.
- **Unit-tested deterministic math**: 9 passing tests cover caption phrasing, transcript chunking with overlap, JSON-fence stripping, overlap deduplication, rolling-average smoothing, and crop clamping.
- **Containerized**: `docker-compose up` runs Redis, the API, the worker, and the Vite dev server. Volumes mount the media directory so renders survive container restarts.
- **CLI fallback**: `python -m scripts.transcribe_cli input.mp4` gives a standalone word-level transcript without spinning up the API — useful for batch jobs or CI.

---

## 4. Outputs

### 4.1 Per-clip artifacts

For every job, the system produces:

- **`media/job_{id}/audio.wav`** — extracted 16 kHz mono audio.
- **`media/job_{id}/transcript.json`** — full word-level transcript:
  ```json
  {
    "text": "Welcome to the future of...",
    "words": [
      { "word": "Welcome", "start": 0.12, "end": 0.45 },
      { "word": "to",      "start": 0.46, "end": 0.60 }
    ]
  }
  ```
- **`media/job_{id}/clip_{n}.ass`** — kinetic subtitle file per clip.
- **`media/job_{id}/clip_{n}.mp4`** — final 1080×1920 H.264/AAC vertical video with burned-in captions.

### 4.2 Per-clip metadata (returned from the API)

```json
{
  "id": 7,
  "title": "The Future of AI Systems",
  "start_time": 132.4,
  "end_time": 187.9,
  "virality_score": 92,
  "reasoning": "Strong hook within the first 3 seconds, ends with a complete contextual summary.",
  "rendered": true,
  "output_url": "/api/clips/7/download"
}
```

### 4.3 REST endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/videos` | Upload a long-form video. Kicks off processing. |
| `GET`  | `/api/videos` | List uploaded videos. |
| `GET`  | `/api/jobs` | List all jobs with current status + clips. |
| `GET`  | `/api/jobs/{id}` | Detail for a specific job. |
| `GET`  | `/api/clips/{id}` | Metadata for a single clip. |
| `GET`  | `/api/clips/{id}/download` | Stream the rendered MP4. |
| `GET`  | `/api/health` | Liveness check. |
| `GET`  | `/docs` | OpenAPI / Swagger UI. |

---

## 5. General use cases

### 5.1 Content creators

- **Podcasters**: turn each 60-minute episode into 8–12 vertical promo clips per release without manual editing.
- **YouTubers**: repurpose long-form videos into Shorts to feed the algorithm without doubling content production cost.
- **Streamers**: post-process VOD recordings into highlight clips with auto-captions.

### 5.2 Businesses & agencies

- **Marketing teams**: convert webinars, panel discussions, and keynotes into a continuous social media drip.
- **Sales enablement**: pull the most compelling 60-second testimonials and demo highlights out of recorded customer calls.
- **Conferences & events**: produce per-talk social cuts within minutes of a session ending instead of weeks after.
- **Agencies**: white-label the pipeline to deliver short-form content at scale per client.

### 5.3 Education & training

- **Online courses**: surface the strongest 60–90 second teasers per lecture for ads and previews.
- **Internal training**: index long training videos into searchable, captioned micro-segments.

### 5.4 Research & analysis

- **Media monitoring**: word-level transcripts + ranked-segment metadata are a structured dataset, not just videos.
- **Discovery / archiving**: the transcript JSON is full-text searchable; the curation JSON is a virality-ranked index of long archives.

---

## 6. Business benefits

### 6.1 Cost & throughput

- **Compresses an editor's workflow** that typically takes 30–60 minutes per clip down to a single upload. At 10 clips per long-form video, that is conservatively a **10×–30× reduction in editing labor cost**.
- **Increases output volume**: a single piece of long-form content becomes 5–15 distribution assets instead of one.
- **Self-hosted**: no per-clip SaaS fee. Variable cost is bounded by Whisper compute (free, local) and a small Claude API spend per video (typically tens of cents to a few dollars depending on length and model tier).

### 6.2 Revenue & distribution

- **More posts → more impressions → more top-of-funnel reach.** Short-form algorithms reward volume, which manual editing constrains.
- **Faster time-to-publish**: live event → social clips in minutes, not next week — capturing peak attention windows.
- **Multi-platform parity**: a single render targets the 9:16 spec common to TikTok, Reels, Shorts, and LinkedIn Video.

### 6.3 Strategic differentiation

- **Defensible data asset**: every processed video produces structured transcripts and ranked-segment metadata that compound into a reusable content intelligence layer (search, analytics, recommendation).
- **Editorial consistency**: caption style, safe-area placement, virality scoring, and reframing logic are codified — output is on-brand and predictable across hundreds of clips.
- **AI-native pipeline, not a wrapper**: each subsystem is owned in code, can be swapped, tuned, or extended (different LLMs, different fonts, different aspect ratios) without vendor lock-in.

### 6.4 Risk & governance

- **No third-party platform stores your raw video** — Whisper runs locally, only the transcript text is sent to Claude.
- **Reproducible**: every run is fully described by source video + commit SHA, so outputs are auditable.
- **Transparent ranking**: every clip ships with the LLM's `reasoning` field, so editors can see *why* a segment was chosen.

---

## 7. Quality & operations

- **Container-first deployment**: `docker compose up` brings the entire stack online (Redis, API, worker, frontend) on Windows, macOS, or Linux.
- **Configuration via environment** only — no code change required for model size, output dimensions, smoothing window, chunk size, or storage location.
- **Horizontal scaling**: the API is stateless; the work queue is Celery; add worker replicas to scale throughput linearly.
- **Storage agnostic**: `MEDIA_ROOT` can be a local mount, an NFS share, or an S3-mounted volume.
- **Database portable**: SQLite by default for zero-config dev; swap to Postgres by changing `DATABASE_URL`.

---

## 8. Roadmap (suggested next iterations)

| Theme | Idea |
|---|---|
| **Quality** | B-roll insertion; speaker diarization; multi-speaker reframing (smart split-screen). |
| **Distribution** | One-click publish to TikTok / Reels / Shorts via their respective APIs. |
| **Curation** | Style presets ("educational", "comedy", "controversy") that tune the curation prompt. |
| **Analytics** | Track which AI-predicted scores correlate with real-world engagement per platform — feed back into the prompt. |
| **Caption polish** | Word-level emphasis ("bigger" for stressed syllables), emoji insertion, multi-line phrase wrapping. |
| **Performance** | GPU Whisper (`whisper.cpp` or `faster-whisper`) for ~10× transcription speedup. |
| **Multi-tenant** | Auth, per-tenant storage prefixes, per-tenant API quotas. |

---

## 9. Status

| Milestone | Status |
|---|---|
| M1: FFmpeg + Whisper word-level CLI | ✅ Complete |
| M2: Claude JSON curation with word-boundary snapping | ✅ Complete |
| M3: MediaPipe face tracking with rolling-average smoothing | ✅ Complete |
| M4: Word-level JSON → `.ass` kinetic captions | ✅ Complete |
| M5: Async FastAPI workflow + React dashboard | ✅ Complete |
| Unit tests (deterministic math) | ✅ 9 passing |
| Docker-compose stack | ✅ Running on Windows 11 + Docker Desktop |

---

*Built collaboratively via the linked Gemini design conversation and Claude Code. Source of truth: `jeff0926/supo-c1-p` @ `claude/new-session-aK45l`.*
