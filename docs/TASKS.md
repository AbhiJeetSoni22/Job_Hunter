# Task & Build History

This document logs historical build tasks and development milestones synchronized with the current implementation.

**Status Key:**
- `[x]` Done — fully implemented and verified in codebase
- `[~]` Partial — partially implemented or known limitation
- `[ ]` Not started — future roadmap item

---

## Phase 0A — Backend Foundation ✅ Done
- `[x]` Repository & backend folder structure (`backend/`)
- `[x]` Application configuration via `pydantic-settings` (`app/config.py`)
- `[x]` SQLAlchemy 2.x engine & `SessionLocal` (`app/database.py`)
- `[x]` Global FastAPI exception handlers & `ApiResponse` envelope (`app/main.py`)
- `[x]` CORS middleware integration (`app/main.py`)
- `[x]` Health check endpoint `GET /api/health` (`app/routers/health.py`)
- `[x]` PostgreSQL service configuration (`docker-compose.yml`)

---

## Phase 0B — Frontend Foundation ✅ Done
- `[x]` Next.js 15 App Router setup (`frontend/`)
- `[x]` TypeScript & Tailwind CSS 4 configuration
- `[x]` Shared UI components (`Button`, `Card`, `Badge`, `PageHeader`, `BackButton`, `ConfirmDialog`, `Toast`, `Skeleton`, `LoadingSpinner`)
- `[x]` Centralized API fetch client (`frontend/lib/api.ts`)
- `[x]` TypeScript interfaces (`frontend/lib/types.ts`)
- `[x]` Next.js proxy rewrites `/api/*` -> `http://localhost:8000` (`next.config.ts`)

---

## Phase 1 — Core Schema & Job Collection ✅ Done
- `[x]` Initial Alembic migration `cc9c2e74a08d_initial_schema.py` (`jobs`, `resumes`, `scrape_runs` tables)
- `[x]` Base scraper interface (`app/scrapers/base.py`)
- `[x]` RemoteOK scraper (`app/scrapers/remoteok.py`)
- `[x]` YC Jobs Playwright scraper (`app/scrapers/yc_jobs.py`)
- `[x]` Job deduplication by canonical URL in `JobService.upsert_jobs()`
- `[x]` Scraper orchestration & logging in `ScraperService`
- `[x]` Router endpoints: `POST /api/scraper/run`, `GET /api/scraper/status`, `GET /api/jobs`, `GET /api/jobs/{id}`, `DELETE /api/jobs/{id}`
- `[x]` Interactive job list and job detail pages (`app/jobs/page.tsx`, `app/jobs/[id]/page.tsx`)

---

## Phase 2 — Resume Upload & AI Match Scoring ✅ Done
- `[x]` Resume ORM model (`app/models/resume.py`)
- `[x]` PDF text extraction using PyMuPDF (`fitz`)
- `[x]` Gemini client integration (`app/ai/gemini_client.py`) with exponential backoff retries
- `[x]` Gemini prompt `SKILL_EXTRACTION_PROMPT` (`app/ai/prompts.py`)
- `[x]` Gemini prompt `JOB_MATCH_PROMPT` (`app/ai/prompts.py`)
- `[x]` Resume Service & Router (`upload_resume`, `get_latest`, `delete_latest`)
- `[x]` Job Match Scoring (`match_service.score_job`)
- `[x]` Score caching & stale-score detection (`needs_rescore`)
- `[x]` Application tracking status (`saved`, `applied`, `interview`, `offer`, `rejected`) and free-text notes editing

---

## Phase 3 — Recommendation Dashboard & Background Processing ✅ Done
- `[x]` Alembic migration `68abbd5b8e5a_add_scoring_runs_table.py` (`scoring_runs` table)
- `[x]` Persistent background scoring model (`ScoringRun`) tracking batch progress (`running` | `completed`), scored count, and failed count
- `[x]` `POST /api/scraper/run` synchronous `ScoringRun` creation & background task dispatch (`_auto_score_in_background`)
- `[x]` Status polling endpoint `GET /api/scraper/scoring-status`
- `[x]` Dashboard aggregate statistics endpoint `GET /api/dashboard/stats` (computed via 2 SQL queries)
- `[x]` Frontend recommendation dashboard (`app/dashboard/page.tsx`, `TopMatches.tsx`, `MatchQualityBreakdown.tsx`)

---

## Phase 4 — Job Lifecycle, Expiration & System Polish ✅ Done
- `[x]` Alembic migration `63d3ec745a23_add_job_lifecycle_fields.py` (`last_seen_at`, `missing_sync_count`, `expired_at`)
- `[x]` Missing sync tracking in `upsert_jobs()` (expires job after 2 consecutive missing syncs)
- `[x]` `include_expired` query parameter on `GET /api/jobs`
- `[x]` Exclude expired jobs from Recommendation Dashboard metrics
- `[x]` Management cleanup command (`python -m app.cleanup [--days 30]`) for purging un-annotated, saved expired jobs
- `[x]` Configurable CORS via `CORS_ORIGINS` in `app/config.py` and `app/main.py`
- `[x]` Web app metadata (`favicon.ico`, `icon.png`, `apple-icon.png`, `og-image.png`, `robots.txt`, `site.webmanifest`, `sitemap.ts`)
- `[x]` Hand-rolled UI components (`ConfirmDialog`, `BackButton`, `Toast`, `Skeleton`)
- `[x]` Pytest backend test suite (123 total test items)

---

## Phase 5 — Resume Gap Analyzer ✅ Done
- `[x]` Gemini prompt `RESUME_GAP_ANALYSIS_PROMPT`
- `[x]` `ResumeAnalysisService` and router endpoint `POST /api/resume/analyze`
- `[x]` Frontend Resume Review page (`app/resume-review/page.tsx`, `JobDescriptionForm.tsx`, `MatchScoreCard.tsx`, `SkillTagSection.tsx`, `BulletListSection.tsx`)

---

## Phase 6 — AI Interview Preparation Generator ✅ Done
- `[x]` Gemini prompt `INTERVIEW_PREP_PROMPT`
- `[x]` `InterviewPrepService` and router endpoint `POST /api/jobs/{job_id}/interview-prep`
- `[x]` Frontend Interview Prep panel (`components/interview-prep/InterviewPrepPanel.tsx`) on job detail page

---

## Remaining Development & Future Roadmap 🔲
- `[ ]` Router-level HTTP integration unit tests (FastAPI `TestClient`)
- `[ ]` Dedicated unit test file for `InterviewPrepService` (`tests/test_interview_prep_service.py`)
- `[ ]` Frontend automated unit/component test suite (Jest / React Testing Library)
- `[ ]` ATS Resume Optimizer (Future planned capability for auto-tailoring resume PDFs)
- `[ ]` Multi-user authentication & user account isolation