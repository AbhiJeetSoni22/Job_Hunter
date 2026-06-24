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
        ├── main.py                 ← global HTTPException → ApiResponse handler (Phase 2D)
        ├── config.py
        ├── database.py
        ├── dependencies.py         ← get_active_resume active (Phase 2C)
        ├── models/
        │   ├── __init__.py
        │   ├── job.py
        │   ├── resume.py
        │   └── scrape_run.py
        ├── schemas/
        │   ├── __init__.py
        │   ├── job.py              ← needs_rescore on list+detail; ScoreResult removed (Phase 2D)
        │   └── resume.py
        ├── routers/
        │   ├── __init__.py
        │   ├── health.py
        │   ├── jobs.py             ← passes resume uploaded_at into service (Phase 2D)
        │   ├── scraper.py
        │   └── resume.py           ← paths aligned to spec; DELETE added (Phase 2D)
        ├── services/
        │   ├── __init__.py
        │   ├── job_service.py      ← needs_rescore computed on list+detail (Phase 2D)
        │   ├── scraper_service.py
        │   ├── resume_service.py
        │   └── match_service.py
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
- `schemas/job.py`: `JobListItem`, `JobResponse`, `JobUpdateRequest`, `JobUpdateResponse`, `JobUpsertData`, `PaginatedJobList`, `ScrapeRunResponse`, `ScraperRunSummary`, `ApiResponse[T]`, `ApiError`
- `services/job_service.py`: `list_jobs()`, `get_job()`, `update_job()`, `delete_job()`, `upsert_jobs()` — all with deduplication, sort whitelist
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
- `services/resume_service.py`: upload validation, PyMuPDF text extraction, DB upsert (delete-then-insert), `get_latest()`, `get_by_id()`, `delete_latest()`
- `routers/resume.py`: `POST /api/resume`, `GET /api/resume`, `GET /api/resume/{resume_id}`, `DELETE /api/resume`
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

### ✅ Phase 2D — Backend Hardening and API Cleanup
- `main.py`: global `HTTPException` handler — all errors return `{"data": null, "error": {"code": "...", "message": "..."}}` envelope consistently
- `main.py`: catch-all `Exception` handler — unhandled errors return `INTERNAL_ERROR`, never leak stack traces
- `main.py`: `_status_to_code()` maps FastAPI built-in HTTP codes to API error code strings
- `schemas/job.py`: `needs_rescore: bool` added to `JobListItem` and `JobResponse`
- `schemas/job.py`: dead `ScoreResult` class removed — `ScoreResponse` is the single authoritative score schema
- `services/job_service.py`: `list_jobs()` and `get_job()` accept optional `current_resume_uploaded_at: datetime | None`
- `services/job_service.py`: `_compute_needs_rescore()` static helper — True only when score exists AND resume changed
- `services/job_service.py`: `_to_list_item()` and `_to_response()` private helpers replace inline field mapping
- `routers/jobs.py`: `_get_resume_uploaded_at()` helper fetches active resume non-blocking (no 422 on read endpoints)
- `routers/jobs.py`: `list_jobs()` and `get_job()` pass `current_resume_uploaded_at` through to service
- `routers/resume.py`: paths aligned to `api_spec.md` — `POST /api/resume`, `GET /api/resume`, `DELETE /api/resume`
- `routers/resume.py`: `DELETE /api/resume` endpoint added; returns 404 `NO_RESUME` when nothing to delete
- No database migration required — no new columns

---

## Pending Phases

### 🔲 Phase 1E — YC Jobs Scraper
- Implement `scrapers/yc_jobs.py` with Playwright
- Navigate `workatastartup.com/jobs` with internship filter
- Extract and normalise job fields to `JobUpsertData`
- Handle browser timeout gracefully in finally block

### 🔲 Phase 3 — Frontend (Next.js 15)
- Pages: `/jobs`, `/jobs/[id]`, `/resume`
- Components: `JobCard`, `JobList`, `MatchResult`, `StatusDropdown`, `ResumeUploader`
- API layer: `lib/api.ts` — all fetch calls centralised
- Score badge, `needs_rescore` warning badge, missing skills list, summary on job detail
- Sortable job list by score

