# Tasks

Build history for the MVP, audited against the actual codebase (not against
prior task-list status). Status reflects what exists in `backend/` and
`frontend/` today.

**Status key:**

* [x] Done — implemented and verified in code
* [~] Partial — implemented but with a known gap, noted inline
* [ ] Not started

---

# Phase 0A — Backend Foundation ✅ Done

## Goal
Database runs. FastAPI starts. Health endpoint works.

### Project Setup
* [x] Create repository
* [x] Create `backend/`
* [x] Create `frontend/`
* [x] Create `.gitignore`
* [x] Create `README.md`

### Dependencies (`backend/pyproject.toml`)
* [x] FastAPI 0.115.5
* [x] SQLAlchemy 2.0.36
* [x] Alembic 1.14.0
* [x] psycopg2-binary (PostgreSQL driver)
* [x] PyMuPDF 1.24.14
* [x] Playwright 1.48.0
* [x] httpx 0.27.2
* [x] pydantic-settings 2.6.1
* [x] google-generativeai 0.8.3

### Configuration
* [x] `app/config.py` — typed `Settings` (pydantic-settings), `.env` support
* [x] Validates `APP_ENV` and `LOG_LEVEL` at startup via field validators
* [x] `get_settings()` cached with `lru_cache`

### Database
* [x] `app/database.py` — SQLAlchemy engine + `SessionLocal`
* [x] `get_db()` / `DbSession` dependency

### FastAPI
* [x] `app/main.py` — app factory
* [x] CORS middleware configured
* [x] Global exception handlers for `HTTPException`, `RequestValidationError`, and unhandled exceptions — all normalized to the `{data, error}` envelope
* [x] Routers registered under `/api`

### Health Endpoint
* [x] `routers/health.py`
* [x] `GET /api/health` with DB connectivity check

### Alembic
* [x] `alembic.ini`, `alembic/env.py` configured, imports `app.models` for autogenerate

### Docker
* [x] `docker-compose.yml` — PostgreSQL 16 service, healthcheck configured

---

# Phase 0B — Frontend Foundation ✅ Done

## Goal
Next.js starts. Navigation works. Frontend can talk to the backend.

### Setup
* [x] Next.js 15 app, App Router
* [x] TypeScript enabled
* [x] Tailwind CSS v4 (via `@tailwindcss/postcss`, no `tailwind.config.ts` needed in v4)
* [x] ESLint configured

### UI
* [x] Custom hand-rolled component library in `components/ui/` (Button, Card, Badge, LoadingSpinner, EmptyState, ErrorState, PageHeader, Toast)
* [ ] shadcn/ui — **not used.** Earlier planning docs referenced it; the actual implementation is a small custom component set instead. This doc previously listed shadcn/ui as a dependency in error.

### Types (`lib/types.ts`)
* [x] `ApiResponse<T>`, `ApiError`, pagination types
* [x] Job types (`JobListItem`, `JobResponse`, `JobStatus`, filters, score response)
* [x] Resume types

### API Client (`lib/api.ts`)
* [x] Typed fetch wrapper — all components call through this, never `fetch` directly
* [x] Error handling via `ApiClientError`
* [x] Helper methods per resource (jobs, resume, scraper, dashboard)

### Layout
* [x] Root layout with sticky navbar, brand, nav links, footer
* [x] Nav links: Dashboard, Jobs, Resume

### Verification
* [x] Frontend starts, navigation works, backend reachable via Next.js rewrite proxy

---

# Phase 1 — Job Collection ✅ Done

## Backend Models
* [x] `models/job.py` — 18 columns, matches `DATABASE.md`
* [x] `models/scrape_run.py`
* [x] `schemas/job.py` — `JobListItem`, `JobResponse`, `ScrapeRunResponse`, `PaginatedJobList`, `ApiResponse[T]`, `ApiError`

