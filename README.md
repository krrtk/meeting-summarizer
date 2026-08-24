# link to demo: https://youtu.be/b8SwDVfkN2A
In this demo I have use two audio file for reference:

1)priya_rahul_alex_meet.wav for showing how my webappp works when multiple people are in a meeting, for that case all the key decisions, summary etc... were working.

2)not_meeting_but_conversation.wav for a casual conversation where no formal meeting setting is there and hence no key decisions, deadlines etc. is there thus showing webapp doesn't halucinate, it only provides legit information that is uploaded to it
# AI Meeting Summarizer
Upload a meeting audio recording and get back a structured summary: key decisions, action items, open questions, and next steps — powered by Groq Whisper (transcription) and an LLM (extraction).

---

## Prerequisites

| Tool | Minimum version | Notes |
|------|-----------------|-------|
| Python | 3.11+ | 3.14 tested |
| Node.js | 18+ | 22 LTS recommended |
| npm | 9+ | or pnpm |
| [Groq API key](https://console.groq.com) | — | Free tier is sufficient |

---

## Project layout

```
.
├── backend/          # FastAPI + SQLAlchemy + Groq
│   ├── app/
│   │   ├── api/          meetings.py  – REST endpoints
│   │   ├── core/         config.py, errors.py
│   │   ├── models/       meeting.py, database.py
│   │   ├── prompts/      meeting_extraction.py
│   │   ├── repositories/ meeting_repository.py
│   │   ├── schemas/      meeting.py
│   │   └── services/     audio_service.py, transcription_service.py, summarization_service.py
│   ├── requirements.txt
│   └── main.py
├── frontend/         # Next.js 16 + Tailwind CSS
│   ├── app/
│   ├── components/   meeting-summarizer.tsx  – single-page UI
│   └── lib/          meeting-api.ts          – typed API client
├── tests/            # pytest test suite (16 tests)
├── .env.example      # copy → .env and fill in GROQ_API_KEY
└── README.md
```

---

## Local setup

### 1. Clone and configure environment

```bash
git clone <repo-url>
cd "Unthinkable_meeting summarizer"

# Copy the example env file and add your Groq API key
cp .env.example .env
# Edit .env and set:  GROQ_API_KEY=gsk_...
```

> **Important:** `.env` is gitignored and must **never** be committed.

---

### 2. Backend

```bash
cd backend

# Create and activate a virtual environment
python -m venv myenv
# Windows
myenv\Scripts\activate
# macOS / Linux
source myenv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start the development server (auto-reloads on file changes)
uvicorn app.main:app --reload
```

The API is now available at **http://localhost:8000**.

- Health check: `GET http://localhost:8000/api/health`
- API docs (Swagger): `http://localhost:8000/docs`

> **SQLite:** The database file (`meeting_summarizer.db`) is created automatically in the directory where you run `uvicorn`. No migration step is required.

---

### 3. Frontend

Open a new terminal:

```bash
cd frontend
npm install
npm run dev
```

The UI is now available at **http://localhost:3000**.

---

### 4. Run the test suite

From the project root (with the virtualenv active):

```bash
backend\myenv\Scripts\python.exe -m pytest tests/test_api.py -v
# or on macOS/Linux:
backend/myenv/bin/python -m pytest tests/test_api.py -v
```

Expected: **16 passed**.

---

## Environment variables reference

All variables live in `.env` at the project root and are loaded by both the backend (`pydantic-settings`) and the frontend (`NEXT_PUBLIC_*` variables are automatically picked up by Next.js at build/dev time).

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GROQ_API_KEY` | ✅ | — | Your Groq API key. Without a real key the services return canned mock data. |
| `GROQ_TRANSCRIPTION_MODEL` | No | `whisper-large-v3-turbo` | Groq Whisper model for audio-to-text. |
| `GROQ_LLM_MODEL` | No | `openai/gpt-oss-120b` | Chat model used for meeting extraction/summarization. |
| `MAX_AUDIO_SIZE_MB` | No | `100` | Maximum upload size enforced server-side. |
| `DATABASE_URL` | No | `sqlite:///./meeting_summarizer.db` | SQLAlchemy connection string. SQLite is the default; swap for Postgres in production. |
| `FRONTEND_ORIGIN` | No | `http://localhost:3000` | Allowed CORS origin for the FastAPI backend. |
| `NEXT_PUBLIC_API_BASE_URL` | No | `http://localhost:8000` | Base URL the browser uses to reach the backend. |

---

## API reference

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/health` | Liveness check — returns `{"status": "ok"}` |
| `POST` | `/api/meetings` | Upload audio file; returns `{id, status}` immediately |
| `GET` | `/api/meetings` | List all meetings (transcript omitted for performance) |
| `GET` | `/api/meetings/{id}` | Full meeting detail including transcript and extraction |

### POST /api/meetings

- **Content-Type:** `multipart/form-data`
- **Field:** `file` — audio file (MP3, WAV, M4A, MP4, OGG, WEBM; ≤ 100 MB)
- Returns `{"id": 1, "status": "processing"}` immediately.
- Processing happens in a background task. Poll `GET /api/meetings/{id}` until `status` is `"completed"` or `"failed"`.

### Error shape

```json
{
  "detail": {
    "code": "INVALID_AUDIO",
    "message": "Human-readable description."
  }
}
```

Error codes: `INVALID_AUDIO`, `FILE_TOO_LARGE`, `TRANSCRIPTION_FAILED`, `LLM_FAILED`, `INVALID_LLM_OUTPUT`, `MEETING_NOT_FOUND`.

---

## Supported audio formats

MP3, WAV, M4A, MP4, OGG, WEBM — maximum 100 MB.

---

## Architecture

```
Browser
  │  multipart/form-data upload
  ▼
FastAPI  ──► audio_service: validate + save temp file
  │  immediate response {id, status: processing}
  ▼
BackgroundTask
  ├─ transcription_service  ──► Groq Whisper API  ──► plain text transcript
  └─ summarization_service  ──► Groq LLM API      ──► structured JSON (MeetingExtraction)
        │
        └─ SQLite via SQLAlchemy  ──► meeting record (status: completed/failed)

Browser polls GET /api/meetings/{id} every 2 s until status changes.
```

---

## Notes

- **No migrations:** SQLAlchemy `Base.metadata.create_all()` runs on every startup. It is idempotent — safe to restart the server at any time.
- **Mock mode:** If `GROQ_API_KEY` is missing or set to `mock-key-for-local-testing`, both services return hardcoded fixture data so you can test the UI without API credits.
- **Temp files:** Audio uploads are written to `scratch/temp_audio/` (relative to the project root) and deleted after processing.
