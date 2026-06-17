# Tasks

Build plan for the MVP.

Four phases.

Each task should be small enough to finish in one sitting.

**Status key:**

* [ ] Todo
* [x] Done
* [-] Skipped

---

# Phase 0A — Backend Foundation

## Goal

Database runs.

FastAPI starts.

Health endpoint works.

### Project Setup

* [ ] Create repository
* [ ] Create `backend/`
* [ ] Create `frontend/`
* [ ] Create `.env.example`
* [ ] Create `.gitignore`
* [ ] Create `README.md`

### Dependencies

* [ ] Create `pyproject.toml`
* [ ] Install FastAPI
* [ ] Install SQLAlchemy 2.x
* [ ] Install Alembic
* [ ] Install PostgreSQL driver
* [ ] Install PyMuPDF
* [ ] Install Playwright
* [ ] Install httpx
* [ ] Install pydantic-settings
* [ ] Install google-generativeai

### Configuration

* [ ] Create `app/config.py`
* [ ] Create typed Settings class
* [ ] Load environment variables
* [ ] Validate required settings

### Database

* [ ] Create `app/database.py`
* [ ] Configure SQLAlchemy engine
* [ ] Configure SessionLocal
* [ ] Create `get_db()` dependency

### FastAPI

* [ ] Create `app/main.py`
* [ ] Configure FastAPI app
* [ ] Configure CORS
* [ ] Register routers

### Health Endpoint

* [ ] Create `routers/health.py`
* [ ] Implement `GET /api/health`
* [ ] Verify database connectivity
* [ ] Return proper health response

### Alembic

* [ ] Configure Alembic
* [ ] Create `alembic.ini`
* [ ] Create `alembic/env.py`

### Docker

* [ ] Create `docker-compose.yml`
* [ ] Add PostgreSQL 16 service
* [ ] Verify container starts

### Verification

* [ ] Run PostgreSQL
* [ ] Start FastAPI
* [ ] Verify `/api/health`
* [ ] Verify database connection

---

# Phase 0B — Frontend Foundation

## Goal

Next.js starts.

Navigation works.

Frontend can communicate with backend.

### Setup

* [ ] Create Next.js 15 app
* [ ] Enable TypeScript
* [ ] Configure Tailwind CSS
* [ ] Configure ESLint

### UI

* [ ] Install shadcn/ui
* [ ] Initialize shadcn/ui

### Types

#### API

* [ ] Create `types/api.ts`
* [ ] Create `ApiResponse<T>`
* [ ] Create `ApiError`
* [ ] Create pagination types

#### Job

* [ ] Create `types/job.ts`
* [ ] Create `Job`
* [ ] Create `JobListItem`
* [ ] Create `JobStatus`
* [ ] Create `JobFilters`
* [ ] Create `ScoreResult`

#### Resume

* [ ] Create `types/resume.ts`
* [ ] Create `Resume`
* [ ] Create `Skill`

### API Client

* [ ] Create `lib/api.ts`
* [ ] Create typed fetch wrapper
* [ ] Add error handling
* [ ] Add helper methods

### Layout

* [ ] Create root layout
* [ ] Add navigation
* [ ] Add links:

  * [ ] Jobs
  * [ ] Resume

### Verification

* [ ] Frontend starts
* [ ] Navigation works
* [ ] Health endpoint reachable from frontend

---

# Phase 1 — Job Collection

## Goal

Real jobs appear in database and UI.

---

## Backend Models

### Jobs

* [ ] Create `models/job.py`
* [ ] Implement all columns from DATABASE.md

### Scrape Runs

* [ ] Create `models/scrape_run.py`

### Schemas

* [ ] Create `schemas/job.py`
* [ ] Create `JobListItem`
* [ ] Create `JobResponse`
* [ ] Create `ScrapeRunResponse`

---

## Scrapers

### Base Scraper

* [ ] Create `scrapers/base.py`
* [ ] Define `run() -> list[dict]`

### RemoteOK

* [ ] Create `scrapers/remoteok.py`
* [ ] Fetch API response
* [ ] Parse jobs
* [ ] Normalize fields

### YC Jobs

* [ ] Create `scrapers/yc_jobs.py`
* [ ] Launch Playwright
* [ ] Extract jobs
* [ ] Normalize fields
* [ ] Handle timeout gracefully
* [ ] Close browser

---

## Services

### Job Service

* [ ] Create `job_service.py`

Functions:

* [ ] list_jobs()
* [ ] get_job()
* [ ] update_job()
* [ ] upsert_jobs()

### Scraper Service

* [ ] Create `scraper_service.py`

Functions:

* [ ] run_all_scrapers()
* [ ] persist_jobs()
* [ ] log_scrape_run()

---