## Scrapers
* [x] `scrapers/base.py` — `BaseScraper` abstract class, `run() -> list[dict]` contract
* [x] `scrapers/remoteok.py` — fetches RemoteOK's public JSON API via httpx, parses and normalizes fields
* [x] `scrapers/yc_jobs.py` — Playwright headless Chromium, extracts job cards, normalizes fields, handles timeouts gracefully, closes the browser in a `finally` block

## Services
* [x] `services/job_service.py` — `JobService` class: `list_jobs()`, `get_job()`, `update_job()`, `delete_job()`, `upsert_jobs()`
* [x] `services/scraper_service.py` — `ScraperService` class: `run_all()`, `get_status()`, `run_auto_score()`, per-source error isolation, `ScrapeRun` persistence

## Routers
* [x] `POST /api/scraper/run`
* [x] `GET /api/scraper/status`
* [x] `GET /api/jobs` (paginated, filtered, sorted)
* [x] `GET /api/jobs/{id}`
* [x] `DELETE /api/jobs/{id}` — added beyond the original plan
* [x] Pagination: `page`, `page_size`, total count

## Frontend
* [x] `JobCard`, `JobList` components
* [x] Jobs page — fetch, render, sync button, refresh after sync, server-side filters (status/source/scored), sort controls, pagination (Prev/Next), Reset filters
* [x] Job detail page (`/jobs/[id]`) — description, metadata, score button

**Phase complete:** Sync works against both live sources, jobs appear in the UI, job detail page works.

---

# Phase 2 — Resume Upload & Job Scoring ✅ Done

## Resume
* [x] `models/resume.py`
* [x] `schemas/resume.py`
* [x] `ai/gemini_client.py` — `GeminiClient.extract_skills()`, `GeminiClient.match_job()`, retry on 429/500/502/503 with exponential backoff (1s/2s/4s, 3 attempts), raises `AIError` on final failure
* [x] `ai/prompts.py` — `SKILL_EXTRACTION_PROMPT`, `JOB_MATCH_PROMPT`
* [x] `services/resume_service.py` — `ResumeService`: `upload_resume()`, `get_latest()`, `get_by_id()`, `delete_latest()`, plus internal PDF validation/extraction helpers
* [x] Upload validation: PDF-only, 5 MB max

### Resume Router
* [x] `POST /api/resume`
* [x] `GET /api/resume`
* [x] `GET /api/resume/{id}`
* [x] `DELETE /api/resume`
* [~] **Known issue:** `routers/resume.py` has a stray duplicate `@router.post("", ...)` decorator (lines ~90-99) left over from a previous edit. Because it has no function body of its own, Python decorator-stacking rules attach it to the *next* function (`get_resume`), which means `GET /api/resume`'s handler is technically also registered for `POST /api/resume`. In practice the real upload route (the first `@router.post`) is registered first and FastAPI matches it, so this has not caused an observed bug — but it's dead, confusing code that should be deleted. Flagged here per the "determine actual implementation, don't just trust old docs" instruction for this audit; not fixed as part of this documentation pass.

## Job Scoring
* [x] `services/match_service.py` — module-level `score_job()`, `recommendation_label()`, cache check via `resume_uploaded_at` comparison, `JobNotFoundError`/`NoResumeError`
* [x] Cache rule implemented exactly as planned: cached result returned only when `job.match_score` exists AND `job.resume_uploaded_at == resume.uploaded_at`
* [x] `POST /api/jobs/{id}/score`
* [x] `PATCH /api/jobs/{id}`

## Frontend
* [x] `ResumeUploader` (drag-and-drop + click), resume page, skills display (`SkillChip`)
* [x] Score display, missing skills, summary, `ScoreBadge`, `NeedsRescoreBadge`
* [x] Job detail: Score button, match result display, re-score badge
* [x] Status dropdown → `PATCH` status; notes textarea → `PATCH` notes, dirty-state Save button
* [x] Filters: status, source, scored-only toggle

**Phase complete:** all items verified working, including cache hits and stale-score detection.

---

# Phase 3 — Polish ✅ Mostly done

