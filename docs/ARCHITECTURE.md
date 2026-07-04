# Architecture

---

## Overview

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
    └── ai/           ← Gemini client + prompt templates
    │
    ▼
PostgreSQL 16
(jobs, resumes, scrape_runs)
```

---

# System Components

## Frontend — Next.js 15

App Router, all pages are client components (`"use client"`) since every page needs interactivity (sync button, filters, forms) rather than static content.

### Routes

| Route        | Purpose                                                              |
| ------------ | --------------------------------------------------------------------- |
| `/`          | Dashboard — live stat cards, Sync Jobs button, top matches, match-quality breakdown |
| `/jobs`      | Job list — server-side filters (status/source/scored), sorting, pagination |
| `/jobs/[id]` | Job detail — description, Score button, match result, status/notes editing |
| `/resume`    | Resume upload (drag-and-drop), extracted skills, delete                |

Frontend communicates with FastAPI through a Next.js `rewrites()` proxy (`/api/*` → `http://localhost:8000/api/*`) — not through separate Next.js API routes.

---

## Backend — FastAPI

Routers stay thin. All business logic lives in services.

### Request Lifecycle

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

### Architecture Rules

- Routers never query the database directly.
- Services never import routers.
- Scrapers never touch the database or import services — they only return normalized `list[dict]` job data; `ScraperService` is responsible for persistence.
- All business logic lives in services; services are unit-testable without a running FastAPI app.

---

## AI Layer — Gemini

Two AI operations, both implemented on `GeminiClient` (`app/ai/gemini_client.py`):

### Skill Extraction

```text
Resume Upload (PDF)
        ↓
PyMuPDF → raw text
        ↓
GeminiClient.extract_skills(raw_text)
        ↓
Normalized skills array (JSONB)
```

### Job Matching

```text
Job Description + Resume Skills
        ↓
GeminiClient.match_job(job_description, skills)
        ↓
match_score, missing_skills, match_summary
```

Both calls go through `GeminiClient._call_with_retry()`: exponential backoff (1s, 2s, 4s) across 3 attempts, retrying on HTTP 429/500/502/503, raising `AIError` after the final failure. Temperature is fixed at `0.1` for both prompts to keep JSON output consistent.

---

## Scrapers

Both scrapers implement the same interface:

```python
class BaseScraper(ABC):
    def run(self) -> list[dict]: ...
```

### RemoteOK (`scrapers/remoteok.py`)
Calls RemoteOK's public JSON API directly via `httpx`. No browser required, no ToS concerns.

### YC Jobs (`scrapers/yc_jobs.py`)
Launches headless Chromium via Playwright, navigates to Work at a Startup's job listing (filtered to `role=eng&type=intern`), waits for job link anchors to render (client-side SPA — `domcontentloaded` alone isn't enough), walks each anchor's ancestor chain to find its containing card, and extracts title/company/location/description/posted-at per card. Closes the browser in a `finally` block regardless of outcome.

### Orchestration
`ScraperService.run_all()` runs both scrapers, isolates failures per source (one source erroring never stops the other), persists results via `JobService.upsert_jobs()`, and logs one `ScrapeRun` row per source per sync attempt via `_persist_run()`.

---

## Auto-Scoring After Sync

Added after the original MVP scope (originally listed as out of scope in `PRD.md`; implemented once the dashboard needed fresh scores to show something meaningful):

```text
POST /api/scraper/run
        ↓
ScraperService.run_all()  — scrapes, persists, returns summary + new job IDs
        ↓
Router returns the response to the browser immediately
        ↓
FastAPI BackgroundTasks calls ScraperService.run_auto_score(new_job_ids)
        ↓
_auto_score_new_jobs(): for each new job, match_service.score_job()
        (skipped with no error if no resume is uploaded;
         one job's AIError does not abort the rest)
```

This uses a fresh DB session inside the background task, independent of the request-scoped session used to build the response — the response is already on the wire by the time scoring starts.

---

## Database

PostgreSQL 16. Three tables, no joins required for any current query:

```text
jobs          resumes          scrape_runs
```

No audit tables, no soft deletes, no history tracking — all intentionally out of scope for a single-user tool. Full schema in `DATABASE.md`.

---

# Folder Structure

## Backend

```text
backend/
├── pyproject.toml
├── alembic.ini
│
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
│   │   └── dashboard.py
│   │
│   ├── routers/
│   │   ├── health.py
│   │   ├── jobs.py
│   │   ├── resume.py
│   │   ├── scraper.py
│   │   └── dashboard.py
│   │
│   ├── services/
│   │   ├── job_service.py
│   │   ├── resume_service.py
│   │   ├── match_service.py
│   │   ├── scraper_service.py
│   │   └── dashboard_service.py
│   │
│   ├── scrapers/
│   │   ├── base.py
│   │   ├── remoteok.py
│   │   └── yc_jobs.py
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
    └── test_dashboard_service.py
```

---

### Service Responsibilities

The service layer mixes classes (stateful, hold a DB session) and a module of functions (`match_service`) — this reflects how each grew, not an inconsistency to "fix":

#### `job_service.JobService`
```text
list_jobs()      get_job()      update_job()
delete_job()     upsert_jobs()
```

#### `resume_service.ResumeService`
```text
upload_resume()  get_latest()  get_by_id()  delete_latest()
```

#### `match_service` (module-level functions, not a class)
```text
score_job()  recommendation_label()
```
Raises `JobNotFoundError` / `NoResumeError` — routers translate these to HTTP 404 / 422.

#### `scraper_service.ScraperService`
```text
run_all()  get_status()  run_auto_score()
```

#### `dashboard_service.DashboardService`
```text
get_stats()
```

---

### Import Rules

Allowed:
```text
routers → services → models
services → ai
services → scrapers (ScraperService only, to call .run())
```

Not allowed:
```text
router → router
service → router
scraper → service    (scrapers are pure — no DB, no service calls)
```

---

## Frontend

```text
frontend/
├── package.json
├── next.config.ts        (rewrites /api/* → localhost:8000; proxyTimeout set for long-running sync calls)
├── postcss.config.mjs     (Tailwind v4 — no tailwind.config.ts or components.json)
│
├── app/
│   ├── layout.tsx
│   ├── page.tsx            (dashboard)
│   ├── jobs/
│   │   ├── page.tsx
│   │   └── [id]/page.tsx
│   └── resume/
│       └── page.tsx
│
├── components/
│   ├── ui/         (Button, Card, Badge, LoadingSpinner, EmptyState, ErrorState, PageHeader, Toast)
│   ├── jobs/       (JobCard, JobList, ScoreBadge, StatusBadge, NeedsRescoreBadge, RecommendationBadge)
│   ├── resume/     (SkillChip, ResumeInfoCard, ResumeUploader)
│   └── dashboard/  (TopMatches, MatchQualityBreakdown)
│
└── lib/
    ├── api.ts       (all fetch calls; components never call fetch directly)
    └── types.ts
```

Note: there is no `components.json` (no shadcn/ui) and no `tailwind.config.ts` (Tailwind v4 is configured entirely through `postcss.config.mjs` and `@import "tailwindcss"` in `styles/globals.css`, using CSS custom properties for the dark theme).

---

### Frontend Rules

- Pages import components and the API layer only.
- Components import types; they never call `fetch` directly.
- All HTTP calls go through `lib/api.ts`.

---

# Data Flows

## Job Sync

```text
User clicks "Sync Jobs"
        ↓
POST /api/scraper/run
        ↓
ScraperService.run_all()
        ↓
RemoteOKScraper.run()   +   YCJobsScraper.run()   (independent; one failing doesn't stop the other)
        ↓
JobService.upsert_jobs()   → dedup by url, returns new job IDs
        ↓
Log one ScrapeRun row per source
        ↓
Return ScraperRunSummary to the browser
        ↓
(background) ScraperService.run_auto_score(new_job_ids)
        ↓
match_service.score_job() for each new job
```

## Resume Upload

```text
User uploads PDF
        ↓
POST /api/resume
        ↓
ResumeService.upload_resume()
        ↓
Validate content-type + size (≤ 5 MB)
        ↓
PyMuPDF → raw text
        ↓
GeminiClient.extract_skills(raw_text)
        ↓
Delete any existing resume row, insert the new one
        ↓
Return filename, skills, uploaded_at
```

## Job Scoring

```text
User clicks "Score"
        ↓
POST /api/jobs/{id}/score
        ↓
match_service.score_job()
        ↓
No active resume? → 422 NO_RESUME
        ↓
job.match_score set AND job.resume_uploaded_at == resume.uploaded_at?
        ├── yes → return cached result (cached: true)
        └── no  → GeminiClient.match_job() → persist match_score,
                  missing_skills, match_summary, matched_at,
                  resume_uploaded_at → return fresh result
```

## Status / Notes Update

```text
PATCH /api/jobs/{id}
        ↓
JobService.update_job()
        ↓
Update status and/or notes (both optional; invalid status → 422)
        ↓
Return updated record
```

## Dashboard Stats

```text
GET /api/dashboard/stats
        ↓
DashboardService.get_stats()
        ↓
One aggregate query (COUNT/AVG/MAX + CASE WHEN buckets)
        +
One indexed top-5-by-score query
        ↓
Return totals, quality breakdown, top matches — no N+1 regardless of job count
```

---

# Dependency Versions

| Package             | Version   |
| -------------------- | --------- |
| Python                | 3.12      |
| FastAPI               | 0.115.5   |
| uvicorn               | 0.32.1    |
| SQLAlchemy            | 2.0.36    |
| Alembic               | 1.14.0    |
| psycopg2-binary       | 2.9.10    |
| PyMuPDF               | 1.24.14   |
| Playwright            | 1.48.0    |
| httpx                 | 0.27.2    |
| pydantic-settings     | 2.6.1     |
| google-generativeai   | 0.8.3     |
| Node.js               | 20 LTS    |
| Next.js               | 15.5.x    |
| React                 | 19.0.x    |
| TypeScript            | 5.x       |
| Tailwind CSS          | 4.x       |

---

# Local Development

`docker-compose.yml` runs PostgreSQL only. Frontend and backend both run directly on the host.

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

## Environment Variables

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/internship_hunter
GEMINI_API_KEY=your_api_key
GEMINI_MODEL=gemini-2.5-flash
APP_ENV=development
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:3000
```

Full variable reference in `DEPLOYMENT.md`.