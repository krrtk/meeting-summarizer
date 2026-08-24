# Meeting Summarizer — Master Project Specification

## 1. Project Overview

Build a small, polished AI Meeting Summarizer MVP.

The goal is **not** to build an enterprise or market-level product. The goal is to build a reliable, clean, well-structured MVP that is strong enough to pass a first-round evaluation and provides good technical discussion points during interviews.

The application accepts meeting audio, transcribes it using an ASR API, extracts structured meeting intelligence with an LLM, validates the result, stores it in SQLite, and presents the result through a simple React frontend.

---

## 2. Assignment Requirements

The application must:

1. Accept meeting audio files.
2. Transcribe audio using an ASR API.
3. Generate:
   - meeting summary
   - key decisions
   - action items
   - responsible person when identifiable
   - deadlines when explicitly mentioned
   - unresolved/open questions
   - next steps
4. Provide a simple frontend for uploading audio and viewing results.
5. Have a clean backend.
6. Use an LLM effectively.
7. Have good prompt design.
8. Have basic error handling and validation.
9. Have a clean GitHub repository and README.
10. Be easy for the developer to explain in an interview.

---

## 3. Scope and Engineering Philosophy

Optimize for:

- correctness
- simplicity
- maintainability
- reliability for normal meeting audio
- demo quality
- interview explainability

Do **not** optimize for:

- enterprise-scale infrastructure
- distributed systems
- high concurrency
- complex deployment
- unnecessary abstractions

### Explicit scope constraints

Do not introduce the following unless a concrete requirement makes them necessary:

- Kubernetes
- microservices
- Kafka
- Redis
- Celery/background job infrastructure
- message queues
- vector databases
- authentication/user management
- RAG
- complex observability stacks

If a change to the architecture appears necessary, explain the reason and propose the change before implementation. Do not independently redesign the architecture.

---

# 4. Technology Stack

## Frontend

- React
- Vite
- Tailwind CSS

## Backend

- Python
- FastAPI
- Pydantic

## Database

- SQLite

## ASR

Use the current OpenAI speech-to-text API available during implementation.

Preferred starting model:

- `gpt-4o-mini-transcribe`

Alternative when implementation requirements or current API availability make it more appropriate:

- another currently supported OpenAI speech-to-text model

The exact model name must be configurable through an environment variable.

## LLM

Use the current OpenAI API available during implementation, preferably through the Responses API with Structured Outputs.

The exact model name must be configurable through an environment variable.

## Validation

- Pydantic

## Deployment

Keep deployment simple. Local development must be the primary target.

---

# 5. Final Architecture

The intended architecture is:

```text
                         ┌─────────────────────┐
                         │     React + Vite    │
                         │     Tailwind CSS    │
                         └──────────┬──────────┘
                                    │
                             POST /meetings
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │       FastAPI       │
                         │                     │
                         │  API / Validation   │
                         └──────────┬──────────┘
                                    │
                        ┌───────────┴───────────┐
                        ▼                       ▼
                ┌──────────────┐       ┌──────────────┐
                │ Audio Service│       │ SQLite       │
                │              │       │ Repository   │
                └──────┬───────┘       └──────────────┘
                       │
                       ▼
                OpenAI Speech-to-Text
                       │
                       ▼
                    Transcript
                       │
              preprocessing/chunking
                       │
                       ▼
                OpenAI Responses API
                 Structured Outputs
                       │
                       ▼
                Pydantic validation
                       │
                       ▼
                 SQLite persistence
                       │
                       ▼
                 GET /meetings/{id}
                       │
                       ▼
                    Frontend
```

## Processing flow

```text
Audio Upload
→ FastAPI
→ Audio validation
→ ASR
→ Transcript
→ Transcript preprocessing/chunking when required
→ LLM structured extraction
→ Pydantic validation
→ SQLite persistence
→ Frontend results
```

For the MVP, processing may be synchronous. Do not add job queues or worker infrastructure unless the architecture is explicitly changed and justified.

---

# 6. Repository / Folder Structure

Use the following structure unless a small implementation detail requires a clearly justified adjustment:

```text
meeting-summarizer/
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   │
│   │   ├── api/
│   │   │   └── meetings.py
│   │   │
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   └── errors.py
│   │   │
│   │   ├── models/
│   │   │   ├── database.py
│   │   │   └── meeting.py
│   │   │
│   │   ├── schemas/
│   │   │   └── meeting.py
│   │   │
│   │   ├── services/
│   │   │   ├── audio_service.py
│   │   │   ├── transcription_service.py
│   │   │   └── summarization_service.py
│   │   │
│   │   ├── repositories/
│   │   │   └── meeting_repository.py
│   │   │
│   │   └── prompts/
│   │       └── meeting_extraction.py
│   │
│   ├── requirements.txt
│   └── meeting_summarizer.db
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── AudioUploader.jsx
│   │   │   ├── LoadingState.jsx
│   │   │   ├── MeetingSummary.jsx
│   │   │   └── ActionItems.jsx
│   │   │
│   │   ├── services/
│   │   │   └── api.js
│   │   │
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── index.css
│   │
│   ├── package.json
│   └── vite.config.js
│
├── tests/
│   ├── test_validation.py
│   ├── test_prompt_output.py
│   └── test_api.py
│
├── README.md
├── project_spec.md
├── .env.example
└── .gitignore
```

## Responsibility boundaries

- `api/`: HTTP routes and request/response handling.
- `services/`: business logic and external API integration.
- `repositories/`: database persistence and retrieval.
- `schemas/`: Pydantic request/response/data validation.
- `models/`: database models and DB setup.
- `prompts/`: LLM instructions and extraction prompt.
- `core/`: configuration and shared application errors.

Keep modules small and understandable.

---

# 7. API Contract

The frontend must only depend on the documented backend API. It must not know anything about OpenAI internals.

## 7.1 POST `/api/meetings`

Uploads an audio file and processes it.

### Request

```http
Content-Type: multipart/form-data

file: <audio-file>
```

### Success response

```json
{
  "id": 1,
  "status": "completed"
}
```

Recommended implementation behavior:

```text
upload
→ validate
→ persist initial record
→ transcribe
→ extract
→ validate output
→ persist final result
→ return status
```

For the MVP, this endpoint can process synchronously.

## 7.2 GET `/api/meetings/{meeting_id}`

Returns a processed meeting.

Example:

```json
{
  "id": 1,
  "filename": "team_meeting.mp3",
  "status": "completed",
  "transcript": "Alice: ...",
  "result": {
    "meeting_title": "Product Planning Meeting",
    "summary": "The team discussed...",
    "key_decisions": [
      "Launch beta in September"
    ],
    "action_items": [
      {
        "task": "Prepare beta documentation",
        "owner": "Alice",
        "deadline": "September 10",
        "priority": "high"
      }
    ],
    "open_questions": [
      "Who will handle customer support?"
    ],
    "next_steps": [
      "Review beta readiness next week"
    ]
  }
}
```

## 7.3 GET `/api/meetings`

Optional but recommended for a polished demo.

Example:

```json
[
  {
    "id": 1,
    "filename": "team_meeting.mp3",
    "status": "completed",
    "created_at": "2026-08-23T13:20:00"
  }
]
```

## 7.4 GET `/api/health`

Return:

```json
{
  "status": "ok"
}
```

---

# 8. Error Contract

Use one predictable shape for application errors:

```json
{
  "detail": {
    "code": "INVALID_AUDIO",
    "message": "Unsupported audio format."
  }
}
```

Recommended application error codes:

```text
INVALID_AUDIO
FILE_TOO_LARGE
TRANSCRIPTION_FAILED
LLM_FAILED
INVALID_LLM_OUTPUT
MEETING_NOT_FOUND
PROCESSING_FAILED
```

Do not expose raw provider/API exceptions to the frontend.

---

# 9. Database Schema

Use a simple SQLite design.

## `meetings`

| Column | Type | Purpose |
|---|---|---|
| `id` | INTEGER PK | Meeting ID |
| `filename` | TEXT | Original filename |
| `status` | TEXT | processing / completed / failed |
| `transcript` | TEXT | Raw transcript |
| `result_json` | TEXT | Validated structured extraction |
| `error_message` | TEXT NULL | Internal/user-safe failure description |
| `created_at` | DATETIME | Creation time |
| `updated_at` | DATETIME | Last update |

## Database design decision

Do not create separate relational tables for:

- action items
- key decisions
- questions
- owners
- deadlines

For this MVP, store the validated structured result as JSON in `result_json`.

Reason:

- the result is naturally hierarchical
- there is no requirement for independent querying/editing of each action item
- a single-meeting read is the main use case
- it keeps the implementation small
- it avoids unnecessary relational complexity

Interview explanation:

> Because the extracted meeting information is hierarchical and the application does not need independent querying or editing of action items, I stored the validated structured result as JSON rather than introducing unnecessary relational complexity.

---

# 10. LLM Output Schema

The LLM must return exactly this conceptual structure:

```json
{
  "meeting_title": "",
  "summary": "",
  "key_decisions": [],
  "action_items": [
    {
      "task": "",
      "owner": null,
      "deadline": null,
      "priority": null
    }
  ],
  "open_questions": [],
  "next_steps": []
}
```

Recommended Pydantic models:

```python
class ActionItem(BaseModel):
    task: str
    owner: str | None
    deadline: str | None
    priority: str | None


class MeetingExtraction(BaseModel):
    meeting_title: str
    summary: str
    key_decisions: list[str]
    action_items: list[ActionItem]
    open_questions: list[str]
    next_steps: list[str]
```

The implementation may strengthen field constraints where appropriate, provided the required output contract remains compatible.

---

# 11. LLM Grounding Rules

The LLM must **never invent**:

- names
- responsible people
- deadlines
- decisions
- action items
- commitments
- priorities

## Owner rule

If a responsible person is not explicitly identifiable:

```json
"owner": null
```

## Deadline rule

If a deadline is not explicitly mentioned:

```json
"deadline": null
```

## Priority rule

Only populate priority when the transcript explicitly indicates priority or urgency.

Otherwise:

```json
"priority": null
```

## Classification rule

A discussion, suggestion, possibility, or opinion must not automatically become:

- a decision
- an action item
- a commitment

Distinguish clearly between:

- decision
- action item
- open question
- next step

Prefer omission over invention.

---

# 12. Prompt Design Requirements

The meeting extraction prompt should be evidence-constrained rather than a generic "summarize this meeting" prompt.

Core behavior:

```text
Extract only information supported by the transcript.

Never infer:
- people
- ownership
- deadlines
- decisions
- tasks
- commitments

Use null when an owner, deadline, or priority is not explicitly identifiable.

A discussion, suggestion, possibility, or unresolved topic must not
automatically become a decision or action item.

Distinguish:
- decision
- action item
- open question
- next step

Prefer omission over invention.
```

The final prompt should also instruct the model to:

- treat the transcript as the only source of truth
- preserve meaningful dates/deadlines as stated
- avoid inventing context not present in the transcript
- produce concise but useful summaries
- return only the requested structured output
- avoid duplicate action items and decisions

The prompt should be stored separately from application code in:

```text
backend/app/prompts/meeting_extraction.py
```

---

# 13. Structured Output Strategy

Do not rely on free-form text followed by manual JSON parsing if Structured Outputs are available.

Preferred pipeline:

```text
Transcript
   ↓
OpenAI Responses API
   ↓
Structured Outputs
   ↓
Pydantic validation
   ↓
SQLite
```

Do not save unvalidated model output directly to the database.

If a structured response is missing required information or cannot be parsed/validated, treat it as an application failure rather than silently accepting malformed data.

---

# 14. Transcript Processing and Chunking

Normal meeting transcripts should be processed with the simplest possible approach.

## Normal-size transcript

```text
Transcript
   ↓
Single extraction request
```

## Large transcript

If the transcript is too large for a safe single model request:

```text
Transcript
   ↓
Split into chunks
   ↓
Extract structured information per chunk
   ↓
Combine chunk-level information
   ↓
Final consolidation
   ↓
Pydantic validation
```

Do not introduce RAG, vector databases, embeddings, or retrieval infrastructure for this problem unless a later requirement clearly demands it.

Chunking should be deterministic and easy to explain.

---

# 15. Audio Validation

Validate the upload before calling external APIs.

Minimum checks:

- file exists
- supported file format
- reasonable content type
- maximum file size
- safe filename handling

Supported common formats can include:

```text
mp3
wav
m4a
mp4
ogg
webm
```