## Backend
* [x] Scraper failures handled and isolated per-source
* [x] Gemini failures mapped to `502 AI_ERROR`
* [x] Consistent error codes across all endpoints
* [x] Upload validation (PDF, size)
* [x] Service-layer tests — 104 tests across `test_job_service.py`, `test_resume_service.py`, `test_match_service.py`, `test_scraper_service.py`, `test_dashboard_service.py`
* [x] Gemini mocked in tests (`unittest.mock.patch` on `GeminiClient`)

## Frontend
* [x] Loading spinners on job list, job detail, resume page, and every async action (no loading skeletons yet — see Phase 4 below)
* [x] Empty states: no jobs, no resume
* [x] Error handling: toast notifications on sync/score/upload errors (`Toast.tsx`, `useToast()`)
* [x] Sorting: null match scores sort last
* [ ] Resume delete confirmation dialog — not implemented; `DELETE /api/resume` fires immediately on click

## Documentation
* [x] README finalized (this pass)
* [x] Docs cross-checked against code (this pass)
* [~] `.env.example` — confirm it lists every variable in the Environment Variables table before shipping (see `DEPLOYMENT.md`)

---

# Phase 5 — Recommendation Dashboard ✅ Done

*(Not in the original plan — added after Phase 3. Numbered 5 to match the phase label already used in code comments and `PROJECT_STATUS.md`; there is no separate "Phase 4" implementation, though a Phase 4 polish list exists below.)*

* [x] `schemas/dashboard.py` — `DashboardStats`, `MatchQualityBreakdown`, `TopMatchItem`
* [x] `services/dashboard_service.py` — `DashboardService.get_stats()`, one aggregate query + one indexed top-N query, no N+1
* [x] `routers/dashboard.py` — `GET /api/dashboard/stats`
* [x] `recommendation_label(score)` in `match_service.py` — Excellent/Strong/Potential/Low Match, surfaced on job list, job detail, and score response
* [x] `upsert_jobs()` returns newly-inserted job IDs so the sync flow can auto-score just those
* [x] `scraper_service._auto_score_new_jobs()` — scores new jobs post-sync via `BackgroundTasks`, skips cleanly with no resume, one job's AI error doesn't abort the rest
* [x] Frontend: `TopMatches.tsx`, `MatchQualityBreakdown.tsx`, `RecommendationBadge.tsx`, dashboard page wired to `GET /api/dashboard/stats`

---

# Phase 4 — Remaining Polish (Not started / partial)

* [ ] Loading skeletons for job list and job detail (currently spinners)
* [ ] Resume delete confirmation dialog
* [ ] Remove the debug dump call in `yc_jobs.py` (`_dump_debug()`) now that the scraper's selectors have been confirmed working against live data (28 jobs found, 23 new, in the most recent verified run)
* [ ] Fix the dead duplicate decorator in `routers/resume.py` (see Phase 2 note above)

---

# Phase 6 — Resume Gap Analyzer ✅ Done

*(New, isolated feature. Does not modify any existing Phase 1-5 logic or tables.)*

## Backend

* [x] `schemas/resume_analysis.py` — new file with `ResumeAnalysisRequest` and `ResumeAnalysisResponse`
* [x] `services/resume_analysis_service.py` — new service: `ResumeAnalysisService.analyze()`, job description validation, reuses `ResumeService.get_latest_with_text()` and `GeminiClient`
* [x] `routers/resume_analysis.py` — new router: `POST /api/resume/analyze` with proper error translation (NO_RESUME 422, EMPTY_JOB_DESCRIPTION 422, ANALYSIS_ERROR 502)
* [x] `ai/prompts.py` — `RESUME_GAP_ANALYSIS_PROMPT` added (separate from existing job-match prompt); prompt takes resume text + job description, returns match_score, summary, missing_skills, strengths, suggestions, ats_tips
* [x] `app/main.py` — resume_analysis router registered (imports handled correctly, no collision with existing /resume router)

## Frontend

