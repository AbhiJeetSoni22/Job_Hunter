# Project Status & Development Progress

**Project:** AI Internship Hunter / Job Hunter  
**Current Milestone:** Phase 0 — Stabilization  
**Current Batch:** Batch 1 — Scoring Pipeline Correctness (COMPLETED)  
**Next Milestone:** Phase 0 → Batch 2 — Scraper Correctness & Safety  
**Current Implementation Status:** Synchronized with Codebase  

---

## 1. Executive Summary

AI Internship Hunter is an AI-powered job discovery and application tracking platform built with FastAPI, Next.js, PostgreSQL, and Google Gemini AI. The project automates job collection, matches job descriptions against candidate resume skills, tracks applications through a multi-stage pipeline, surfaces recommendation dashboard analytics, and provides AI tools for gap analysis and interview preparation.

A controlled production-hardening roadmap is underway. **Phase 0 — Batch 1 (Scoring Pipeline Correctness)** has been completed, resolving critical scoring pipeline bugs, hardening AI error handling, providing force-rescore and bulk-scoring capabilities, implementing stuck run reconciliation, and ensuring strict multi-user score isolation.

---

## 2. Controlled Production Roadmap

### PHASE 0 — STABILIZATION (IN PROGRESS)
- [x] **Batch 1 — Scoring Pipeline Correctness**
  - Force-rescore mechanism (`POST /api/jobs/{id}/score?force=true`) bypassing stale cache.
  - Bulk scoring of unscored and stale jobs (`POST /api/jobs/bulk-score`).
  - Hardened Gemini failure handling (`ValueError`, missing keys, bad types wrapped into `AIError`).
  - Scoring run crash protection (batch loop wrapped to mark `ScoringRun` as `failed` with `error_message`).
  - Stuck scoring run recovery (`reconcile_stuck_runs` after 15m timeout and `POST /api/scraper/recover-stuck-runs`).
  - Preserved valid score on failed rescore attempt.
  - Schema migration: `b2c3d4e5f6a7_add_error_message_to_scoring_runs.py`.
- [ ] **Batch 2 — Scraper Correctness & Safety**
- [ ] **Batch 3 — Security / Configuration Hardening**
- [ ] **Batch 4 — Tests / CI / Documentation Alignment**

### PHASE 1 — POSTGRESQL TASK QUEUE + WORKER (PLANNED)
- [ ] `tasks` table with state machine & payload storage
- [ ] Dedicated worker process
- [ ] Retry & dead-letter queue semantics
- [ ] Durable background processing replacing in-process `BackgroundTasks`
- [ ] Scheduler foundation for recurring ingestion & maintenance

### PHASE 2 — PRODUCT / PIPELINE IMPROVEMENTS (PLANNED)
- [ ] Job Search & Filtering
- [ ] Application Tracker v2
- [ ] Candidate Profile / Eligibility
- [ ] Scheduled Ingestion

### PHASE 3+ — AI / RETRIEVAL / ADVANCED (PLANNED)
- [ ] AI gateway with rate-limiting & failover
- [ ] Persisted AI artifacts (gap analysis, interview prep)
- [ ] AI usage and cost tracking
- [ ] Prompt versioning & offline evaluation framework
- [ ] pgvector / hybrid retrieval when justified
- [ ] Automated resume tailoring & cover letter generation

---

## 3. Phase 0 Batch 1: Scoring Pipeline Correctness (Implementation Details)

### What Was Broken:
1. **Stale scores could not be refreshed**: Scoring was locked to cached results; calling the scoring endpoint returned cached data without a force bypass.
2. **Late-joining users could not bulk-score existing jobs**: Auto-scoring only targeted newly scraped jobs during ingestion; users joining after jobs already existed had no bulk-scoring path.
3. **Malformed AI responses orphaned scoring runs**: Unhandled JSON formatting or schema validation errors inside `match_job` could bubble up, leaving `ScoringRun` indefinitely in `running` status.
4. **Stuck scoring runs lacked recovery**: In the event of process restarts or unhandled failures during `BackgroundTasks`, scoring runs remained permanently in `running`, blocking or misleading the UI.
5. **Rescore failure destroyed score state**: A failed rescore could overwrite or corrupt valid prior score data.