Keep the maximum size configurable:

```text
MAX_AUDIO_SIZE_MB=100
```

Do not rely exclusively on the extension supplied by the client.

---

# 16. Configuration and Secrets

Never hardcode secrets.

Use environment variables.

Recommended `.env.example`:

```env
OPENAI_API_KEY=
OPENAI_TRANSCRIPTION_MODEL=gpt-4o-mini-transcribe
OPENAI_LLM_MODEL=<current-compatible-model>
MAX_AUDIO_SIZE_MB=100
DATABASE_URL=sqlite:///./meeting_summarizer.db
FRONTEND_ORIGIN=http://localhost:5173
```

The exact default model values may change during implementation if the current OpenAI API offers a better supported choice.

The application must read configuration from environment variables through a dedicated configuration module.

---

# 17. Frontend / Backend Data Contract

The frontend must interact only with the backend API.

## Upload flow

```text
Frontend
   │
   │ multipart/form-data
   ▼
POST /api/meetings
   │
   ▼
{ id, status }
   │
   ▼
GET /api/meetings/{id}
   │
   ▼
Complete meeting result
```

## Frontend states

Keep the state model minimal:

```text
idle
uploading
processing
success
error
```

The frontend should not know:

- which ASR model is used
- which LLM model is used
- how prompts work
- how SQLite is structured
- how OpenAI is called

---

# 18. Frontend UI Requirements

The frontend should be simple, clean, responsive, and demo-friendly.

## Initial screen

```text
┌──────────────────────────────────────┐
│        AI Meeting Summarizer         │
│                                      │
│     [ Upload Meeting Audio ]         │
│                                      │
│       Supported: MP3, WAV, M4A      │
└──────────────────────────────────────┘
```

## Result screen

Display:

```text
Meeting Title

Summary
──────────────────────────

Key Decisions
• ...
• ...

Action Items
┌──────────────┬────────┬──────────┐
│ Task         │ Owner  │ Deadline │
├──────────────┼────────┼──────────┤
│ ...          │ Alice  │ Friday   │
└──────────────┴────────┴──────────┘

Open Questions
• ...

Next Steps
• ...
```

Design goals:

- readable typography
- clear hierarchy
- useful spacing
- obvious upload control
- clear loading state
- clear error state
- mobile-friendly layout

Do not build:

- user accounts
- dashboards with complex analytics
- notifications
- collaborative editing
- meeting calendar integrations
- real-time transcription
- complex settings pages

---

# 19. Error Handling Strategy

Handle errors at every boundary.

## Upload boundary

Possible failures:

- missing file
- unsupported format
- oversized file

Return a user-safe API error.

## Transcription boundary

Catch:

- provider errors
- network failures
- timeouts
- rate limits

Map them to:

```text
TRANSCRIPTION_FAILED
```

## LLM boundary

Catch:

- provider/API failures
- network failures
- timeouts
- rate limits
- invalid structured output

Map them appropriately to:

```text
LLM_FAILED
INVALID_LLM_OUTPUT
```

## Persistence boundary

If database persistence fails:

```text
PROCESSING_FAILED
```

Log the underlying technical exception server-side.

## Frontend boundary

Show a human-readable message such as:

```text
The audio file is too large.
```

or:

```text
Transcription failed. Please try again.
```

Never display raw stack traces in the UI.

---

# 20. Logging

Keep logging simple.

Useful events:

- upload received
- validation failure
- transcription started/completed/failed
- extraction started/completed/failed
- database persistence failure
- request failures

Do not log:

- API keys
- secrets
- unnecessary sensitive audio contents

Avoid building a complex observability platform for this MVP.

---

# 21. Testing Strategy

Do not aim for 100% coverage.

Test the parts where failures would affect correctness or the demo.

## 21.1 Audio validation tests

Test:

```text
valid MP3 → accepted
valid WAV → accepted
unsupported file → rejected
oversized file → rejected
missing file → rejected
```

## 21.2 Pydantic validation tests

Test:

```text
valid extraction → accepted
missing required field → rejected
null owner → accepted
null deadline → accepted
null priority → accepted
```

## 21.3 API tests

Test:

```text
GET /api/health
POST /api/meetings
GET /api/meetings/{id}
missing meeting → 404
invalid audio → appropriate 4xx
```

