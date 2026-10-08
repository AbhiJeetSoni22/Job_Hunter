# Project Status & Development Progress

**Project:** AI Internship Hunter / Job Hunter  
**Current Milestone:** Phase 0 — Stabilization  
**Current Batch:** Batch 3 — Security / Configuration Hardening (COMPLETED)  
**Next Milestone:** Phase 0 → Batch 4 — Tests / CI / Documentation Alignment  
**Current Implementation Status:** Synchronized with Codebase  

---

## 1. Executive Summary

AI Internship Hunter is an AI-powered job discovery and application tracking platform built with FastAPI, Next.js, PostgreSQL, and Google Gemini AI. The project automates job collection, matches job descriptions against candidate resume skills, tracks applications through a multi-stage pipeline, surfaces recommendation dashboard analytics, and provides AI tools for gap analysis and interview preparation.

A controlled production-hardening roadmap is underway.
- **Phase 0 — Batch 1 (Scoring Pipeline Correctness)** has been completed, resolving critical scoring pipeline bugs, hardening AI error handling, providing force-rescore and bulk-scoring capabilities, implementing stuck run reconciliation, and ensuring strict multi-user score isolation.
- **Phase 0 — Batch 2 (Scraper Correctness & Safety)** has been completed, eliminating accidental mass expiry from failed or empty scrapes, introducing an explicit `ScraperResult` contract, fixing critical selector fallback bugs in the YC parser, and making database upserts and job lifecycle state transitions fully transactional.
- **Phase 0 — Batch 3 (Security / Configuration Hardening)** has been completed, securing JWT configuration, enforcing production CORS policies, hardening email fail-closed behavior, adding HTTP security headers, protecting OTP endpoints with advisory locks, bounding resume uploads and validating PDF magic bytes, adding PostgreSQL-backed per-user AI rate limiting, and guarding scraper runs with advisory locks and cooldown periods.

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
- [x] **Batch 2 — Scraper Correctness & Safety**
  - Explicit `ScraperResult` contract distinguishing success, failures, warnings, and suspiciousness.
  - Safe lifecycle guard (`age_missing: bool`) preventing empty or failed scrapes from aging/expiring active jobs.
  - Source-aware trust evaluation (`is_scrape_trustworthy`) distinguishing valid 0-job results from suspicious scrapes.
  - Fixed YC parser selector fallback indentation bugs in location, description, and date parsing.
  - Added DOM anchor vs parsed job validation to detect YC parser breakage.
  - Transactional rollback safety in `JobService.upsert_jobs` ensuring partial DB failures never corrupt state.
  - Preserved multi-user data isolation across global scraping and user-scoped auto-scoring.
- [x] **Batch 3 — Security / Configuration Hardening**
  - Production JWT secret validation (length >= 32, forbidden insecure defaults in prod).
  - Production CORS validation (forbidden wildcards in prod, origin parsing).
  - JWT access token lifetime reduced to 24 hours.
  - Fail-closed email service configuration in production mode.
  - Concurrency & attempt protection for OTP requests & verification using PostgreSQL advisory locks.
  - HTTP security headers middleware (`X-Content-Type-Options`, `X-Frame-Options`, `X-XSS-Protection`, `Referrer-Policy`, `Content-Security-Policy`).
  - Max bulk score limit tied to environment configuration (`settings.MAX_BULK_SCORE_LIMIT`).
  - Bounded resume uploads (`MAX_FILE_SIZE_BYTES = 5MB`, bounded stream read avoiding unbounded memory consumption).
  - Strict PDF magic-byte validation (`b"%PDF-"`).
  - Per-user AI rate limiting (`AI_RATE_LIMIT_PER_MINUTE`, HTTP 429 `AI_RATE_LIMIT_EXCEEDED`, envelope format, PostgreSQL-backed).
  - Scraper cooldown and concurrent run serialization (`SCRAPER_COOLDOWN_SECONDS`, HTTP 429 `SCRAPER_RATE_LIMITED`, PostgreSQL advisory locks).
  - Schema migration: `c3d4e5f6a7b8_add_rate_limit_events_table.py`.
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

## 4. Phase 0 Batch 2: Scraper Correctness & Safety (Implementation Details)