* [x] `app/resume-review/page.tsx` — new page component for Resume Gap Analyzer
* [x] Resume pre-check on mount — gates page before user enters job description
* [x] `components/resume-review/JobDescriptionForm.tsx` — text area for job description + Analyze button
* [x] `components/resume-review/MatchScoreCard.tsx` — displays match_score prominently
* [x] `components/resume-review/SkillTagSection.tsx` — renders missing_skills, strengths as pills/chips
* [x] `components/resume-review/BulletListSection.tsx` — renders suggestions and ats_tips as bullet lists
* [x] Loading spinner during analysis, error states (NO_RESUME, network errors, AI failures)
* [x] `lib/api.ts` — `analyzeResume()` method added, error handling via `ApiClientError`
* [x] `lib/types.ts` — `ResumeAnalysisResponse` type added

## Documentation

* [x] `API_SPEC.md` — `POST /api/resume/analyze` endpoint documented with request/response examples and error cases
* [x] `ARCHITECTURE.md` — routes table updated with `/resume-review`, AI Layer section expanded to document the new prompt
* [x] `PRD.md` — Capability 6 added to MVP scope with user flow
* [x] `README.md` — Resume Gap Analyzer added to features list and project structure
* [x] `TASKS.md` — Phase 6 documented (this section)
* [x] `PROMPTS.md` — `RESUME_GAP_ANALYSIS_PROMPT` documented

**Phase complete:** All Resume Gap Analyzer components working end-to-end. Feature operates independently without affecting existing job scoring, tracking, or dashboard.

---

# Phase 7 — Interview Preparation Generator ✅ Done

*(New, isolated feature. Reuses the active resume and Gemini path without introducing persistence, caching, or background jobs.)*

## Backend
* [x] `schemas/interview_prep.py` — new `InterviewPrepResponse` schema with `project_questions`, `technical_questions`, `behavioral_questions`, `topics_to_revise`, and `interview_tips`
* [x] `services/interview_prep_service.py` — new `InterviewPrepService.generate()` orchestrator, using `ResumeService.get_latest_with_text()` and job lookup by ID
* [x] `routers/interview_prep.py` — new `POST /api/jobs/{job_id}/interview-prep` endpoint, translated to HTTP 200/404/422/502 as appropriate
* [x] `ai/prompts.py` — `INTERVIEW_PREP_PROMPT` added as a dedicated prompt separate from the resume-gap analyzer and job-matching prompts
* [x] `ai/gemini_client.py` — `generate_interview_prep()` and response parser added without modifying existing scoring behavior

## Frontend
* [x] Job detail page (`app/jobs/[id]/page.tsx`) — `Generate Interview Prep` action added inline with the existing score panel
* [x] `lib/api.ts` — typed `generateInterviewPrep()` helper added for the new endpoint
* [x] `components/interview-prep/InterviewPrepPanel.tsx` — renders the five result sections in the same card-based layout used elsewhere

## Documentation
* [x] `API_SPEC.md` — endpoint and error contract documented
* [x] `ARCHITECTURE.md` — request flow and service placement documented
* [x] `PROMPTS.md` — prompt schema and expected output documented

**Phase complete:** Interview Preparation Generator works end-to-end on the job detail page without adding any new infrastructure or persistence.

---

# MVP Completion Checklist

* [x] Jobs sync from RemoteOK
* [x] Jobs sync from YC Jobs
* [x] Duplicate URLs ignored
* [x] Scraper failures isolated
* [x] Resume upload works
* [x] Skills extracted
* [x] Resume replacement works
* [x] Job scoring works
* [x] Cached scoring works
* [x] Re-score detection works
* [x] Status updates persist
* [x] Notes persist
* [x] Health endpoint verifies DB
* [x] Auto-scoring after sync (originally listed as out-of-scope in `PRD.md`; implemented in Phase 5)
* [x] Recommendation dashboard
* [x] Resume Gap Analyzer (new in Phase 6)
* [x] 104 pytest tests passing (DB-gated via `TEST_DATABASE_URL`)
* [ ] `.env.example` verified complete against `DEPLOYMENT.md`
* [ ] Resume delete confirmation dialog
* [ ] Loading skeletons

**Overall: MVP complete including Resume Gap Analyzer.** Remaining items are polish, not blockers.