## Routers

### Scraper Router

* [ ] POST `/api/scraper/run`
* [ ] GET `/api/scraper/status`

### Jobs Router

* [ ] GET `/api/jobs`
* [ ] GET `/api/jobs/{id}`

### Pagination

* [ ] page
* [ ] page_size
* [ ] total count

---

## Frontend

### Components

* [ ] JobCard
* [ ] JobList

### Jobs Page

* [ ] Fetch jobs
* [ ] Render jobs
* [ ] Add sync button
* [ ] Refresh list after sync

### Job Detail

* [ ] Create `/jobs/[id]`
* [ ] Display job description
* [ ] Display metadata
* [ ] Add score placeholder

### Pagination UI

* [ ] Previous page
* [ ] Next page
* [ ] Page size selector
* [ ] Total jobs count

### Phase Complete

* [ ] Sync Jobs works
* [ ] Jobs appear in UI
* [ ] Job detail page works

---

# Phase 2 — Resume Upload & Job Scoring

## Goal

Upload resume.

Extract skills.

Score jobs.

Track application status.

---

## Resume

### Model

* [ ] Create `models/resume.py`

### Schema

* [ ] Create `schemas/resume.py`

### Gemini Client

* [ ] Create `ai/gemini_client.py`

Functions:

* [ ] extract_skills()
* [ ] match_job()

Features:

* [ ] Retry on 429
* [ ] Retry on 503
* [ ] Exponential backoff
* [ ] Raise AIError on failure

### Prompts

* [ ] Create `ai/prompts.py`

Contains:

* [ ] SKILL_EXTRACTION_PROMPT
* [ ] JOB_MATCH_PROMPT

### Resume Service

* [ ] upload_resume()
* [ ] get_resume()
* [ ] delete_resume()
* [ ] extract_text()

### Resume Router

* [ ] POST `/api/resume`
* [ ] GET `/api/resume`
* [ ] DELETE `/api/resume`

### Upload Validation

* [ ] PDF only
* [ ] Maximum size 5 MB

---

## Job Scoring

### Match Service

* [ ] Create `match_service.py`

Functions:

* [ ] score_job()
* [ ] validate_cache()
* [ ] detect_stale_scores()

### Cache Rules

Return cached result only when:

```text
job.match_score exists

AND

job.resume_uploaded_at
==
current_resume.uploaded_at
```

Otherwise:

```text
Needs Re-score
↓
Call Gemini Again
```

### Router

* [ ] POST `/api/jobs/{id}/score`
* [ ] PATCH `/api/jobs/{id}`

---

## Frontend

### Resume

* [ ] ResumeUploader component
* [ ] Resume page
* [ ] Skills display

### Match Result

* [ ] Score display
* [ ] Missing skills
* [ ] Summary

### Job Detail

* [ ] Score button
* [ ] Display match result
* [ ] Display re-score warning

### Status Tracking

* [ ] StatusDropdown
* [ ] PATCH status
* [ ] PATCH notes

### Filters

* [ ] Filter by status
* [ ] Filter by source
* [ ] Scored only toggle

### Phase Complete

* [ ] Resume upload works
* [ ] Skills extracted
* [ ] Score generated
* [ ] Cache works
* [ ] Re-score detection works
* [ ] Status persists
* [ ] Notes persist

---

# Phase 3 — Polish

## Goal

Reliable enough for daily use.

---

## Backend

* [ ] Handle scraper failures
* [ ] Handle Gemini failures
* [ ] Return proper error codes
* [ ] Validate uploads
* [ ] Add service tests
* [ ] Mock Gemini in tests

---

## Frontend

### Loading States

* [ ] Job list loading
* [ ] Job detail loading
* [ ] Resume loading

### Empty States

* [ ] No jobs
* [ ] No resume
* [ ] No scores

### Error Handling

* [ ] Sync error toast
* [ ] Score error toast
* [ ] Upload error toast

### Sorting

* [ ] Null scores sorted last

### Resume Delete

* [ ] Confirmation dialog

---

## Documentation

* [ ] Finalize README
* [ ] Verify docs consistency
* [ ] Verify API examples
* [ ] Update .env.example

---

# MVP Completion Checklist

* [ ] Jobs sync from RemoteOK
* [ ] Jobs sync from YC Jobs
* [ ] Duplicate URLs ignored
* [ ] Scraper failures isolated
* [ ] Resume upload works
* [ ] Skills extracted
* [ ] Resume replacement works
* [ ] Job scoring works
* [ ] Cached scoring works
* [ ] Re-score detection works
* [ ] Status updates persist
* [ ] Notes persist
* [ ] Health endpoint verifies DB
* [ ] No secrets committed
* [ ] .env.example complete
* [ ] README complete