### What Was Broken:
1. **Accidental Mass Expiry**: When scrapers returned `[]` (due to network failure, bot protection, Playwright timeouts, or parser selector breakage), `JobService.upsert_jobs` treated the result as a successful scrape of 0 jobs and aged all active jobs (`missing_sync_count += 1`). Two consecutive empty scrapes permanently marked all active listings expired (`expired_at = now()`).
2. **Missing Scraper Result Contract**: Scrapers returned only `list[JobUpsertData]`, making it impossible for the ingestion coordinator to differentiate between a successful 0-job scrape, a partial scrape, an anti-bot lockout, or an uncaught parser failure.
3. **Broken YC Scraper Selector Fallbacks**: In `YCJobsScraper`, `_extract_location`, `_extract_description`, and `_extract_posted_at` had prematurely indented `return None` and fallback expressions placed inside the selector loops, causing the loop to exit on the very first selector attempt and ignoring configured fallbacks.
4. **Silent YC Parser Failures**: When Playwright timed out waiting for job elements or selector structures changed, `YCJobsScraper` caught `TimeoutError` and returned `[]`, masking scraper breakage as a successful 0-job scrape.
5. **Partial Scraper DB Mutation Risk**: In `JobService.upsert_jobs`, job record insertions, updates, and lifecycle aging were not encapsulated in an explicit transaction rollback block, allowing partial failure to potentially commit inconsistent lifecycle state.

### What Was Fixed:
1. **Explicit `ScraperResult` Contract**: Created `ScraperResult` dataclass in `app/scrapers/base.py` containing `source`, `jobs`, `success`, `error`, `warnings`, `is_suspicious`, and `details`. Implemented sequence protocol emulation (`__iter__`, `__len__`, `__getitem__`) for seamless backward compatibility.
2. **Safe Scrape Health Guard**: Added `is_scrape_trustworthy(source, result)` in `ScraperService` and `age_missing: bool = True` in `JobService.upsert_jobs`. Lifecycles are aged *only* when the scrape result is authenticated as trustworthy:
   - Failed scrapes (`success=False`) never age or expire jobs.
   - Suspicious empty scrapes (e.g. 0 jobs returned when database has active jobs) do not age jobs unless the source has explicitly validated that the empty state is legitimate.
   - Genuine empty scrapes (e.g., RemoteOK returns >1 raw records but 0 keyword matches) are verified as trustworthy.
3. **Fixed YC Scraper Parser & Fallbacks**:
   - Corrected loop indentation in `_extract_location`, `_extract_description`, and `_extract_posted_at` so all fallback selectors are evaluated.
   - Raised explicit `TimeoutError` when Playwright times out waiting for job cards instead of silently swallowing errors.
   - Added parser integrity assertion: raises `RuntimeError` if job link anchors exist in the DOM but 0 valid jobs could be extracted.
4. **Database Transaction Rollback & Commit Isolation**:
   - `JobService.upsert_jobs` wrapped in `try ... except: self.db.rollback(); raise`.
   - `new_job_ids` tracking deferred until after `self.db.commit()` succeeds.
5. **Multi-User Data Isolation Preserved**:
   - Scrapers ingest canonical global jobs (`jobs` table).
   - Auto-scoring is isolated per-user (`UserJob` and `ScoringRun` tied strictly to `CurrentUser.id`).
6. **No Alembic Migration Needed**: The existing `scrape_runs` table schema (`started_at`, `completed_at`, `jobs_found`, `jobs_new`, `error`) fully supported all required audit logging without modifying tables.

### Files Modified / Created:
- `backend/app/scrapers/base.py`: Added `ScraperResult` dataclass and updated `BaseScraper` contract.
- `backend/app/scrapers/remoteok.py`: Returned `ScraperResult` and added suspicious-truncation detection.
- `backend/app/scrapers/yc_jobs.py`: Fixed selector fallback indentation, removed silent timeout swallow, added anchor extraction validation, returned `ScraperResult`.
- `backend/app/services/job_service.py`: Added `count_active_jobs`, added `age_missing` guard to `upsert_jobs`, implemented explicit rollback safety.
- `backend/app/services/scraper_service.py`: Implemented `is_scrape_trustworthy`, guarded `age_missing` lifecycle execution, recorded suspicious flags in `ScrapeRun.error`.
- `backend/tests/test_scraper_service.py`: Hardened run cleanup in tests for DB isolation.
- `backend/tests/test_scraper_hardening.py`: Added 14 comprehensive tests covering all 18 requirements.
- `docs/PROJECT_STATUS.md`: Updated roadmap status and documentation.

