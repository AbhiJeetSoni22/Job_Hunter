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
        └── ai/             ← Gemini client
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
        ├── dependencies.py         ← get_active_resume activated (Phase 2C)
        ├── models/
        │   ├── __init__.py
        │   ├── job.py
        │   ├── resume.py
        │   └── scrape_run.py
        ├── schemas/
        │   ├── __init__.py
        │   ├── job.py              ← ScoreResponse added (Phase 2C)
        │   └── resume.py
        ├── routers/
        │   ├── __init__.py
        │   ├── health.py
        │   ├── jobs.py             ← score endpoint live (Phase 2C)
        │   ├── scraper.py
        │   └── resume.py
        ├── services/
        │   ├── __init__.py
        │   ├── job_service.py
        │   ├── scraper_service.py
        │   ├── resume_service.py
        │   └── match_service.py    ← new (Phase 2C)
        ├── scrapers/
        │   ├── __init__.py
        │   ├── base.py
        │   ├── remoteok.py
        │   └── yc_jobs.py          ← stub (Phase 1E pending)
        └── ai/
            ├── __init__.py
            ├── gemini_client.py
            └── prompts.py
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
- Tags appended to description for richer Gemini context
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

### ✅ Phase 2C — Job Match Scoring
- `services/match_service.py` created with single public function `score_job(job_id, db)`
- Cache logic: hit → return stored result; stale → return stored + `needs_rescore=True`; miss → call Gemini
- Cache key: `job.resume_uploaded_at == resume.uploaded_at`
- On cache miss: calls `GeminiClient().match_job(description, skills)`, persists all score fields
- Persisted fields: `match_score`, `missing_skills`, `match_summary`, `matched_at`, `resume_uploaded_at`, `updated_at`
- `dependencies.py` updated: `get_active_resume()` now active — raises HTTP 422 `NO_RESUME` when no resume exists
- `schemas/job.py` updated: `ScoreResponse` added with `cached` and `needs_rescore` fields
- `routers/jobs.py` updated: `POST /api/jobs/{id}/score` 501 stub replaced with full Phase 2C handler
- No database migration required — all score columns existed from Phase 1A
- Bug fix: JSON parsing hardened; `match_summary` persistence corrected

---

## Pending Phases

### 🔲 Phase 1E — YC Jobs Scraper
- Implement `scrapers/yc_jobs.py` with Playwright
- Navigate `workatastartup.com/jobs` with internship filter
- Extract and normalise job fields to `JobUpsertData`
- Handle browser timeout gracefully in finally block

### 🔲 Phase 2D — Frontend Integration
- Build Next.js 15 frontend (App Router)
- Pages: `/jobs`, `/jobs/[id]`, `/resume`
- Components: `JobCard`, `JobList`, `MatchResult`, `StatusDropdown`, `ResumeUploader`
- API layer: `lib/api.ts` — all fetch calls centralised
- Score badge, missing skills list, summary on job detail
- Sortable job list by score

### 🔲 Phase 3 — Polish and Hardening
- Empty state handling (no jobs, no resume, no scores)
- Loading states in frontend
- Error toasts for sync, score, upload failures
- Pytest service tests with mocked Gemini and DB

### 🔲 Phase 4 — Application Tracking Workflows
- Status dropdown per job: `saved → applied → interview → offer / rejected`
- Notes field per job
- Kanban or list view filtered by status

### 🔲 Phase 5 — Recommendation Engine
- Auto-score after sync
- Surfaced top-N jobs by score on dashboard
- Configurable threshold alerts

---

## Current API Endpoints

