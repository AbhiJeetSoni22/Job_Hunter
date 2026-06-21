# Project Status

**Project:** AI Internship Hunter
**Type:** Personal use · Single-user · No auth · No SaaS
**Goal:** Automate internship discovery, AI-powered scoring, and application tracking

---

## Problem Statement

Internship hunting is manual and unstructured. Browsing job boards, reading descriptions, comparing them to your resume, and tracking what you applied to — all of it happens across browser tabs and spreadsheets. Good opportunities get missed, weak ones get time, and the process is slower than it needs to be.

---

## MVP Goal

A personal tool that:
1. Collects internship listings from RemoteOK and YC Jobs
2. Scores each job against your resume using Gemini AI
3. Tracks application status per job

Secondary: portfolio-quality code that demonstrates full-stack dev, AI integration, web scraping, FastAPI architecture, and PostgreSQL design.

---

## Current Architecture

```
Browser (Next.js 15)
        │
        │ HTTP/JSON
        ▼
FastAPI Backend (Python 3.12)
        ├── routers/        ← HTTP only, thin
        ├── services/       ← all business logic
        ├── scrapers/       ← source adapters
        ├── models/         ← SQLAlchemy ORM
        ├── schemas/        ← Pydantic v2
        └── ai/             ← Gemini client (Phase 2)
        │
        ▼
PostgreSQL 16
        ├── jobs
        ├── resumes
        └── scrape_runs
```

**Key design rules:**
- Routers never query the DB directly
- Services own all business logic
- Scrapers fetch and normalise only — never touch the DB
- One ScrapeRun row per source per sync
- Single active resume at any time; replaced on upload

---

## Current Folder Structure

```
ai-internship-hunter/
├── docker-compose.yml
├── .env.example
├── docs/
│   ├── PRD.md
│   ├── DATABASE.md
│   ├── API_SPEC.md
│   ├── ARCHITECTURE.md
│   ├── TASKS.md
│   ├── PROMPTS.md
│   └── PROJECT_STATUS.md       ← this file
└── backend/
    ├── pyproject.toml
    ├── alembic.ini
    ├── alembic/
    │   ├── env.py
    │   ├── script.py.mako
    │   └── versions/
    │       └── cc9c2e74a08d_initial_schema.py
    └── app/
        ├── main.py
        ├── config.py
        ├── database.py
        ├── dependencies.py
        ├── models/
        │   ├── __init__.py
        │   ├── job.py
        │   ├── resume.py
        │   └── scrape_run.py
        ├── schemas/
        │   ├── __init__.py
        │   ├── job.py
        │   └── resume.py               ← Phase 1D
        ├── routers/
        │   ├── __init__.py
        │   ├── health.py
        │   ├── jobs.py
        │   ├── scraper.py
        │   └── resume.py               ← Phase 1D
        ├── services/
        │   ├── __init__.py
        │   ├── job_service.py
        │   ├── scraper_service.py
        │   └── resume_service.py       ← Phase 1D
        ├── scrapers/
        │   ├── __init__.py
        │   ├── base.py
        │   ├── remoteok.py             ← real implementation
        │   └── yc_jobs.py              ← stub (Phase 1E)
        └── ai/
            ├── __init__.py
            ├── gemini_client.py        ← Phase 2A ✅
            └── prompts.py              ← Phase 2A ✅
```

---

## Completed Phases

### ✅ Phase 0A — Backend Foundation
- FastAPI app factory with CORS and global exception handler
- PostgreSQL 16 via Docker Compose
- SQLAlchemy 2.x engine with connection pooling
- Alembic configured; `env.py` reads DB URL from pydantic-settings
- `GET /api/health` endpoint with DB connectivity check
- Typed `Settings` class via pydantic-settings
- `DbSession` dependency alias for all routers

### ✅ Phase 1A — Database Layer
- `Job` ORM model: 18 columns, 3 indexes + unique constraint on URL
- `Resume` ORM model: 5 columns, JSONB skills array
- `ScrapeRun` ORM model: 7 columns, composite index on source+started_at
- `app/models/__init__.py` as model registry (required for Alembic autogenerate)
- `alembic/env.py` updated to import `app.models` before inspecting metadata
- Initial migration `cc9c2e74a08d_initial_schema.py` applied and verified