---

## 5. Phase 0 Batch 3: Security / Configuration Hardening (Implementation Details)

### What Was Vulnerable / Unhardened:
1. **Unbounded Resume Upload**: Resume upload endpoint allowed unbounded `file.read()`, permitting gigabyte-scale memory consumption DoS attacks.
2. **Missing PDF Content Validation**: Upload validation checked only MIME type (`application/pdf` or `application/octet-stream`) and filename extension (`.pdf`), allowing arbitrary files or malware payloads to be uploaded if disguised with a `.pdf` extension.
3. **Missing Per-User AI Rate Limiting**: AI endpoints (`/api/jobs/{id}/score`, `/api/jobs/bulk-score`, `/api/resume/analyze`, `/api/jobs/{id}/interview-prep`) lacked rate limiting, exposing the system to quota depletion, runaway Google Gemini API costs, and abuse.
4. **Scraper Concurrency & Abuse**: Scraping trigger lacked user-scoped cooldown and concurrent run serialization, allowing users to flood background scraper runs or trigger overlapping processes.
5. **Hardcoded Bulk Scoring Limit**: `POST /api/jobs/bulk-score` had hardcoded `le=100` in route annotations instead of binding to `settings.MAX_BULK_SCORE_LIMIT`.
6. **Insecure Production Defaults**: JWT secret lacked production enforcement, wildcard CORS was tolerated in production mode, and JWT access token lifetimes lasted up to 7 days.
7. **OTP Endpoint Concurrency & Email Fail-Open**: OTP generation and verification lacked concurrency locks and allowed partial verification brute forcing; email sending silently caught failures in production.
8. **Missing HTTP Security Headers**: HTTP responses lacked standard defense-in-depth security headers (`X-Content-Type-Options`, `X-Frame-Options`, `Content-Security-Policy`, etc.).

### What Was Fixed:
1. **Bounded Resume File Read**: `ResumeService.upload_resume` reads at most `MAX_FILE_SIZE_BYTES + 1` (5MB + 1 byte) via chunked or bounded streaming, rejecting oversized files with HTTP 422 immediately without loading excessive bytes into memory.
2. **PDF Magic-Byte Verification**: `ResumeService._validate_magic_bytes` inspects the initial bytes of uploaded file content, strictly enforcing the `b"%PDF-"` file header magic bytes before parsing text with PyMuPDF.
3. **Per-User AI Rate Limiting (PostgreSQL-Backed & Concurrency-Safe)**:
   - Added `RateLimitEvent` model and `rate_limit_events` table (migration `c3d4e5f6a7b8_add_rate_limit_events_table.py`).
   - Implemented `RateLimitService.check_ai_rate_limit` tracking a 60-second sliding window against `settings.AI_RATE_LIMIT_PER_MINUTE` (default 30).
   - Serialized concurrent rate-limit checks per user using PostgreSQL transaction-scoped advisory locks (`pg_advisory_xact_lock(hashtext('ai_rate_limit:' || user_id))`), guaranteeing atomic check-and-insert execution and eliminating race conditions across concurrent requests.
   - Injected `check_ai_rate_limit` dependency into `/api/jobs/{id}/score`, `/api/jobs/bulk-score`, `/api/resume/analyze`, and `/api/jobs/{id}/interview-prep`.
   - Returns standard HTTP 429 envelope `{ success: false, data: null, error: { code: "AI_RATE_LIMIT_EXCEEDED", message: "..." } }`.
4. **Scraper Cooldown & Advisory Lock Concurrency Protection**:
   - `RateLimitService.scraper_run_guard` combines PostgreSQL session advisory locks (`pg_try_advisory_lock(hashtext('scraper_run:{user_id}'))`) with `rate_limit_events` DB status records.
   - Enforces `settings.SCRAPER_COOLDOWN_SECONDS` (default 60) between consecutive scraper runs for the same user.
   - Prevents overlapping concurrent scraper executions per user, returning HTTP 429 `SCRAPER_RATE_LIMITED`.
