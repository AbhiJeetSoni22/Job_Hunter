# Architecture

This is the technical reference for **how the system works internally**. For project progress, phase history, and roadmap, see [`PROJECT_STATUS.md`](PROJECT_STATUS.md).

---

## Table of Contents

1. [High-Level Architecture](#1-high-level-architecture)
2. [Backend Architecture](#2-backend-architecture)
3. [Frontend Architecture](#3-frontend-architecture)
4. [AI Architecture](#4-ai-architecture)
5. [Database Architecture](#5-database-architecture)
6. [Request Lifecycle](#6-request-lifecycle)
7. [Data Flow](#7-data-flow)
8. [Performance Optimizations](#8-performance-optimizations)
9. [Error Handling](#9-error-handling)
10. [Caching Strategy](#10-caching-strategy)
11. [Design Principles](#11-design-principles)
12. [Scalability Considerations](#12-scalability-considerations)
13. [Security Considerations](#13-security-considerations)
14. [Folder Structure](#14-folder-structure)
15. [Dependency Versions](#15-dependency-versions)
16. [Local Development](#16-local-development)

---

## 1. High-Level Architecture

Single-user personal tool. No authentication. No task queue. No scheduler. The only background execution is a single FastAPI `BackgroundTasks` call that scores newly-synced jobs after the sync response has already gone back to the browser — everything else is synchronous and on-demand.

```text
Browser (Next.js 15, client components)
    │
    │ HTTP/JSON via lib/api.ts
    ▼
FastAPI Backend
    ├── routers/     ← HTTP only, no business logic
    ├── services/    ← all business logic, independently testable
    ├── scrapers/    ← RemoteOK (httpx) + YC Jobs (Playwright)
    └── ai/          ← Gemini client + prompt templates
    │
    ▼
PostgreSQL 16
(jobs, resumes, scrape_runs)
```

Four AI capabilities now sit behind the `ai/` layer (skill extraction, job matching, resume gap analysis, interview prep generation) — all four route through the same `GeminiClient`, sharing one retry/backoff and JSON-parsing implementation (see §4, §8, §10).

---

## 2. Backend Architecture

Routers stay thin. All business logic lives in services. This split was established in the earliest phase of the project specifically so every later feature (scoring, dashboard, gap analyzer, interview prep) could be added the same way, without re-deciding where logic belongs.

### Routers (`app/routers/`)

| Router | Prefix | Responsibility |
|---|---|---|
| `health.py` | `/api` | Liveness + DB connectivity |
| `jobs.py` | `/api/jobs` | List/get/score/update/delete |
| `resume.py` | `/api/resume` | Upload/get/delete |
| `resume_analysis.py` | `/api/resume` | Resume Gap Analyzer (`POST /analyze`) — added Phase 6, registered separately from `resume.py`, shares the URL prefix only for readability |
| `interview_prep.py` | `/api/jobs` | Interview Prep Generator (`POST /{job_id}/interview-prep`) — added Phase 7, registered separately from `jobs.py` for the same reason |
| `scraper.py` | `/api/scraper` | Trigger scrape, get scraper status |
| `dashboard.py` | `/api/dashboard` | Aggregate stats — added Phase 5 |

Rule: routers never query the database directly, never call `GeminiClient` directly, and never contain business logic — they parse input, call exactly one service method, and translate the service's exceptions into HTTP responses.

### Services (`app/services/`)

| Service | Shape | Responsibility |
|---|---|---|
| `job_service.JobService` | class | `list_jobs()`, `get_job()`, `update_job()`, `delete_job()`, `upsert_jobs()` |
| `resume_service.ResumeService` | class | `upload_resume()`, `get_latest()`, `get_by_id()`, `get_latest_with_text()`, `delete_latest()` |
| `match_service` | module-level functions | `score_job()`, `recommendation_label()` — raises `JobNotFoundError`/`NoResumeError`, translated by the router to 404/422 |
| `scraper_service.ScraperService` | class | `run_all()`, `get_status()`, `run_auto_score()` |
| `dashboard_service.DashboardService` | class | `get_stats()` |
| `resume_analysis_service.ResumeAnalysisService` | class | `analyze()` — Phase 6 |
| `interview_prep_service.InterviewPrepService` | class | `generate()` — Phase 7 |

The mix of classes (stateful, hold a DB session) and one module of plain functions (`match_service`) reflects how each grew, not an inconsistency to "fix" — see §11 Design Principles.

### Schemas (`app/schemas/`)

Pydantic v2 models, one file per feature area (`job.py`, `resume.py`, `dashboard.py`, `resume_analysis.py`, `interview_prep.py`). Every response is wrapped in a generic `ApiResponse[T]` envelope (`data`, `error`) defined once in `job.py` and reused everywhere. Schemas never import ORM models directly — services convert `Model → Schema` via `model_validate()`.

### Models (`app/models/`)

Three SQLAlchemy 2.x ORM models — `Job`, `Resume`, `ScrapeRun` — with no relationships/foreign keys between them (see §5, §11). `app/models/__init__.py` acts as a model registry: importing it (as `alembic/env.py` does) guarantees every model is registered on `Base.metadata` before Alembic inspects it for autogeneration.

### AI (`app/ai/`)

`gemini_client.py` (the only code that talks to Gemini) + `prompts.py` (four prompt-template constants). See §4.

### Scrapers (`app/scrapers/`)

`base.py` defines the shared interface:

```python
class BaseScraper(ABC):
    def run(self) -> list[JobUpsertData]: ...
```

`remoteok.py` and `yc_jobs.py` implement it. Scrapers are pure — no DB access, no service calls — they only return normalized job data; `ScraperService` is responsible for persistence.

### Dependencies (`app/dependencies.py`, `app/database.py`)

`app/database.py` defines `get_db` (a FastAPI dependency yielding a request-scoped `Session`). `app/dependencies.py` independently defines an equivalent `get_db_session`/`DbSession` pair, plus `get_active_resume` (a dependency that raises 422 `NO_RESUME` when no resume exists, used by the scoring endpoint before the service is even called). Routers currently use one or the other inconsistently.

### Import Rules

Allowed: `routers → services → models`, `services → ai`, `services → scrapers` (ScraperService calling `.run()` only).
Not allowed: `router → router`, `service → router`, `scraper → service` (scrapers are pure, per above).

---

## 3. Frontend Architecture

Next.js 15, App Router, every page is a client component (`"use client"`) since every page needs interactivity (sync button, filters, forms) rather than static content — except the home page, which is a static landing page.

### Routes

| Route | Purpose |
|---|---|
| `/` | Static landing/marketing page — hero, feature grid, preview cards, CTA. **Not** the dashboard (see correction note below). |
| `/dashboard` | The live dashboard — stat cards, Sync Jobs button, Top Matches, Match Quality Breakdown |
| `/jobs` | Job list — server-side filters (status/source/scored), sorting, pagination |
| `/jobs/[id]` | Job detail — description, Score button, match result, status/notes editing, and the Interview Prep panel (Phase 7) |
| `/resume` | Resume upload (drag-and-drop), extracted skills, delete |
| `/resume-review` | Resume Gap Analyzer (Phase 6) — paste a job description, analyze against the active resume |

> **Correction:** an earlier version of this document listed `/` as the dashboard route. That was accurate at an earlier point in the project but is no longer correct — the dashboard was moved to its own `/dashboard` route (Phase 5), and `/` was later repurposed as a static landing page. The navbar (`app/layout.tsx`) links to `/dashboard`, `/jobs`, `/resume`, and `/resume-review`.

Frontend communicates with FastAPI through a Next.js `rewrites()` proxy (`/api/*` → the backend's base URL, configurable via `API_BASE_URL`, default `http://localhost:8000`) — not through separate Next.js API routes. The browser never talks to the backend directly.

### Components (`components/`)

| Directory | Contents |
|---|---|
| `ui/` | `Button`, `Card`, `Badge`, `LoadingSpinner`, `EmptyState`, `ErrorState`, `PageHeader`, `Toast`, `Skeleton` (`JobCardSkeleton`, `StatCardSkeleton`) |
| `jobs/` | `JobCard`, `JobList`, `ScoreBadge`, `StatusBadge`, `StatusSelect`, `NeedsRescoreBadge`, `RecommendationBadge` (Phase 5), `ResumeRequiredBadge` |
| `resume/` | `SkillChip`, `ResumeInfoCard`, `ResumeUploader`, `ResumeOverviewCard`, `ResumePageHeader`, `ResumeSkillsCard`, `ResumeUploadCard`, `ResumeUploadProgress`, `ResumeEmptyPanel` |
| `dashboard/` | `TopMatches`, `MatchQualityBreakdown` (both Phase 5) |
| `resume-review/` | `JobDescriptionForm`, `MatchScoreCard`, `SkillTagSection`, `BulletListSection` (all Phase 6) |
| `interview-prep/` | `InterviewPrepPanel` (Phase 7) |

### API Layer

`lib/api.ts` is the single fetch client — no component calls `fetch` directly. It exposes one typed function per endpoint (`getJobs`, `uploadResume`, `scoreJob`, `analyzeResume`, `generateInterviewPrep`, etc.), all going through a shared `apiFetch<T>()` wrapper that:
- Never sets `Content-Type` when the body is `FormData` (the browser must set the multipart boundary itself).
- Applies a single request timeout via `AbortController` across every call (see §8 — this value was raised over the course of the project to accommodate slower AI-backed endpoints).
- Guards against non-JSON responses (proxy/error pages) before attempting to parse JSON.
- Unwraps the backend's `ApiResponse` envelope and throws a typed `ApiClientError(code, message)` on any `error` field or non-2xx status, which components catch to drive toast notifications.

`lib/types.ts` mirrors every backend schema — one new type added per feature (`ResumeAnalysisResponse`, `InterviewPrepResponse`, etc.) as it shipped.

### State Flow

No global state manager. Each page owns its own `useState`/`useEffect` data-fetching lifecycle and renders shared `ui/` components for loading (`Skeleton`, `LoadingSpinner`), empty (`EmptyState`), and error (`ErrorState`, `Toast`) states. The job detail page uses optimistic updates for status changes (update the UI immediately, roll back on a failed request) rather than waiting for the round-trip before reflecting the change.

There is no `components.json` (no shadcn/ui) and no `tailwind.config.ts` — Tailwind v4 is configured entirely through `postcss.config.mjs` and `@import "tailwindcss"` in `styles/globals.css`, using CSS custom properties for the dark theme.

---

## 4. AI Architecture

All four AI operations are implemented as methods on one class, `GeminiClient` (`app/ai/gemini_client.py`), each paired with a dedicated prompt template in `app/ai/prompts.py`. Centralizing them this way (Phase 2A) is what let three later AI features (job matching, gap analysis, interview prep) reuse the same retry/parsing machinery instead of each reimplementing it.

### 4.1 Skill Extraction
```text
Resume Upload (PDF) → PyMuPDF → raw text → GeminiClient.extract_skills(raw_text)
    → normalized skills array (stored as JSONB on the resume row)
```
Never raises to the caller on a malformed response — returns `[]` instead, so resume upload always succeeds even if the AI output is unusable.

### 4.2 Job Matching
```text
Job Description + Resume Skills → GeminiClient.match_job(job_description, skills)
    → match_score (0-100, clamped), missing_skills (≤5), match_summary (2 sentences)
```
Raises on structurally invalid output (this one path does propagate a failure — a bad score isn't allowed to silently become "0").

### 4.3 Resume Gap Analysis (Phase 6)
```text
Resume Text + Job Description (pasted by the user)
    → GeminiClient.analyze_resume_gap(resume_text, job_description)
    → match_score, summary, missing_skills, strengths, suggestions, ats_tips (each list ≤5)
```
A separate prompt from job matching, framed as a career-coach/technical-recruiter persona focused on resume-improvement advice rather than just a fit number.

### 4.4 Interview Preparation Generator (Phase 7)
```text
Active Resume Text + Job Description + Job Title + Company Name
    → InterviewPrepService.generate(job_id)
    → GeminiClient.generate_interview_prep(resume_text, job_description, job_title, company_name)
    → project_questions (≤8), technical_questions (≤8), behavioral_questions (≤6),
      topics_to_revise (≤8), interview_tips (≤6)
```
The request flow is intentionally isolated and fully stateless:
```text
POST /api/jobs/{job_id}/interview-prep
    → routers/interview_prep.py
    → InterviewPrepService.generate(job_id)
        → ResumeService.get_latest_with_text()  (active resume)
        → Job lookup from the database          (title + description + company)
    → GeminiClient.generate_interview_prep(...)
    → InterviewPrepResponse returned directly to the browser
```
No database write occurs, no cache is consulted, and no background task is launched. This is the most permissive parser of the four — every list field defaults to `[]` on malformed data rather than raising, since partial interview-prep results are still useful, unlike a partially-invalid match score.

The prompt itself explicitly front-loads project-specific questions as the highest-priority section (grounded strictly in resume-named projects, instructed never to invent one), and tells the model that returning fewer than the maximum item count is acceptable if the resume doesn't support more — prioritizing realism over hitting a quota.

### Prompt Structure

Every prompt is a plain Python string constant, rendered with `str.format()`, instructing Gemini to return **only** JSON with no markdown fences or preamble, and embedding the exact expected schema plus bounded output limits (max skills, max missing-skills, exact sentence counts, per-list item caps) directly in the instructions. Temperature is fixed at `0.1` across all four prompts to keep JSON output consistent and minimize hallucination.

### JSON Parsing

A shared `_extract_json_str()` helper tries, in order: (1) a fenced ` ```json ` code block, (2) the first `{`/`[` through its matching closing brace/bracket (handles leading prose Gemini sometimes adds despite instructions), (3) the raw string as a last resort. Each of the four methods then has its own dedicated validator on top of that shared extraction (clamping numeric ranges, truncating oversized lists, dropping non-string/empty items), with the strictness of "raise vs. return an empty/default value" tuned per feature based on how much a partial result is still useful.

### Retry Strategy

All four Gemini calls go through one shared retry wrapper: 3 attempts total, exponential backoff (1s → 2s → 4s) between attempts, retried only on signals recognized as transient (HTTP 429/500/502/503, rate-limit/quota messages, "unavailable", timeouts, connection errors). Any other exception aborts immediately without retrying. After all attempts are exhausted, a custom `AIError` is raised, wrapping the last underlying exception, which routers translate into a `502` response.

### Error Handling (AI-specific)

- Resume upload: AI failure → empty skills list, upload still succeeds (graceful degradation).
- Job match scoring: AI failure → `AIError` propagates to a `502` HTTP response (no silent fallback — a wrong score is worse than no score).
- Resume Gap Analysis / Interview Prep: AI failure → `502`, since both features are inherently "ask the AI, show the result" with nothing else to fall back to.
- Raw resume text and the API key are never written to logs, by design — only lengths, counts, and short truncated response snippets appear in log output.

---

## 5. Database Architecture

PostgreSQL 16. Three tables, no foreign keys or joins required for any current query — a deliberate simplification for a single-user tool (see §11).

```text
jobs          resumes          scrape_runs
```

| Table | Purpose | Key columns |
|---|---|---|
| `jobs` | One row per scraped listing; also holds match results and application-tracking fields directly (no separate `matches`/`applications` table) | `id`, `title`, `company`, `description`, `url` (unique — dedup key), `source`, `location`, `status`, `notes`, `match_score`, `missing_skills`, `match_summary`, `matched_at`, `resume_uploaded_at`, `posted_at`, `created_at`, `updated_at` |
| `resumes` | The single active resume (at most one row at a time) | `id`, `filename`, `raw_text`, `skills`, `uploaded_at` |
| `scrape_runs` | Append-only log, one row per source per sync attempt | `id`, `source`, `jobs_found`, `jobs_new`, `error`, `started_at`, `completed_at` |

**Indexes:** `jobs.status`, `jobs.source`, `jobs.match_score` (supports the dashboard's top-N query), a unique index on `jobs.url`, and a composite index on `scrape_runs(source, started_at)` (supports "latest run per source").

**Migrations:** a single Alembic revision (`cc9c2e74a08d_initial_schema.py`) creates all three tables as described above. No schema changes have been needed since — Phases 5, 6, and 7 all reuse these tables without modification; the Resume Gap Analyzer and Interview Prep Generator write nothing to the database at all.

**No FKs, no enums:** `status` and `source` are plain `VARCHAR`, validated at the Pydantic/service layer rather than via a database enum type — adding a new valid value never requires a migration. See §11 for the reasoning behind the no-FK, no-versioning, single-resume-row design overall.

---

## 6. Request Lifecycle

```text
Router receives request
        ↓
Validate input (Pydantic / FastAPI Query params)
        ↓
Call service (class instance or module-level function)
        ↓
Service queries DB / calls Gemini / calls a scraper
        ↓
Service returns a plain result or raises a domain exception
        ↓
Router translates domain exceptions → HTTPException
        ↓
Global exception handlers normalize every response to
    {"data": ..., "error": null | {"code", "message"}}
```

Example — `POST /api/jobs/{id}/score`:
```text
Router: get_active_resume dependency runs first (422 NO_RESUME if none)
        ↓
match_service.score_job(job_id, db)
        ↓
Cache check (see §10) → hit/stale: return stored result, no AI call
                       → miss: call Gemini, persist, return fresh result
        ↓
Router wraps result in ApiResponse
```

---

## 7. Data Flow

### Job Sync
```text
User clicks "Sync Jobs" → POST /api/scraper/run → ScraperService.run_all()
        ↓
RemoteOKScraper.run()  +  YCJobsScraper.run()   (independent; one failing doesn't stop the other)
        ↓
JobService.upsert_jobs()  → dedup by url, returns new job IDs
        ↓
Log one ScrapeRun row per source → return ScraperRunSummary to the browser
        ↓
(background) ScraperService.run_auto_score(new_job_ids) → match_service.score_job() per new job
```

### Resume Upload
```text
User uploads PDF → POST /api/resume → ResumeService.upload_resume()
        ↓
Validate content-type + size → PyMuPDF → raw text
        ↓
GeminiClient.extract_skills(raw_text)
        ↓
Delete any existing resume row, insert the new one
        ↓
Return filename, skills, uploaded_at
```

### Job Scoring
```text
User clicks "Score" → POST /api/jobs/{id}/score → match_service.score_job()
        ↓
No active resume? → 422 NO_RESUME
        ↓
Cache hit/stale (§10)? → return stored result
        ↓ (miss)
GeminiClient.match_job() → persist match_score, missing_skills, match_summary,
                            matched_at, resume_uploaded_at → return fresh result
```

### Resume Gap Analysis (Phase 6)
```text
User pastes a job description on /resume-review → POST /api/resume/analyze
        ↓
ResumeAnalysisService.analyze() — validate/truncate description, load active resume text
        ↓
GeminiClient.analyze_resume_gap() → return match_score, summary, missing_skills,
                                     strengths, suggestions, ats_tips
```
Nothing is written to the database — fully stateless, every call is a fresh AI invocation.

### Interview Preparation (Phase 7)
```text
User requests interview prep on a job detail page → POST /api/jobs/{id}/interview-prep
        ↓
InterviewPrepService.generate(job_id) — load job, load active resume text
        ↓
GeminiClient.generate_interview_prep() → return the five question/tip lists
```
Also fully stateless — see §4.4.

### Status / Notes Update
```text
PATCH /api/jobs/{id} → JobService.update_job()
        ↓
Update status and/or notes (both optional; invalid status → 422) → return updated record
```

### Dashboard Stats
```text
GET /api/dashboard/stats → DashboardService.get_stats()
        ↓
One aggregate query (counts/average/max/quality-tier buckets)
    + one indexed top-5-by-score query
        ↓
Return totals, quality breakdown, top matches — no per-row iteration in Python, regardless of job count
```

---

## 8. Performance Optimizations

- **YC Jobs scraper page-load strategy.** Originally waited for the page to reach a fully-idle network state before proceeding, which stalled for 20-25 seconds on this JS-heavy single-page app. Switched to waiting only for the DOM to parse plus an explicit wait for job-link elements to appear — the job list is confirmed rendered before extraction starts, without waiting on background requests that never fully quiesce.
- **YC Jobs card-ancestor lookup.** The original approach walked up to 8 levels of parent elements per job, one browser round-trip per level — for 30 jobs, up to 240 round-trips (~8-12 seconds). This was replaced with a single in-browser lookup per job (one round-trip each), cutting 30 jobs down to 30 round-trips total.
- **YC Jobs post-scroll wait.** A fixed wait after scrolling to trigger lazy-loaded content was reduced from 3 seconds to 500ms once it was confirmed the DOM-ready + selector-wait guarantee above already ensures the job list is present.
- **Frontend request timeout.** The API client's request timeout was raised over the course of the project (from an initial 15 seconds to 120 seconds) to accommodate the slower AI-backed endpoints — particularly interview-prep generation and the YC Jobs scrape — which can legitimately take longer than a typical CRUD request without indicating a failure.
- **Dashboard aggregation.** Every dashboard metric (totals, average/best score, applications submitted, quality-tier counts) is computed in a single aggregate SQL query using conditional counting expressions, plus one separate indexed top-5 query — two total queries regardless of how many jobs exist, avoiding per-row iteration in Python or N+1 query patterns as the job count grows.
- **Auto-scoring runs in the background**, not inline with the sync response — Gemini calls are too slow (10-30 seconds per job) to include in the HTTP response without risking client/proxy timeouts, so newly-scraped jobs are scored via `BackgroundTasks` after the response has already been sent.

---

## 9. Error Handling

- **Global exception handlers** (registered once in `app/main.py`) normalize every response — success or failure — into `{"data": ..., "error": null | {"code", "message"}}`:
  - `HTTPException` → the envelope shape above, using whatever `{code, message}` the raising code supplied (or a mapped generic code for FastAPI's own built-in HTTP errors).
  - `RequestValidationError` (Pydantic/FastAPI input validation) → `422` with a concatenated field-error message under code `VALIDATION_ERROR`.
  - Any other unhandled `Exception` → `500` with a generic `INTERNAL_ERROR` message — **stack traces never reach the client**.
- **Domain exceptions**, not HTTP concepts, are what services raise: `ValueError` (validation), `LookupError` (not found), and purpose-built classes (`JobNotFoundError`, `NoResumeError` in scoring; `JobNotFoundError` in interview prep). Routers are the only layer that knows about HTTP status codes — they catch these and translate.
- **AI failures** surface as `AIError` from `GeminiClient` after retries are exhausted, translated by routers to `502` — except in resume upload, where an AI failure is deliberately swallowed (empty skills list, upload still succeeds) rather than surfaced as an error at all. This asymmetry is intentional: a resume without extracted skills is still useful; a job score that silently failed would be misleading.

---

## 10. Caching Strategy

There is exactly **one** caching layer in the entire system: **job-match scores**, cached per resume version directly on the `jobs` table.

```text
_check_cache(job, resume):
    match_score is NULL                              → "miss"  (call Gemini)
    job.resume_uploaded_at == resume.uploaded_at      → "hit"   (return stored result, no AI call)
    job.resume_uploaded_at != resume.uploaded_at       → "stale" (return stored result, flagged
                                                          needs_rescore=true, still no AI call)
```

This means: re-opening an already-scored job never re-calls Gemini. Replacing the active resume does **not** retroactively invalidate or re-score existing jobs — it just changes what future cache-checks compare against, which is why "stale" jobs stay stale until explicitly re-scored.

**The Resume Gap Analyzer and Interview Prep Generator have no caching at all** — both are stateless by design (§4.3, §4.4); every invocation is a fresh Gemini call, and nothing is persisted to compare against on a future request. This is a deliberate simplicity trade-off for two features designed to be run occasionally against arbitrary input (any pasted job description; any job's prep material), not features expected to be re-queried repeatedly against unchanged input the way job scoring is.

Auto-scoring after a sync (§7, §8) reuses this exact same cache-check path — it calls the identical `score_job()` function used by manual scoring, so cache behavior, retry logic, and error handling are all shared, not reimplemented for the background case.

---

## 11. Design Principles

- **Routers stay thin; services own logic.** Established in Phase 1B specifically so every later feature could follow the same pattern without re-litigating where code belongs.
- **Single-user, single-active-resume.** No `users` table exists. Uploading a new resume deletes the old row and inserts the new one in the same transaction — there is no versioning or soft delete, by design, not by oversight.
- **No `matches`/`applications` tables.** Match results and application-tracking fields live directly on the `jobs` table. For one user, a job row *is* the application record — a join table would add complexity with no corresponding benefit at this scale.
- **Plain `VARCHAR`, not database enums**, for `status` and `source`. Validity is enforced at the Pydantic/service layer so that adding a new valid value never requires a schema migration.
- **Isolated-vertical pattern for additive features.** Phases 6 and 7 (Resume Gap Analyzer, Interview Prep Generator) were both built as fully separate schema/service/router/prompt stacks specifically so they could not accidentally break the original scoring/tracking/dashboard functionality — a deliberate low-risk strategy for adding features to a small, single-maintainer codebase.
- **Classes where state (a DB session) needs to be held; plain functions where it doesn't.** `match_service` is a module of functions, not a class, because nothing about job-match scoring needs instance state beyond the session passed into each call — this is a stylistic difference between services, not an inconsistency.
- **Graceful degradation is chosen deliberately, per feature, based on what a partial failure means.** A resume without extracted skills is still a stored, usable resume (fail soft). A job score that's structurally invalid is not a usable job score (fail loud). This asymmetry is intentional, not inconsistent — see §9.

---

## 12. Scalability Considerations

This architecture is intentionally **not** built for multi-user or high-throughput scale:
- No user/tenant partitioning — a single resume row for the whole system.
- Job scoring is one Gemini call per job with no batching; a large sync can mean many sequential background AI calls.
- The YC Jobs scraper launches a full headless browser synchronously inside a request-triggered service call — acceptable for an occasional personal sync, not for concurrent multi-user traffic.
- Dashboard queries are the one place scalability was explicitly engineered for — the aggregate + top-N query design (§8) stays at two total queries regardless of job count, rather than degrading as the job table grows.

---

## 13. Security Considerations

- **No authentication or authorization anywhere.** Anyone who can reach the backend can read/modify all data. Acceptable only because the tool is designed to run on `localhost` for one person.
- **API keys are read from environment variables only** and are never logged, along with raw resume text (§4, Error Handling).
- **Uploaded PDFs are validated** (content type, size, page count, encryption, minimum extractable text, a resume-content heuristic) before processing — reducing, not eliminating, the risk of processing arbitrary or malicious files.
- **CORS is currently hardcoded** to `http://localhost:3000` in the middleware configuration, so the backend is configured for local development only.
- **No rate limiting** on any endpoint, including the AI-backed ones, which could otherwise be triggered repeatedly at cost to the operator's own AI-provider quota/billing.

---

## 15. Folder Structure

### Backend

```text
backend/
├── pyproject.toml
├── alembic.ini
├── alembic/
│   ├── env.py
│   └── versions/
│       └── cc9c2e74a08d_initial_schema.py
│
├── app/
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── dependencies.py
│   │
│   ├── models/
│   │   ├── job.py
│   │   ├── resume.py
│   │   └── scrape_run.py
│   │
│   ├── schemas/
│   │   ├── job.py
│   │   ├── resume.py
│   │   ├── dashboard.py            ← Phase 5
│   │   ├── resume_analysis.py      ← Phase 6
│   │   └── interview_prep.py       ← Phase 7
│   │
│   ├── routers/
│   │   ├── health.py
│   │   ├── jobs.py
│   │   ├── resume.py
│   │   ├── scraper.py
│   │   ├── dashboard.py            ← Phase 5
│   │   ├── resume_analysis.py      ← Phase 6
│   │   └── interview_prep.py       ← Phase 7
│   │
│   ├── services/
│   │   ├── job_service.py
│   │   ├── resume_service.py
│   │   ├── match_service.py
│   │   ├── scraper_service.py
│   │   ├── dashboard_service.py           ← Phase 5
│   │   ├── resume_analysis_service.py     ← Phase 6
│   │   └── interview_prep_service.py      ← Phase 7
│   │
│   ├── scrapers/
│   │   ├── base.py
│   │   ├── remoteok.py
│   │   ├── yc_jobs.py
│   │   └── dashboard.py
│   │
│   └── ai/
│       ├── gemini_client.py
│       └── prompts.py
│
└── tests/
    ├── conftest.py
    ├── test_job_service.py
    ├── test_resume_service.py
    ├── test_match_service.py
    ├── test_scraper_service.py
    ├── test_dashboard_service.py             ← Phase 5
    └── test_resume_analysis_service.py       ← Phase 6
    (no test_interview_prep_service.py)
```

### Frontend

```text
frontend/
├── package.json
├── next.config.ts          (rewrites /api/* → API_BASE_URL; proxyTimeout set for long-running calls)
├── postcss.config.mjs      (Tailwind v4 — no tailwind.config.ts or components.json)
│
├── app/
│   ├── layout.tsx          (nav: Dashboard / Jobs / Resume / Resume Review)
│   ├── template.tsx        (page-fade transition wrapper)
│   ├── page.tsx            (landing page — see §3 correction note)
│   ├── dashboard/
│   │   └── page.tsx        (the actual dashboard — see §3 correction note)
│   ├── jobs/
│   │   ├── page.tsx
│   │   └── [id]/page.tsx
│   ├── resume/
│   │   └── page.tsx
│   └── resume-review/      ← Phase 6
│       └── page.tsx
│
├── components/
│   ├── ui/              (Button, Card, Badge, LoadingSpinner, EmptyState, ErrorState,
│   │                      PageHeader, Toast, Skeleton)
│   ├── jobs/             (JobCard, JobList, ScoreBadge, StatusBadge, StatusSelect,
│   │                      NeedsRescoreBadge, RecommendationBadge, ResumeRequiredBadge)
│   ├── resume/           (SkillChip, ResumeInfoCard, ResumeUploader, ResumeOverviewCard,
│   │                      ResumePageHeader, ResumeSkillsCard, ResumeUploadCard,
│   │                      ResumeUploadProgress, ResumeEmptyPanel)
│   ├── dashboard/        (TopMatches, MatchQualityBreakdown)        ← Phase 5
│   ├── resume-review/    (JobDescriptionForm, MatchScoreCard,
│   │                      SkillTagSection, BulletListSection)       ← Phase 6
│   └── interview-prep/   (InterviewPrepPanel)                        ← Phase 7
│
├── lib/
│   ├── api.ts               (all fetch calls; components never call fetch directly)
│   ├── types.ts
│   └── categorizeSkills.ts
│
└── hooks/                (empty — no custom hooks currently exist)
```

Frontend rules: pages import components and the API layer only; components import types and never call `fetch` directly; all HTTP calls go through `lib/api.ts`.

---

## 15. Dependency Versions

| Package | Version |
|---|---|
| Python | 3.12 |
| FastAPI | 0.115.5 |
| uvicorn | 0.32.1 |
| SQLAlchemy | 2.0.36 |
| Alembic | 1.14.0 |
| psycopg2-binary | 2.9.10 |
| PyMuPDF | 1.24.14 |
| Playwright | 1.48.0 |
| httpx | 0.27.2 |
| pydantic-settings | 2.6.1 |
| google-generativeai | 0.8.3 |
| Node.js | 20 LTS |
| Next.js | 15.5.x |
| React | 19.0.x |
| TypeScript | 5.x |
| Tailwind CSS | 4.x |

---

## 16. Local Development

`docker-compose.yml` runs PostgreSQL only. Frontend and backend both run directly on the host — there are no Dockerfiles for either.

```yaml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: internship_hunter
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
```

### Environment Variables

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/internship_hunter
GEMINI_API_KEY=your_api_key
GEMINI_MODEL=gemini-2.5-flash
APP_ENV=development
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:3000
```

`CORS_ORIGINS` is parsed and validated by the settings layer but not currently consumed by the CORS middleware itself.