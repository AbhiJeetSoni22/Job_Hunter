# System Architecture

This is the authoritative technical reference for **how the system works internally**. For high-level requirements and feature progress, see [`PRD.md`](PRD.md) and [`PROJECT_STATUS.md`](PROJECT_STATUS.md).

---

## Table of Contents

1. [High-Level Architecture](#1-high-level-architecture)
2. [Backend Architecture](#2-backend-architecture)
3. [Persistent Background Scoring & Polling Architecture](#3-persistent-background-scoring--polling-architecture)
4. [Job Lifecycle & Expiration Architecture](#4-job-lifecycle--expiration-architecture)
5. [Frontend Architecture](#5-frontend-architecture)
6. [AI Architecture](#6-ai-architecture)
7. [Database Architecture](#7-database-architecture)
8. [Request Lifecycle](#8-request-lifecycle)
9. [Performance & Query Design](#9-performance--query-design)
10. [Error Handling & Envelope Model](#10-error-handling--envelope-model)
11. [Caching Strategy](#11-caching-strategy)
12. [Folder Structure](#12-folder-structure)
13. [Local Development & Environment](#13-local-development--environment)

---

## 1. High-Level Architecture

AI Internship Hunter is an AI-powered job discovery platform built with FastAPI, Next.js 15, PostgreSQL, and Google Gemini AI, currently featuring Phase 1 Authentication Foundation.

**System Constraints & Boundaries:**
- **Authentication Foundation**: User accounts, password security via Argon2id, PyJWT access tokens (7-day default expiry), and reusable `get_current_user` FastAPI dependency.
- **Phase 1 Resource Boundaries**: Existing jobs, resumes, scrape_runs, and scoring_runs tables remain shared/unmodified (no resource ownership migrations in Phase 1).
- **No External Task Queue / Message Broker**: No Redis, Celery, RabbitMQ, or external worker processes.
- **No Built-in In-Process Scheduler**: Scraping and cleanup are invoked on-demand via HTTP or external CLI commands (`python -m app.cleanup`).
- **Asynchronous Execution Model**: Post-sync auto-scoring runs after HTTP response transmission using FastAPI `BackgroundTasks`, with live progress persisted in PostgreSQL for client polling.

```text
Browser (Next.js 15 Client Components)
    │
    │ HTTP / JSON via lib/api.ts (Authorization: Bearer <token>)
    ▼
FastAPI Application (app/main.py)
    ├── Routers (app/routers/)          ← Validation & HTTP response mapping only
    ├── Core/Security (app/core/)       ← Argon2id hashing & PyJWT token handling
    ├── Dependencies (app/dependencies) ← get_current_user dependency
    ├── Services (app/services/)        ← Business rules & transaction management
    ├── Scrapers (app/scrapers/)        ← RemoteOK API (httpx) + YC Jobs (Playwright)
    └── AI Layer (app/ai/)              ← GeminiClient + 4 Prompt Templates
    │
    ▼
PostgreSQL 16 Database
    ├── users                           ← Candidate identity & Argon2id password hash
    ├── jobs                            ← Job listings, match scores, lifecycle fields
    ├── resumes                         ← Active candidate resume & extracted skills
    ├── scrape_runs                     ← Scraper execution logs
    └── scoring_runs                    ← Persistent background scoring batch progress
```

---

## 2. Backend Architecture

The backend follows a strict layered architecture: **Routers → Services → Core / AI Client / Scrapers / ORM Models**.

### 2.1 Routers (`app/routers/`)

Routers contain **zero business logic** and **zero database queries**. They handle request validation, delegate to a service, catch domain exceptions, and map results to standard `ApiResponse` envelopes.

| Router | Path Prefix | Endpoints | Responsibility |
|---|---|---|---|
| `health.py` | `/api` | `GET /health` | Liveness & PostgreSQL connection status |
| `auth.py` | `/api/auth` | `POST /register`, `POST /login`, `GET /me` | User registration, authentication, JWT token issuance, and profile resolution |
| `jobs.py` | `/api/jobs` | `GET /`, `GET /{id}`, `POST /{id}/score`, `PATCH /{id}`, `DELETE /{id}` | Job listing, detail, scoring, updates, deletion |
| `scraper.py` | `/api/scraper` | `POST /run`, `GET /status`, `GET /scoring-status` | Scraping trigger, source status, scoring run polling |
| `resume.py` | `/api/resume` | `POST /`, `GET /`, `DELETE /`, `GET /{resume_id}` | Resume PDF upload, active resume lookup, deletion |
| `resume_analysis.py` | `/api/resume` | `POST /analyze` | Resume Gap Analyzer (on-demand job text evaluation) |
| `interview_prep.py` | `/api/jobs` | `POST /{job_id}/interview-prep` | AI Interview Preparation Generator per job |
| `dashboard.py` | `/api/dashboard` | `GET /stats` | Recommendation dashboard aggregate statistics |

### 2.2 Services (`app/services/`)

Services contain all business rules, transaction boundaries, and integrations.

| Service | Pattern | Core Responsibilities |
|---|---|---|
| `JobService` | Class | Paginated search, lifecycle state updates, deduplication (`upsert_jobs`), expired job cleanup (`cleanup_expired_jobs`). |
| `ResumeService` | Class | PDF validation, PyMuPDF text extraction, Gemini skill extraction, single active resume replacement. |
| `match_service` | Module | Job match scoring, score cache verification, recommendation label calculation. |
| `ScraperService` | Class | Scraper orchestration, `ScrapeRun` logging, `ScoringRun` creation, background auto-scoring execution. |
| `DashboardService` | Class | Single-pass aggregate metric calculation and top matches lookup. |
| `ResumeAnalysisService` | Class | On-demand resume gap analysis against external job text. |
| `InterviewPrepService` | Class | Job description + active resume synthesis for interview prep generation. |

---

## 3. Persistent Background Scoring & Polling Architecture

Auto-scoring newly scraped jobs requires calling Gemini for each new job. Because Gemini API calls take 10–30 seconds per job, scoring cannot block the HTTP sync response (`POST /api/scraper/run`).

To solve this without an external task queue or losing progress tracking on server restarts, auto-scoring uses **FastAPI BackgroundTasks paired with persistent database state (`ScoringRun`)**.

```text
1. Client POST /api/scraper/run
        │
        ▼
2. ScraperService.run_all()
   - Scrapes RemoteOK & YC Jobs
   - JobService.upsert_jobs() inserts N new jobs
        │
        ▼
3. ScraperService.start_scoring_run(N)
   - Synchronously inserts a `scoring_runs` row:
     status="running", total_jobs=N, scored_jobs=0, failed_jobs=0
        │
        ▼
4. FastAPI returns HTTP 200 response immediately:
   ScraperRunSummary(..., scoring_run_id=UUID)
        │
        ├─────────────────────────────────────────┐
        ▼ (Background Task Execution)             ▼ (Client Polling Loop)
5. _auto_score_in_background()             6. Client receives scoring_run_id
   - Opens fresh SessionLocal()               - Polls GET /api/scraper/scoring-status?run_id=UUID
   - Loops over new job IDs                   - Renders live progress (e.g. "Scoring 2/5...")
   - Calls match_service.score_job()          - When status == "completed":
   - Updates `scored_jobs` / `failed_jobs`      Stops polling & refreshes dashboard
   - On completion, sets status="completed"
```

### Key Design Guarantee:
If individual job scoring fails (e.g. `AIError`, missing resume, missing job), `failed_jobs` is incremented. The batch reaches `completed` state exactly when `scored_jobs + failed_jobs == total_jobs`. Polling is guaranteed to terminate cleanly regardless of per-job Gemini failures.

---

## 4. Job Lifecycle & Expiration Architecture

Jobs removed from upstream job boards are automatically tracked and expired:

1. **Missing Sync Detection**: Every `Job` model has `last_seen_at` (DateTime), `missing_sync_count` (Integer), and `expired_at` (DateTime).
2. **Upsert Logic (`upsert_jobs`)**:
   - Jobs appearing in a sync have `last_seen_at` updated, `missing_sync_count` reset to `0`, and `expired_at` cleared (if previously expired).
   - Existing active jobs for that source *not* present in the sync have `missing_sync_count` incremented by 1.
3. **Expiration Threshold**: When `missing_sync_count >= 2`, `expired_at` is set to the current timestamp.
4. **Filtering & Dashboard Exclusion**: `GET /api/jobs` defaults to `include_expired=False`. Dashboard stats (`DashboardService.get_stats()`) explicitly filter `where(Job.expired_at.is_(None))`.
5. **Purge Cleanup Command (`python -m app.cleanup`)**:
   - Management script deletes expired jobs older than N days (default 30).
   - Safety rule: Only deletes jobs with status `"saved"` and no user notes. Any job with user activity (`applied`, `interview`, `offer`, `rejected`, or custom notes) is preserved permanently.

---

## 5. Frontend Architecture

The frontend is built with **Next.js 15 App Router** and React 19. All primary pages operate as client components (`"use client"`) for dynamic interactivity, while routing proxy rewrites forward `/api/*` requests to the FastAPI backend.

### 5.1 Route Map
- `/`: Static marketing & landing page.
- `/dashboard`: Recommendation Dashboard (stat cards, top matches, match quality breakdown, sync button).
- `/jobs`: Filterable job listing (status, source, scored status, include expired toggle, pagination, sorting).
- `/jobs/[id]`: Job detail view (description, manual score action, status/notes editor, inline AI Interview Prep panel).
- `/resume`: PDF resume upload dropzone, extracted skill tags display, delete resume action.
- `/resume-review`: Resume Gap Analyzer page (job description text area input, structured feedback display).

### 5.2 Centralized API Client (`frontend/lib/api.ts`)
- All network interaction is encapsulated in `lib/api.ts`.
- Implements `apiFetch<T>()` with error handling that parses the backend `ApiResponse[T]` envelope and throws typed `ApiClientError` instances on API errors.
- Navigation history helper (`lib/navigationHistory.ts`) supports back-button navigation (`BackButton.tsx`).

---

## 6. AI Architecture

All AI features interface with Google Gemini via `GeminiClient` (`app/ai/gemini_client.py`) using fixed prompts in `app/ai/prompts.py`.

```text
GeminiClient Configuration:
  - Model: settings.GEMINI_MODEL (default: "gemini-2.5-flash")
  - Temperature: 0.1 (low variability for structured JSON)
  - Max Output Tokens: 8192
  - Retry Policy: 3 attempts, exponential backoff (1s -> 2s -> 4s)
  - Retry Trigger: HTTP 429, 500, 502, 503, rate limits, timeouts
```

### 6.1 Implemented Prompts
1. `SKILL_EXTRACTION_PROMPT`: Extracts up to 30 normalized technical skills from resume text.
2. `JOB_MATCH_PROMPT`: Scores fit (0–100), lists missing skills (max 5), and provides a 2-sentence summary.
3. `RESUME_GAP_ANALYSIS_PROMPT`: Evaluates resume against pasted JD text for missing skills, strengths, suggestions, and ATS tips.
4. `INTERVIEW_PREP_PROMPT`: Generates project questions (max 8), technical questions (max 8), behavioral questions (max 6), revision topics (max 8), and interview tips (max 6).

---

## 7. Database Architecture

PostgreSQL 16 database configured via SQLAlchemy 2.x ORM models and managed by Alembic.

### 7.1 Schema Overview (4 Tables)

```text
+-----------------------+       +-----------------------+
|         jobs          |       |        resumes        |
+-----------------------+       +-----------------------+
| id (UUID, PK)         |       | id (UUID, PK)         |
| title, company, url   |       | filename, raw_text    |
| description, source   |       | skills (JSONB)        |
| status, notes         |       | uploaded_at           |
| match_score, summary  |       +-----------------------+
| missing_skills(JSONB) |
| matched_at            |       +-----------------------+
| resume_uploaded_at    |       |      scrape_runs      |
| last_seen_at          |       +-----------------------+
| missing_sync_count    |       | id (UUID, PK)         |
| expired_at            |       | source, jobs_found    |
| created_at, updated_at|       | jobs_new, error       |
+-----------------------+       | started_at, completed |
                                +-----------------------+
+-----------------------+
|     scoring_runs      |
+-----------------------+
| id (UUID, PK)         |
| status (running/comp) |
| total_jobs            |
| scored_jobs           |
| failed_jobs           |
| created_at, completed |
+-----------------------+
```

### 7.2 Migrations
1. `cc9c2e74a08d_initial_schema.py`: Created initial `jobs`, `resumes`, and `scrape_runs` tables.
2. `63d3ec745a23_add_job_lifecycle_fields.py`: Added `last_seen_at`, `missing_sync_count`, `expired_at`, and `idx_jobs_expired_at`.
3. `68abbd5b8e5a_add_scoring_runs_table.py`: Created `scoring_runs` table and `idx_scoring_runs_status`.

---

## 8. Request Lifecycle

```text
HTTP Request -> Next.js Proxy Rewrite -> FastAPI Router
  -> Pydantic Schema Validation
  -> Service Business Method
  -> Database / Gemini AI / Scraper Execution
  -> Service Exception or Data Return
  -> FastAPI Router ApiResponse Wrapping -> Client Response
```

---

## 9. Performance & Query Design

- **Dashboard Aggregation**: `DashboardService.get_stats()` executes exactly **2 SQL queries** (one aggregate `CASE WHEN` query for totals/breakdowns, and one indexed query for top 5 matches). No N+1 queries.
- **Upsert Efficiency**: `upsert_jobs` pre-loads existing jobs for incoming batch URLs using bulk `IN` queries.
- **Database Indexing**: Indexes on `jobs.status`, `jobs.source`, `jobs.match_score`, `jobs.expired_at`, `scrape_runs(source, started_at)`, and `scoring_runs.status`.

---

## 10. Error Handling & Envelope Model

All API responses follow a uniform structure:

```json
{
  "data": { ... } | null,
  "error": null | {
    "code": "ERROR_CODE_STRING",
    "message": "Human readable description"
  }
}
```

Standard Error Codes: `NOT_FOUND`, `INVALID_PARAM`, `INVALID_STATUS`, `NO_RESUME`, `INVALID_FILE`, `AI_ERROR`, `ANALYSIS_ERROR`, `INTERVIEW_PREP_ERROR`, `VALIDATION_ERROR`, `INTERNAL_ERROR`.

---

## 11. Caching Strategy

- **Job Match Score Cache**: Match scores are cached on `Job` records (`match_score`, `matched_at`, `resume_uploaded_at`).
- **Stale Score Detection**: If `resume_uploaded_at` on the job record is older than the active resume's `uploaded_at`, `needs_rescore` resolves to `true`.
- **Stateless AI Operations**: Resume Gap Analyzer and AI Interview Prep Generator are intentionally stateless and do not cache results.

---

## 12. Folder Structure

```
Job_Hunter/
├── backend/
│   ├── alembic/versions/          # 3 Alembic migrations
│   ├── app/
│   │   ├── main.py                # App factory & router registration
│   │   ├── cleanup.py             # Expired job cleanup CLI script
│   │   ├── models/                # job.py, resume.py, scrape_run.py, scoring_run.py
│   │   ├── schemas/               # Pydantic schemas (job.py, resume.py, dashboard.py, etc.)
│   │   ├── routers/               # health.py, jobs.py, scraper.py, resume.py, resume_analysis.py, interview_prep.py, dashboard.py
│   │   ├── services/              # job_service.py, resume_service.py, match_service.py, scraper_service.py, etc.
│   │   ├── scrapers/              # base.py, remoteok.py, yc_jobs.py
│   │   └── ai/                    # gemini_client.py, prompts.py
│   └── tests/                     # Backend pytest suite (123 tests)
└── frontend/
    ├── app/                       # Next.js pages (page.tsx, dashboard/, jobs/, resume/, resume-review/)
    ├── components/                # ui/, jobs/, resume/, dashboard/, resume-review/, interview-prep/
    └── lib/                       # api.ts, types.ts, navigationHistory.ts
```

---

## 13. Local Development & Environment

- Database: Run via `docker compose up -d` (PostgreSQL 16 on port 5432).
- Backend: Run via `uvicorn app.main:app --reload --port 8000`.
- Frontend: Run via `npm run dev` on port 3000.