### ✅ Phase 1B — Service and Router Layer
- `schemas/job.py`: `JobListItem`, `JobResponse`, `JobUpdateRequest`, `JobUpdateResponse`, `JobUpsertData`, `PaginatedJobList`, `ScrapeRunResponse`, `ScraperRunSummary`, `ScoreResult`, `ApiResponse[T]`, `ApiError`
- `services/job_service.py`: `list_jobs()`, `get_job()`, `update_job()`, `delete_job()`, `upsert_jobs()` — all with deduplication, sort whitelist, stale-score detection
- `services/scraper_service.py`: `run_all()`, `get_status()`, per-source error isolation, `ScrapeRun` persistence
- `scrapers/base.py`: `BaseScraper` abstract class
- `scrapers/remoteok.py`: stub returning `[]` (real impl in Phase 1C)
- `scrapers/yc_jobs.py`: stub returning `[]`
- `routers/jobs.py`: 5 endpoints
- `routers/scraper.py`: 2 endpoints
- `main.py` updated to register jobs and scraper routers

### ✅ Phase 1C — RemoteOK Scraper
- `scrapers/remoteok.py` fully implemented
- Fetches from `https://remoteok.com/api` via httpx
- HTML description stripping via stdlib `HTMLParser` (no extra dep)
- Filters to internship-relevant jobs via keyword set on `position` + `tags`
- Tags appended to description for richer Gemini context in Phase 2
- `epoch` → `posted_at` with ISO 8601 `date` fallback
- Per-record error isolation: malformed records logged and skipped, rest continue
- Custom `User-Agent` header per RemoteOK ToS guidance

### ✅ Phase 1D — Resume Upload and PDF Extraction
- `schemas/resume.py`: `ResumeResponse`, `ResumeUploadResponse`, `ResumeTextResponse`
- `services/resume_service.py`: upload validation, PyMuPDF text extraction, DB upsert (delete-then-insert), `get_latest()`, `get_by_id()`
- `routers/resume.py`: `POST /api/resume/upload`, `GET /api/resume/latest`, `GET /api/resume/{resume_id}`
- `main.py` updated to register resume router
- No schema changes needed; `Resume` model already has all required columns
- No new migration needed; `resumes` table created in Phase 1A initial migration

### ✅ Phase 2A — Gemini Client
- `ai/gemini_client.py`: `GeminiClient` class with `extract_skills()` and `match_job()`
- Retry on 429, 500, 502, 503 with backoff 1s → 2s → 4s; custom `AIError` after 3 failures
- `_is_retryable()` detects transient failures by status code and exception type
- Response parsing validates schema, clamps score to [0, 100], strips markdown fences
- `ai/prompts.py`: `SKILL_EXTRACTION_PROMPT` and `JOB_MATCH_PROMPT` as string constants
- Temperature `0.1` for deterministic output; `max_output_tokens=2048`
- Never logs API key or raw resume text

### ✅ Phase 2B — Resume Skill Extraction
- `resume_service._extract_skills_safe()` wraps Gemini call with full exception handling
- Graceful degradation: `AIError` or unexpected exception → `skills=[]`, resume saved
- `_persist()` now accepts `skills` parameter populated from Gemini
- `ResumeUploadResponse.skills` now returns populated list on success
- No schema or migration changes needed


---

## Pending Phases

### 🔲 Phase 1E — YC Jobs Scraper
- Implement `scrapers/yc_jobs.py` with Playwright
- Navigate `workatastartup.com/jobs` with internship filter
- Extract and normalise job fields to `JobUpsertData`
- Handle browser timeout gracefully in finally block

### ✅ Phase 2A — Gemini Client
- `ai/gemini_client.py` implemented
- `extract_skills(raw_text)` → `list[str]` with retry on 429/500/502/503
- `match_job(description, skills)` → `MatchResult` TypedDict
- Exponential backoff: 1s → 2s → 4s; raises `AIError` after 3 failures
- Temperature `0.1`; response validated and clamped before return
- `ai/prompts.py` with `SKILL_EXTRACTION_PROMPT` and `JOB_MATCH_PROMPT`
- Markdown fence stripping on all Gemini responses
- `_is_retryable()` detects 429, 500-503, timeout, connection errors

### ✅ Phase 2B — Resume Skill Extraction
- `resume_service._extract_skills_safe()` calls `GeminiClient.extract_skills()`
- Graceful degradation: Gemini failure stores `skills=[]`, upload still succeeds
- Skills persisted into `resume.skills` JSONB column
- `ResumeUploadResponse.skills` now populated on successful extraction