## 21.4 LLM service tests

Mock the OpenAI client in ordinary unit tests.

Test:

```text
valid structured response
invalid response
provider/API exception
```

Avoid requiring a live OpenAI API call for the normal test suite.

## 21.5 Prompt regression test

Use a fixed transcript such as:

```text
Alice: We will launch on September 10.
Bob: I'll prepare the deployment guide by Friday.
Charlie: We still need to decide which payment provider to use.
```

Expected extraction semantics:

```text
decision:
  launch on September 10

action item:
  task: prepare the deployment guide
  owner: Bob
  deadline: Friday

open question:
  which payment provider to use
```

This test should verify that the extraction behavior matches the evidence in the transcript.

---

# 22. Implementation Order

Implement in the following sequence.

## Phase 1 — Backend foundation

1. FastAPI application
2. configuration
3. SQLite connection
4. meeting model
5. Pydantic schemas
6. health endpoint

Goal:

```text
GET /api/health
→ {"status": "ok"}
```

## Phase 2 — Upload pipeline

Implement:

```text
POST /api/meetings
→ validate audio
→ create meeting record
```

Do not add AI yet.

## Phase 3 — Transcription

Add:

```text
Audio service
Transcription service
```

Flow:

```text
Upload
→ validate
→ transcription API
→ save transcript
```

## Phase 4 — LLM extraction

Add:

```text
MeetingExtraction schema
Extraction prompt
Summarization service
```

Flow:

```text
Transcript
→ preprocess
→ LLM
→ structured output
→ Pydantic validation
→ save result
```

## Phase 5 — Large transcript handling

Implement simple deterministic chunking only when necessary.

## Phase 6 — Frontend

Implement:

```text
Upload
Loading
Results
Errors
```

Then polish visual design.

## Phase 7 — Tests

Add the critical backend, validation, API, and prompt regression tests.

## Phase 8 — README / GitHub polish

Complete documentation and add a screenshot/GIF of the working application.

---

# 23. README Requirements

The final `README.md` must explain:

1. Problem
2. Features
3. Architecture
4. Tech stack
5. Setup
6. Environment variables
7. API endpoints
8. AI pipeline
9. Design decisions
10. Limitations
11. Future improvements

It should also include:

- a concise project description
- local setup commands
- frontend/backend startup instructions
- a sample API flow
- screenshots once available

The README should be written for both evaluators and developers.

---

# 24. Design Decisions to Preserve

These decisions should remain explicit unless implementation evidence requires change:

### 24.1 Monolithic backend

Use one FastAPI application instead of microservices.

Reason: the project is small, and a modular monolith is sufficient.

### 24.2 SQLite

Use SQLite instead of PostgreSQL for the MVP.

Reason: easy local setup and more than adequate for the intended scope.

### 24.3 Structured Outputs

Use structured LLM output plus Pydantic validation.

Reason: minimizes parsing fragility and makes the data contract explicit.

### 24.4 Synchronous processing

Process an uploaded meeting in a single request for the MVP.

Reason: simplest reliable implementation for normal-sized demo files.

### 24.5 JSON storage for extraction

Store the validated extraction as JSON instead of normalizing every field into separate relational tables.

Reason: preserves the hierarchical structure and reduces unnecessary database complexity.

### 24.6 Configurable OpenAI models

Model names must come from environment configuration.

Reason: provider model availability can change without requiring an architectural rewrite.

### 24.7 No automatic inference

The system must prefer `null` or omission over unsupported assumptions.

Reason: hallucinated names, deadlines, decisions, and action ownership are especially harmful in meeting summaries.

---

# 25. Limitations

The MVP should explicitly acknowledge:

- synchronous processing may not be ideal for very long meetings
- transcription quality depends on recording quality and speaker clarity
- speaker identification is limited unless diarization is explicitly used
- LLM extraction can still make mistakes despite structured output and grounding rules
- deadline normalization is intentionally conservative
- SQLite is not intended for production-scale concurrent workloads
- the application does not include authentication or multi-user access

Do not hide these limitations. They are useful interview discussion points.

---

# 26. Future Improvements

Potential future improvements, outside the MVP scope:

- asynchronous processing with a job queue
- speaker diarization
- authenticated users
- persistent cloud storage
- PostgreSQL
- searchable meeting history
- editable action items
- notifications/reminders
- calendar integration
- confidence scores
- better date normalization
- streaming transcription
- richer analytics

These should remain future work unless explicitly required.

---

# 27. Security / Reliability Basics

Minimum requirements:

- never hardcode API keys
- keep `.env` out of Git
- validate uploaded files
- enforce file-size limits
- sanitize/avoid unsafe filename usage
- do not expose raw provider exceptions
- validate all structured AI output
- avoid logging secrets
- avoid trusting client-provided MIME type blindly

The MVP does not need a full enterprise security program, but basic defensive engineering is mandatory.

---

# 28. GitHub Requirements

The repository should contain:

```text
README.md
project_spec.md
.gitignore
.env.example
backend/
frontend/
tests/
```

Do not commit:

```text
.env
API keys
large raw audio files
private credentials
local caches
node_modules/
Python virtual environments
build artifacts
```

The Git history should preferably contain small, understandable commits such as:

```text
initialize FastAPI backend
add meeting schema and SQLite repository
add audio validation
integrate transcription
add structured LLM extraction
add frontend upload flow
add result UI
add tests
document project
```

---

# 29. Definition of Done

The project is complete when all of the following are true:

### Backend

- FastAPI starts successfully.
- `/api/health` works.
- Audio upload works.
- Audio validation works.
- Transcription works using the configured OpenAI ASR model.
- Structured extraction works using the configured OpenAI LLM.
- Pydantic validates the extraction.
- Results persist in SQLite.
- Meeting retrieval works.
- Errors are handled predictably.

### Frontend

- React app starts successfully.
- Audio upload is simple and clear.
- Loading/processing state is visible.
- Results are clearly presented.
- Errors are understandable.
- Layout is responsive and visually polished enough for a demo.

### Tests

- critical validation tests pass
- API tests pass
- LLM service tests use mocks
- prompt regression test exists

### Documentation

- README is complete
- project architecture is documented
- setup steps work from a clean environment
- `.env.example` is present
- no secrets are committed

---

# 30. Recommended Interview Explanation

The project should be explainable in approximately 60–90 seconds:

> I built a modular AI meeting summarizer as a FastAPI backend with a React frontend and SQLite persistence. The user uploads meeting audio, the backend validates it and sends it to an OpenAI speech-to-text model. The transcript is then passed through a carefully constrained extraction prompt using the OpenAI Responses API with structured outputs. The resulting meeting summary, decisions, action items, owners, deadlines, open questions, and next steps are validated with Pydantic before being stored in SQLite. I intentionally kept the architecture simple and avoided queues, microservices, and unnecessary infrastructure because this is an MVP. The main reliability concern I focused on was preventing hallucinated meeting commitments, so the prompt explicitly requires evidence from the transcript and uses null when ownership or deadlines are not actually stated.

This explanation should match the implementation exactly.

---

# 31. Agent Instructions

Any coding agent working from this specification must follow these rules:

1. Treat this document as the primary implementation specification.
2. Do not independently redesign the architecture.
3. Prefer the simplest correct implementation.
4. Do not add infrastructure without a concrete reason.
5. Preserve the documented API and data contracts unless a change is proposed and justified.
6. Keep OpenAI model names configurable.
7. Never hardcode secrets.
8. Validate all external input.
9. Validate all LLM output with Pydantic.
10. Prefer omission/null over model inference.
11. Keep code modular but not over-engineered.
12. Write useful comments only where they improve understanding.
13. Add tests for critical functionality.
14. Update README when implementation behavior changes.
15. Make the application easy to run locally.
16. Keep the frontend/backend contract explicit.
17. Do not optimize for enterprise scale.
18. Optimize for correctness, simplicity, maintainability, and demo quality.

---

# 32. Final MVP Boundary

The final system should effectively be:

```text
React
  ↓
FastAPI
  ↓
Audio validation
  ↓
OpenAI Speech-to-Text
  ↓
Transcript preprocessing
  ↓
OpenAI Responses API
  ↓
Structured Outputs
  ↓
Pydantic validation
  ↓
SQLite
  ↓
React results
```

Keep the implementation inside this boundary unless a change is explicitly proposed and justified.