### What Was Fixed:
1. **Force Rescore**: `score_job(..., force=False)` and `POST /api/jobs/{id}/score?force=true` allow users to explicitly force-rescore any job they own, bypassing the score cache and updating `UserJob` atomically upon success.
2. **Previous Score Preservation**: On a failed rescore (e.g. Gemini `AIError`), the previous valid score in `UserJob` is preserved untouched while a 502 error is returned.
3. **Bulk Scoring Endpoint**: Added `POST /api/jobs/bulk-score` (`JobService.find_unscored_and_stale_job_ids`), safely identifying unscored or stale jobs for the current user and launching background scoring with concurrent run protection (HTTP 409 `SCORING_IN_PROGRESS`).
4. **Gemini Error Hardening**: `_call_gemini` in `match_service.py` intercepts `ValueError`, `KeyError`, `TypeError`, and missing schema fields, safely converting them to structured `AIError`. In batch scoring, individual job scoring failures increment `failed_jobs` count without aborting the entire batch.
5. **ScoringRun Status & Error Persistence**: Added `error_message` (`sa.Text`, nullable) and `"failed"` status to `ScoringRun` via Alembic migration `b2c3d4e5f6a7`. Batch runners wrap top-level exceptions in `try/except` and mark the run as `failed` with the error message.
6. **Stuck Run Reconciliation**: Implemented `ScraperService.reconcile_stuck_runs(timeout_minutes=15)` which automatically marks runs older than 15 minutes as `failed` ("Timed out or interrupted"). Exposed manual trigger via `POST /api/scraper/recover-stuck-runs`.
7. **Frontend UX Integration**:
   - `frontend/app/jobs/[id]/page.tsx`: Fixed re-score button to call `scoreJob(job.id, { force: true })` with loading spinners and error toasts.
   - `frontend/app/jobs/page.tsx`: Added "⭐ AI Bulk Score" header action with live polling toast and automatic job list refresh upon completion.
   - `frontend/app/dashboard/page.tsx`: Added `"failed"` run terminal handling to stop polling and alert users.

### Files Modified / Created:
- `backend/app/models/scoring_run.py`: Added `"failed"` to status literals, added `error_message` column.
- `backend/alembic/versions/b2c3d4e5f6a7_add_error_message_to_scoring_runs.py`: Alembic migration for `error_message`.
- `backend/app/schemas/job.py`: Added `error_message` to `ScoringStatusResponse`, added `BulkScoreResponse`.
- `backend/app/services/match_service.py`: Added `force` parameter to bypass cache; hardened `_call_gemini` against malformed payloads.
- `backend/app/services/scraper_service.py`: Added `reconcile_stuck_runs`, `get_active_scoring_run`, resilient `run_auto_score` and `_auto_score_new_jobs` error handlers.
- `backend/app/services/job_service.py`: Added `find_unscored_and_stale_job_ids(user_id, include_stale, limit)`.
- `backend/app/routers/jobs.py`: Added `POST /api/jobs/bulk-score`, updated `POST /api/jobs/{id}/score` with `force: bool`.
- `backend/app/routers/scraper.py`: Added `POST /api/scraper/recover-stuck-runs`, updated `scoring-status` response.
- `backend/tests/conftest.py`: Added column existence check on test DB startup.
- `backend/tests/test_match_service.py`: Added 4 tests for force rescore, cache bypass, previous score preservation.
- `backend/tests/test_scoring_pipeline_hardening.py`: Added 13 tests covering all Batch 1 requirements.
- `frontend/lib/types.ts`: Updated `ScoringStatus` and added `BulkScoreResponse`.
- `frontend/lib/api.ts`: Added `scoreJob(..., { force })`, `bulkScoreJobs()`, and `recoverStuckRuns()`.
- `frontend/app/jobs/[id]/page.tsx`: Wired up force rescore button with live feedback.
- `frontend/app/jobs/page.tsx`: Added "⭐ AI Bulk Score" button with polling and list refresh.
- `frontend/app/dashboard/page.tsx`: Added `"failed"` status polling termination.

---

## 4. Completed Capabilities (Historical)