5. **Configurable Bulk Scoring Limit**:
   - `POST /api/jobs/bulk-score` dynamically validates payload `limit` against `get_settings().MAX_BULK_SCORE_LIMIT`, raising HTTP 422 `VALIDATION_ERROR` with custom detail message if exceeded.
6. **Production Configuration Hardening**:
   - Enforced production JWT secret length >= 32 characters, rejecting insecure default values.
   - Reduced JWT access token expiration to 24 hours.
   - Enforced CORS validation rejecting wildcard `*` in production mode.
   - Configured production email delivery fail-closed behavior.
7. **OTP Row-Level & Advisory Locking**:
   - Added PostgreSQL advisory locks for OTP request serialization and `SELECT ... FOR UPDATE` row locks for OTP verification attempt protection.
8. **HTTP Security Headers Middleware**:
   - Registered middleware injecting `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `X-XSS-Protection: 1; mode=block`, `Referrer-Policy: strict-origin-when-cross-origin`, and `Content-Security-Policy`.

### Files Modified / Created:
- `backend/app/models/rate_limit.py`: Created `RateLimitEvent` model.
- `backend/app/models/__init__.py`: Registered `RateLimitEvent`.
- `backend/alembic/versions/c3d4e5f6a7b8_add_rate_limit_events_table.py`: Migration for `rate_limit_events`.
- `backend/app/services/rate_limit_service.py`: Implemented AI rate limiting with transaction-scoped advisory locks and scraper cooldown/concurrency guards.
- `backend/app/dependencies.py`: Added `check_ai_rate_limit` dependency.
- `backend/app/services/resume_service.py`: Added bounded streaming read and PDF magic byte verification (`b"%PDF-"`).
- `backend/app/routers/jobs.py`: Added `check_ai_rate_limit` to single and bulk scoring; bound bulk score limit to `MAX_BULK_SCORE_LIMIT`.
- `backend/app/routers/resume_analysis.py`: Added `check_ai_rate_limit` to `/analyze`.
- `backend/app/routers/interview_prep.py`: Added `check_ai_rate_limit` to `/{job_id}/interview-prep`.
- `backend/app/routers/scraper.py`: Protected scraper execution with `scraper_run_guard`.
- `backend/tests/test_resume_service.py`: Added magic-byte and bounded-read unit tests.
- `backend/tests/test_batch3_security_hardening.py`: Added 18 comprehensive unit, integration, and multi-connection concurrency tests.
- `docs/PROJECT_STATUS.md`: Updated status to Batch 3 COMPLETED.

---

## 6. Completed Capabilities (Historical)

### ✅ Phase 0 — Core Infrastructure & Database
- **Backend Architecture**: FastAPI application factory with standard exception handlers and CORS middleware (`app/main.py`, `app/config.py`).
- **Database Layer**: PostgreSQL database configured with 7 SQLAlchemy 2.x models (`Job`, `Resume`, `ScrapeRun`, `ScoringRun`, `User`, `UserJob`, `RateLimitEvent`).
- **Migrations**: 8 Alembic migrations applied (`cc9c2e74a08d`, `63d3ec745a23`, `68abbd5b8e5a`, `7a1b2c3d4e5f`, `8c3d4e5f6a7b`, `9d4e5f6a7b8c`, `b2c3d4e5f6a7`, `c3d4e5f6a7b8`).
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

## 7. Known Limitations

- **In-Process BackgroundTasks**: Scraping and bulk scoring still run via FastAPI in-process `BackgroundTasks` until Phase 1 PostgreSQL Task Queue is introduced. Server restart during an active job will interrupt execution (though now safely reconciled via timeout recovery).
- **Database Dependency for Tests**: Backend integration tests require a live PostgreSQL database configured via `TEST_DATABASE_URL`.
- **Synchronous AI Client SDK**: Uses the synchronous Google Gemini SDK (`google-generativeai`).
- **Unpersisted Gap Analysis & Interview Prep**: Results generated by `/api/resume/analyze` and `/api/jobs/{id}/interview-prep` are returned to the client but not stored in the database (scheduled for Phase 3).