### 🔲 Phase 4 — Polish and Hardening
- Empty state handling (no jobs, no resume, no scores)
- Loading states and error toasts in frontend
- Pytest service tests with mocked Gemini and DB

### 🔲 Phase 5 — Application Tracking Workflows
- Status dropdown per job: `saved → applied → interview → offer / rejected`
- Notes field per job
- List view filtered by status

### 🔲 Phase 6 — Recommendation Engine
- Auto-score after sync
- Surface top-N jobs by score on dashboard
- Configurable threshold alerts

---

## Current API Endpoints

| Method | Path | Status | Description |
|---|---|---|---|
| GET | `/api/health` | ✅ Live | DB connectivity check |
| POST | `/api/scraper/run` | ✅ Live | Trigger all scrapers |
| GET | `/api/scraper/status` | ✅ Live | Latest run per source |
| GET | `/api/jobs` | ✅ Live | Paginated, filtered, sorted list with `needs_rescore` |
| GET | `/api/jobs/{id}` | ✅ Live | Full job detail with `needs_rescore` |
| POST | `/api/jobs/{id}/score` | ✅ Live | AI match scoring with cache |
| PATCH | `/api/jobs/{id}` | ✅ Live | Update status and notes |
| DELETE | `/api/jobs/{id}` | ✅ Live | Remove job |
| POST | `/api/resume` | ✅ Live | Upload PDF, extract skills |
| GET | `/api/resume` | ✅ Live | Fetch active resume |
| GET | `/api/resume/{id}` | ✅ Live | Fetch resume by ID |
| DELETE | `/api/resume` | ✅ Live | Delete active resume |

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
| Stale score flag (`needs_rescore`) on list and detail | ✅ Working |
| Job status update | ✅ Working |
| Job delete | ✅ Working |
| Resume upload (PDF) | ✅ Working |
| Resume delete | ✅ Working |
| PDF text extraction | ✅ Working |
| Gemini skill extraction | ✅ Working |
| AI job match scoring | ✅ Working |
| Score caching (cache hit) | ✅ Working |
| Stale score detection | ✅ Working |
| Consistent API error envelope | ✅ Working |
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

## Project Completion

| Layer | % Complete |
|---|---|
| Database schema + migrations | 100% |
| AI / Gemini integration | 100% |
| RemoteOK scraper | 100% |
| YC Jobs scraper | 10% (stub only) |
| Backend services | 100% |
| Backend routers + API contract | 100% |
| Frontend | 0% |
| Tests | 0% |
| **Overall MVP** | **~72%** |

---

## Next Recommended Phase

**Phase 3 — Frontend (Next.js 15)**

Backend API is feature-complete and contract-clean. Every endpoint returns consistent JSON envelopes, `needs_rescore` is surfaced on reads, and error responses are uniform. The tool is fully functional via Swagger UI but has no browser interface.

Minimum viable frontend:
1. `/resume` — upload PDF, view extracted skills
2. `/jobs` — list jobs, trigger sync, sort by score, `needs_rescore` badge
3. `/jobs/[id]` — full detail, score result, missing skills, status dropdown, notes

---

## Long-Term Roadmap

| Phase | Feature | Priority |
|---|---|---|
| 3 | Frontend (Next.js 15) | High |
| 1E | YC Jobs Playwright scraper | High |
| 4 | Service-layer tests + error polish | Medium |
| 5 | Application tracking workflows | Medium |
| 6 | Recommendation engine | Low |
| Post-MVP | Auto-score after sync | Low |
| Post-MVP | Resume versioning | Low |
| Post-MVP | Cover letter generation | Low |
| Post-MVP | Wellfound scraper | Low |
| Post-MVP | Recruiter discovery | Low |
| Post-MVP | Email follow-ups | Low |

---

## Last Updated

**Phase:** 2D complete
**Date:** 2026-06-24
**Updated by:** Implementation engineer
**Next update due:** After Phase 3 (frontend) completion