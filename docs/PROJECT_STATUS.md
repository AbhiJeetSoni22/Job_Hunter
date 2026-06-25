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
├── backend/
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/
│   │       └── cc9c2e74a08d_initial_schema.py
│   └── app/
│       ├── main.py
│       ├── config.py
│       ├── database.py
│       ├── dependencies.py
│       ├── models/
│       │   ├── __init__.py
│       │   ├── job.py
│       │   ├── resume.py
│       │   └── scrape_run.py
│       ├── schemas/
│       │   ├── __init__.py
│       │   ├── job.py
│       │   └── resume.py
│       ├── routers/
│       │   ├── __init__.py
│       │   ├── health.py
│       │   ├── jobs.py
│       │   ├── scraper.py
│       │   └── resume.py
│       ├── services/
│       │   ├── __init__.py
│       │   ├── job_service.py
│       │   ├── scraper_service.py
│       │   ├── resume_service.py
│       │   └── match_service.py
│       ├── scrapers/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── remoteok.py
│       │   └── yc_jobs.py
│       └── ai/
│           ├── __init__.py
│           ├── gemini_client.py
│           └── prompts.py
└── frontend/                           ← Phase 3B
    ├── package.json                    (Next.js 15 + React 19 + Tailwind 4)
    ├── next.config.ts                  (rewrites /api/* → localhost:8000)
    ├── tsconfig.json
    ├── postcss.config.mjs
    ├── styles/
    │   └── globals.css                 (CSS variables + Tailwind import)
    ├── lib/
    │   ├── types.ts                    (all TS types from API contract)
    │   └── api.ts                      (centralised fetch — no fetch in components)
    ├── app/
    │   ├── layout.tsx                  (navbar, footer, max-width container)
    │   ├── page.tsx                    (dashboard: stat cards)
    │   ├── jobs/
    │   │   ├── page.tsx                (job list — server component)
    │   │   └── [id]/
    │   │       └── page.tsx            (job detail — server component)
    │   └── resume/
    │       └── page.tsx                (resume info or empty state)
    ├── components/
    │   ├── ui/
    │   │   ├── Button.tsx
    │   │   ├── Card.tsx
    │   │   ├── Badge.tsx
    │   │   ├── LoadingSpinner.tsx
    │   │   ├── EmptyState.tsx
    │   │   ├── ErrorState.tsx
    │   │   └── PageHeader.tsx
    │   ├── jobs/
    │   │   ├── JobCard.tsx
    │   │   ├── JobList.tsx
    │   │   ├── ScoreBadge.tsx
    │   │   ├── StatusBadge.tsx
    │   │   └── NeedsRescoreBadge.tsx
    │   └── resume/
    │       ├── SkillChip.tsx
    │       ├── ResumeInfoCard.tsx
    │       └── ResumeUploader.tsx
    └── hooks/                          (empty — ready for Phase 3C)
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
- `routers/jobs.py`: 5 endpoints
- `routers/scraper.py`: 2 endpoints

### ✅ Phase 1C — RemoteOK Scraper
- Fetches from `https://remoteok.com/api` via httpx
- HTML description stripping via stdlib `HTMLParser`
- Filters to internship-relevant jobs via keyword set on `position` + `tags`
- Tags appended to description for richer Gemini context
- `epoch` → `posted_at` with ISO 8601 `date` fallback
- Per-record error isolation; custom `User-Agent` per RemoteOK ToS

### ✅ Phase 1D — Resume Upload and PDF Extraction
- `schemas/resume.py`: `ResumeResponse`, `ResumeUploadResponse`, `ResumeTextResponse`
- `services/resume_service.py`: upload validation, PyMuPDF text extraction, DB upsert (delete-then-insert)
- `routers/resume.py`: `POST /api/resume`, `GET /api/resume`, `GET /api/resume/{id}`, `DELETE /api/resume`

### ✅ Phase 2A — Gemini Client
- `GeminiClient` with `extract_skills()` and `match_job()`
- Retry on 429/500/502/503 with backoff 1s → 2s → 4s; custom `AIError` after 3 failures
- Response parsing validates schema, clamps score to [0, 100], strips markdown fences
- `ai/prompts.py`: `SKILL_EXTRACTION_PROMPT` and `JOB_MATCH_PROMPT`

### ✅ Phase 2B — Resume Skill Extraction
- `resume_service._extract_skills_safe()` wraps Gemini call with full exception handling
- Graceful degradation: `AIError` → `skills=[]`, resume still saved
- `ResumeUploadResponse.skills` returns populated list on success

### ✅ Phase 2C — Job Match Scoring
- `services/match_service.py`: `score_job(job_id, db)`
- Cache logic: hit → return stored; stale → return stored + `needs_rescore=True`; miss → call Gemini
- Cache key: `job.resume_uploaded_at == resume.uploaded_at`
- Persisted fields: `match_score`, `missing_skills`, `match_summary`, `matched_at`, `resume_uploaded_at`

### ✅ Phase 2D — Backend Hardening and API Cleanup
- Global `HTTPException` handler — all errors return consistent `{"data": null, "error": {...}}` envelope
- Catch-all `Exception` handler — unhandled errors return `INTERNAL_ERROR`, never leak traces
- `needs_rescore: bool` on `JobListItem` and `JobResponse`
- `_compute_needs_rescore()` static helper — True only when score exists AND resume changed
- `routers/resume.py` paths aligned to spec; `DELETE /api/resume` added

### ✅ Phase 3A — YC Jobs Scraper
- Playwright headless Chromium navigating `https://www.workatastartup.com/jobs?role=eng&type=intern`
- Windows + Python 3.13 fix: `asyncio.WindowsProactorEventLoopPolicy()` set at import time
- Pure Playwright locator approach — no `evaluate()` or JS DOM injection
- Job-link discovery via `page.locator("a[href^='/jobs/']").all()` filtered by regex `^/jobs/\d+$`
- Card container resolved by walking XPath parent axis until ancestor containing company link found
- Always-on debug dump: `yc_dom_dump.html` + `yc_debug.txt` written to cwd on every run
- Verified live: `jobs_found=28, jobs_new=28, error=null`

### ✅ Phase 3B — Frontend Foundation (Next.js 15)
- Next.js 15 App Router, React 19, TypeScript strict, Tailwind CSS v4
- `next.config.ts`: rewrites `/api/*` → `localhost:8000` (no CORS issues in dev)
- `lib/types.ts`: all TypeScript types derived from backend API contract — single source of truth
- `lib/api.ts`: centralised fetch layer — zero fetch calls inside components
  - `ApiClientError` class with `code` + `message`
  - 15-second timeout via `AbortController`
  - FormData detection — never sets `Content-Type` on multipart uploads
  - Non-JSON response guard before `.json()` call
  - `API_BASE_URL` env var for server-side (not `NEXT_PUBLIC_*`, not exposed to browser)
- `app/layout.tsx`: sticky navbar, brand logo, nav links, responsive container, footer
- `app/page.tsx`: dashboard with stat cards (Total Jobs, Resume, Last Sync, Top Match) — server component, parallel fetches
- `app/jobs/page.tsx`: job list — server component, renders `JobList`
- `app/jobs/[id]/page.tsx`: job detail — title, badges, description, apply link
- `app/resume/page.tsx`: resume info card or empty state
- `components/ui/`: `Button`, `Card`, `Badge`, `LoadingSpinner`, `EmptyState`, `ErrorState`, `PageHeader`
- `components/jobs/`: `JobCard`, `JobList`, `ScoreBadge`, `StatusBadge`, `NeedsRescoreBadge`
- `components/resume/`: `SkillChip`, `ResumeInfoCard`, `ResumeUploader`
- Dark theme via CSS custom properties; no Tailwind config file needed (v4)

---

## Pending Phases

### 🔲 Phase 3C — Frontend Interactivity
- Resume upload flow (drag-and-drop → POST → skill display)
- Resume delete with confirmation
- Score button on job detail (`POST /api/jobs/{id}/score`)
- Status dropdown per job (`PATCH /api/jobs/{id}`)
- Notes textarea per job
- Scraper trigger button with loading state
- `needs_rescore` warning + one-click rescore

### 🔲 Phase 4 — Polish and Hardening
- Pagination controls on job list
- Sort and filter controls (by source, status, scored)
- Error toasts (global, reusable)
- Loading skeletons for job list and detail
- Pytest service tests with mocked Gemini and DB

### 🔲 Phase 5 — Application Tracking Workflows
- List view filtered by status
- Status history / timeline
- Bulk status update

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
| YC Jobs scraping | ✅ Working |
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
| Frontend — dashboard | ✅ Working |
| Frontend — job list | ✅ Working |
| Frontend — job detail | ✅ Working |
| Frontend — resume view | ✅ Working |
| Frontend — resume upload (interactive) | 🔲 Phase 3C |
| Frontend — score button | 🔲 Phase 3C |
| Frontend — status dropdown | 🔲 Phase 3C |
| Frontend — scraper trigger | 🔲 Phase 3C |
| Frontend — pagination / filters | 🔲 Phase 4 |

---

## Current Limitations

- **Frontend interactivity incomplete.** Upload, scoring, status update, scraper trigger — all Phase 3C.
- **No pagination UI.** Backend supports it; frontend hardcoded to page 1, page_size 20.
- **No filter/sort UI.** Backend supports it; controls not yet built.
- **Skill extraction degrades gracefully.** If Gemini unavailable at upload time, `skills=[]` stored. Re-upload once reachable.
- **Scoring requires a resume.** `POST /api/jobs/{id}/score` returns 422 until resume uploaded.
- **RemoteOK jobs delayed 24h.** Expected API behaviour; not a bug.
- **Internship filter is keyword-based.** May miss roles with non-standard titles.
- **No background workers.** Scraping and scoring are synchronous, on-demand.
- **YC debug files always written.** `yc_dom_dump.html` + `yc_debug.txt` written to cwd on every scraper run. Remove `_dump_debug()` call in `yc_jobs.py` once selectors are confirmed stable.

---

## Project Completion

| Layer | % Complete |
|---|---|
| Database schema + migrations | 100% |
| AI / Gemini integration | 100% |
| RemoteOK scraper | 100% |
| YC Jobs scraper | 100% |
| Backend services | 100% |
| Backend routers + API contract | 100% |
| Frontend foundation | 100% |
| Frontend interactivity | 0% |
| Tests | 0% |
| **Overall MVP** | **~92%** |

---

## Next Recommended Phase

**Phase 3C — Frontend Interactivity**

Foundation is complete and rendering real data. All read paths work. Next step is wiring the write paths: resume upload, score trigger, status update, and scraper run button. These are all client components with loading states and error handling.

Priority order:
1. Resume upload (unlocks scoring)
2. Score button on job detail (core value prop)
3. Scraper trigger on dashboard (so user can refresh without Swagger)
4. Status dropdown on job detail (tracking workflow)

---

## Long-Term Roadmap

| Phase | Feature | Priority |
|---|---|---|
| 3C | Frontend interactivity | High |
| 4 | Pagination, filters, error toasts, loading skeletons | High |
| 4 | Pytest service tests | Medium |
| 5 | Application tracking workflows | Medium |
| 6 | Recommendation engine | Low |
| Post-MVP | Auto-score after sync | Low |
| Post-MVP | Resume versioning | Low |
| Post-MVP | Cover letter generation | Low |
| Post-MVP | Wellfound scraper | Low |

---

## Last Updated

**Phase:** 3B complete
**Date:** 2026-06-25
**Updated by:** Implementation engineer
**Next update due:** After Phase 3C (frontend interactivity) completion