### ✅ Phase 0 — Core Infrastructure & Database
- **Backend Architecture**: FastAPI application factory with standard exception handlers and CORS middleware (`app/main.py`, `app/config.py`).
- **Database Layer**: PostgreSQL database configured with 6 SQLAlchemy 2.x models (`Job`, `Resume`, `ScrapeRun`, `ScoringRun`, `User`, `UserJob`).
- **Migrations**: 7 Alembic migrations applied (`cc9c2e74a08d`, `63d3ec745a23`, `68abbd5b8e5a`, `7a1b2c3d4e5f`, `8c3d4e5f6a7b`, `9d4e5f6a7b8c`, `b2c3d4e5f6a7`).
- **Health Check**: Endpoint `GET /api/health` checking liveness and database connectivity.

### ✅ Authentication Foundation & Multi-User Data Isolation
- **User Model & Migration**: `User` SQLAlchemy model and `users` table Alembic migration (`7a1b2c3d4e5f_add_users_table.py`).
- **Security Utilities**: Argon2id password hashing and PyJWT access token creation/decoding (`app/core/security.py`).
- **User Service**: Business logic for registration, authentication, email normalization, and user retrieval (`UserService`).
- **Auth Endpoints**: `POST /api/auth/register` (201 Created), `POST /api/auth/login` (200 OK), and `GET /api/auth/me` (200 OK).
- **FastAPI Dependency**: Reusable `get_current_user` dependency for resolving authenticated user identity from Bearer token headers.
- **Multi-User Isolation**: Every user data access operation strictly scopes queries to `current_user.id`.

### ✅ Job Discovery & Scraping
- **RemoteOK Scraper**: Public JSON API integration (`RemoteOKScraper`).
- **YC Jobs Scraper**: Headless browser scraper (`YCJobsScraper` using Playwright).
- **Orchestration**: `ScraperService.run_all()` executes scrapers sequentially and deduplicates jobs by canonical URL.

### ✅ Resume Management & AI Skill Extraction
- **PDF Upload**: Single-active-resume storage model (`ResumeService.upload_resume`).
- **PDF Text Parsing**: Extracted plain text via PyMuPDF (`fitz`).
- **AI Skill Extraction**: Gemini prompt (`SKILL_EXTRACTION_PROMPT`) parses normalized technical skills.
- **Resume CRUD**: Active resume lookup, ID lookup, and deletion (`GET /api/resume`, `DELETE /api/resume`).

### ✅ AI Match Scoring & Stale Score Detection
- **AI Job Matching**: Gemini prompt (`JOB_MATCH_PROMPT`) generates fit scores (0–100), missing skills (max 5), and 2-sentence summaries (`match_service.score_job`).
- **Score Caching & Force Rescore**: Cached score results stored on `UserJob`; `force=true` flag forces re-evaluation.
- **Stale Score Flagging**: `needs_rescore` flag detects when a job's score was generated against a previous resume version (`resume_uploaded_at`).

### ✅ Recommendation Dashboard & Frontend Interactivity
- **Aggregate Analytics**: Dashboard metrics (`GET /api/dashboard/stats`) computed in 2 SQL queries (totals, averages, match quality tiers, top 5 matches).
- **Expired Job Filtering**: Dashboard statistics and top matches strictly exclude expired jobs (`where(Job.expired_at.is_(None))`).
- **Frontend App Router**: Next.js 15 pages (`/`, `/dashboard`, `/jobs`, `/jobs/[id]`, `/resume`, `/resume-review`).
- **UI Component System**: `Card`, `Button`, `Badge`, `PageHeader`, `BackButton`, `ConfirmDialog`, `Toast`, `Skeleton`, `LoadingSpinner`, and `StatusBadge`.

---

## 5. Known Limitations

- **In-Process BackgroundTasks**: Scraping and bulk scoring still run via FastAPI in-process `BackgroundTasks` until Phase 1 PostgreSQL Task Queue is introduced. Server restart during an active job will interrupt execution (though now safely reconciled via timeout recovery).
- **Database Dependency for Tests**: Backend integration tests require a live PostgreSQL database configured via `TEST_DATABASE_URL`.
- **Synchronous AI Client SDK**: Uses the synchronous Google Gemini SDK (`google-generativeai`).
- **Unpersisted Gap Analysis & Interview Prep**: Results generated by `/api/resume/analyze` and `/api/jobs/{id}/interview-prep` are returned to the client but not stored in the database (scheduled for Phase 3).