### 🔲 Phase 2C — Job Match Scoring
- Implement `services/match_service.py`
- `score_job(job_id, db)`: cache check, Gemini call, store result
- Cache hit: `job.match_score` exists AND `job.resume_uploaded_at == resume.uploaded_at`
- Store: `match_score`, `missing_skills`, `match_summary`, `matched_at`, `resume_uploaded_at`
- Wire `POST /api/jobs/{id}/score` in `routers/jobs.py`
- Activate `get_active_resume` dependency in `dependencies.py`

### 🔲 Phase 3 — Polish and Hardening
- Empty state handling (no jobs, no resume, no scores)
- Loading states in frontend
- Error toasts for sync, score, upload failures
- Pytest service tests with mocked Gemini and DB
- Frontend build (Next.js, Tailwind, shadcn/ui)

---

## Current Working Features

| Feature | Status | Endpoint |
|---|---|---|
| Health check | ✅ Working | `GET /api/health` |
| Scraper trigger | ✅ Working | `POST /api/scraper/run` |
| Scraper status | ✅ Working | `GET /api/scraper/status` |
| Job list (paginated) | ✅ Working | `GET /api/jobs` |
| Job detail | ✅ Working | `GET /api/jobs/{id}` |
| Job status update | ✅ Working | `PATCH /api/jobs/{id}` |
| Job delete | ✅ Working | `DELETE /api/jobs/{id}` |
| RemoteOK sync | ✅ Working | via `POST /api/scraper/run` |
| Resume upload | ✅ Working | `POST /api/resume/upload` |
| Resume retrieval (latest) | ✅ Working | `GET /api/resume/latest` |
| Resume retrieval (by id) | ✅ Working | `GET /api/resume/{resume_id}` |
| Job scoring | 🔲 Stub (501) | `POST /api/jobs/{id}/score` |
| YC Jobs sync | 🔲 Stub | via `POST /api/scraper/run` |
| Skill extraction | ✅ Working | via `POST /api/resume/upload` |

---

## Known Limitations

- **Skill extraction degrades gracefully.** If Gemini is unavailable at upload time, `skills=[]` is stored. Re-upload the PDF once Gemini is reachable.
- **Job scoring returns 501.** `POST /api/jobs/{id}/score` is wired but returns `NOT_IMPLEMENTED` until Phase 2C.
- **YC Jobs is a stub.** `YCJobsScraper.run()` returns `[]`; Playwright implementation pending Phase 1E.
- **No frontend yet.** All interaction is via API (`http://localhost:8000/docs`).
- **`updated_at` not auto-triggered.** Set manually in service layer on each write; no DB trigger.
- **RemoteOK jobs delayed 24h.** Expected API behaviour; not a bug.
- **Internship filter is keyword-based.** May miss roles with non-standard titles; can tune `INTERNSHIP_KEYWORDS` in `scrapers/remoteok.py`.

---

## Next Immediate Phase

**Phase 2C — Job Match Scoring**

Tasks:
1. Create `services/match_service.py` with `score_job(job_id, db)`
2. Cache check: return existing score if `job.resume_uploaded_at == resume.uploaded_at`
3. Call `GeminiClient().match_job(description, skills)` on cache miss
4. Store `match_score`, `missing_skills`, `match_summary`, `matched_at`, `resume_uploaded_at` on job
5. Activate `get_active_resume` dependency in `dependencies.py`
6. Wire `POST /api/jobs/{id}/score` in `routers/jobs.py` (currently returns 501)

---

## Long-Term Roadmap

| Phase | Feature | Priority |
|---|---|---|
| 1E | YC Jobs Playwright scraper | High |
| 2A | Gemini client with retry | High |
| 2B | Skill extraction on resume upload | High |
| 2C | Job match scoring with cache | High |
| 3 | Frontend (Next.js) | High |
| 3 | Service-layer tests | Medium |
| 4 | Deployment (Vercel + Render + Supabase) | Medium |
| Post-MVP | Auto-score after sync | Low |
| Post-MVP | Resume versioning | Low |
| Post-MVP | Wellfound scraper | Low |
| Post-MVP | Cover letter generation | Low |
| Post-MVP | Recruiter discovery | Low |
| Post-MVP | Email follow-ups | Low |

---

## Last Updated

**Phase:** 2B complete
**Date:** 2026-06-21
**Updated by:** Implementation engineer
**Next update due:** After Phase 2C completion