| Method | Path | Status | Description |
|---|---|---|---|
| GET | `/api/health` | ✅ Live | DB connectivity check |
| POST | `/api/scraper/run` | ✅ Live | Trigger all scrapers |
| GET | `/api/scraper/status` | ✅ Live | Latest run per source |
| GET | `/api/jobs` | ✅ Live | Paginated, filtered, sorted job list |
| GET | `/api/jobs/{id}` | ✅ Live | Full job detail |
| POST | `/api/jobs/{id}/score` | ✅ Live | AI match scoring with cache |
| PATCH | `/api/jobs/{id}` | ✅ Live | Update status and notes |
| DELETE | `/api/jobs/{id}` | ✅ Live | Remove job |
| POST | `/api/resume/upload` | ✅ Live | Upload PDF, extract skills |
| GET | `/api/resume/latest` | ✅ Live | Fetch active resume |
| GET | `/api/resume/{id}` | ✅ Live | Fetch resume by ID |

---

## Current Database Tables

| Table | Key Columns |
|---|---|
| `jobs` | `id`, `title`, `company`, `description`, `url`, `source`, `status`, `match_score`, `missing_skills`, `match_summary`, `matched_at`, `resume_uploaded_at` |
| `resumes` | `id`, `filename`, `raw_text`, `skills`, `uploaded_at` |
| `scrape_runs` | `id`, `source`, `jobs_found`, `jobs_new`, `error`, `started_at`, `completed_at` |

---

## Current Working Features

| Feature | Status |
|---|---|
| Health check | ✅ Working |
| RemoteOK scraping | ✅ Working |
| Job storage and deduplication | ✅ Working |
| Job listing (paginated, filtered, sorted) | ✅ Working |
| Job detail view | ✅ Working |
| Job status update | ✅ Working |
| Job delete | ✅ Working |
| Resume upload (PDF) | ✅ Working |
| PDF text extraction | ✅ Working |
| Gemini skill extraction | ✅ Working |
| AI job match scoring | ✅ Working |
| Score caching (cache hit) | ✅ Working |
| Stale score detection | ✅ Working |
| YC Jobs scraping | 🔲 Stub |
| Frontend UI | 🔲 Not started |

---

## Current Limitations

- **No frontend.** All interaction via `http://localhost:8000/docs`.
- **YC Jobs is a stub.** Returns `[]`; Playwright implementation pending Phase 1E.
- **Skill extraction degrades gracefully.** If Gemini is unavailable at upload time, `skills=[]` is stored. Re-upload once Gemini is reachable.
- **Scoring requires a resume.** `POST /api/jobs/{id}/score` returns 422 until a resume is uploaded.
- **RemoteOK jobs delayed 24h.** Expected API behaviour; not a bug.
- **Internship filter is keyword-based.** May miss roles with non-standard titles.
- **`updated_at` not auto-triggered.** Set manually in service layer on each write; no DB trigger.
- **No background workers.** Scraping and scoring are synchronous, on-demand operations.

---

## Next Recommended Phase

**Phase 2D — Frontend Integration**

The backend API is feature-complete for MVP. All endpoints are live, tested, and returning correct JSON. The natural next step is the Next.js 15 frontend so the tool is usable without Swagger UI.

Minimum viable frontend:
1. `/resume` — upload PDF, view extracted skills
2. `/jobs` — list jobs, trigger sync, sort by score
3. `/jobs/[id]` — full detail, score badge, missing skills, status dropdown

---

## Long-Term Roadmap

| Phase | Feature | Priority |
|---|---|---|
| 2D | Frontend (Next.js 15) | High |
| 1E | YC Jobs Playwright scraper | High |
| 3 | Service-layer tests + error polish | Medium |
| 4 | Application tracking workflows | Medium |
| 5 | Recommendation engine | Low |
| Post-MVP | Auto-score after sync | Low |
| Post-MVP | Resume versioning | Low |
| Post-MVP | Cover letter generation | Low |
| Post-MVP | Wellfound scraper | Low |
| Post-MVP | Recruiter discovery | Low |
| Post-MVP | Email follow-ups | Low |

---

## Last Updated

**Phase:** 2C complete
**Date:** 2026-06-23
**Updated by:** Implementation engineer
**Next update due:** After Phase 2D completion