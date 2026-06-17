# Architecture

---

## Overview

Single-user personal tool.No authentication.No background workers.No task queue.No scheduler.

Backend runs synchronously — scrapes run on request, scoring runs on request, results are cached in PostgreSQL.

```text
Browser (Next.js 15)
    │
    │ HTTP/JSON
    ▼
FastAPI Backend
    ├── routers/     ← HTTP only
    ├── services/    ← business logic
    ├── scrapers/    ← RemoteOK + YC Jobs
    └── ai/          ← Gemini integration
    │
    ▼
PostgreSQL
(jobs, resumes, scrape_runs)
```

---

# System Components

## Frontend — Next.js 15

Uses App Router.

### Routes

| Route      | Purpose                                         |
| ---------- | ----------------------------------------------- |
| /jobs      | Job list with filters, sorting and score badges |
| /jobs/[id] | Job details, score results, notes and status    |
| /resume    | Resume upload and extracted skills              |

Frontend communicates directly with FastAPI.

No Next.js API routes.

No proxy layer.

---

## Backend — FastAPI

Routers remain thin.

All business logic lives inside services.

### Request Lifecycle

```text
Router receives request
        ↓
Validate input (Pydantic)
        ↓
Call Service
        ↓
Service queries DB
        ↓
Service calls Gemini / Scraper
        ↓
Return result
        ↓
Router serializes response
        ↓
JSON Response
```

### Architecture Rules

* Routers never query the database directly.
* Services never import routers.
* Business logic belongs in services.
* Services are independently testable.

---

## AI Layer — Gemini

Only two AI operations exist in MVP.

### Skill Extraction

```text
Resume Upload
        ↓
Gemini
        ↓
Skills Array
```

### Job Matching

```text
Job Description
+
Resume Skills
        ↓
Gemini
        ↓
Match Score
Missing Skills
Summary
```

Gemini responses are parsed and stored in PostgreSQL.

---

## Scrapers

### RemoteOK

Uses:

```text
httpx
```

Calls RemoteOK public API.

No browser required.

---

### YC Jobs

Uses:

```text
Playwright
```

Launches headless Chromium.

Extracts job data.

Closes browser.

---

### Scraper Rules

Both scrapers implement a common interface.

```python
run() -> list[JobData]
```

Both are orchestrated by:

```text
scraper_service.py
```

A failure in one source must not stop the other source.

Every run is logged into:

```text
scrape_runs
```

---

## Database

PostgreSQL 16

Three tables only.

```text
jobs

resumes

scrape_runs
```

No joins required for MVP.

No audit tables.

No soft deletes.

No history tracking.

---

# Folder Structure

## Backend

```text
backend/
├── pyproject.toml
├── alembic.ini
│
├── alembic/
│   └── versions/
│
└── app/
    ├── main.py
    ├── config.py
    ├── database.py
    │
    ├── models/
    │   ├── job.py
    │   ├── resume.py
    │   └── scrape_run.py
    │
    ├── schemas/
    │   ├── job.py
    │   └── resume.py
    │
    ├── routers/
    │   ├── jobs.py
    │   ├── resumes.py
    │   └── scraper.py
    │
    ├── services/
    │   ├── job_service.py
    │   ├── resume_service.py
    │   ├── match_service.py
    │   └── scraper_service.py
    │
    ├── scrapers/
    │   ├── base.py
    │   ├── remoteok.py
    │   └── yc_jobs.py
    │
    └── ai/
        ├── gemini_client.py
        └── prompts.py
```

---

### Service Responsibilities

#### job_service.py

```text
list_jobs()
get_job()
update_job()
upsert_jobs()
```

---

#### resume_service.py

```text
upload_resume()
get_resume()
delete_resume()
extract_text()
```

---

#### match_service.py

```text
score_job()
validate_cache()
detect_stale_scores()
```

---

#### scraper_service.py

```text
run_all_scrapers()
persist_jobs()
log_scrape_run()
```

---

### Import Rules

Allowed:

```text
routers
    ↓
services

services
    ↓
models

services
    ↓
ai

services
    ↓
scrapers
```

Not Allowed:

```text
router → router

service → router

scraper → service
```

---

## Frontend

```text
frontend/
├── package.json
├── next.config.ts
├── tailwind.config.ts
├── components.json
│
├── app/
│   ├── layout.tsx
│   ├── jobs/
│   │   ├── page.tsx
│   │   └── [id]/page.tsx
│   │
│   └── resume/
│       └── page.tsx
│
├── components/
│   ├── ui/
│   ├── JobCard.tsx
│   ├── JobList.tsx
│   ├── MatchResult.tsx
│   ├── StatusDropdown.tsx
│   └── ResumeUploader.tsx
│
├── lib/
│   └── api.ts
│
└── types/
    ├── job.ts
    ├── resume.ts
    └── api.ts
```

---

### Frontend Rules

Pages:

```text
Import Components
Import API Layer
```

Components:

```text
Import Types
```

API calls:

```text
Only through lib/api.ts
```

Components never call fetch directly.

---

# Data Flows

## Job Sync

```text
User clicks Sync Jobs
        ↓
POST /api/scraper/run
        ↓
scraper_service.run_all_scrapers()

        ↓

RemoteOKScraper.run()

        ↓

YCJobsScraper.run()

        ↓

job_service.upsert_jobs()

        ↓

Log scrape_runs

        ↓

Return summary
```

---

## Resume Upload

```text
User uploads PDF
        ↓
POST /api/resume
        ↓
resume_service.upload_resume()

        ↓

PyMuPDF

        ↓

Extract Raw Text

        ↓

Gemini Skill Extraction

        ↓

Replace Existing Resume

        ↓

Store Resume

        ↓

Return Skills
```

---

## Job Scoring

```text
User clicks Score
        ↓
POST /api/jobs/{id}/score
        ↓
match_service.score_job()

        ↓

Get Active Resume

        ↓

No Resume?
        ↓
422 Error

        ↓

Check Cache

IF

job.match_score exists

AND

job.resume_uploaded_at
==
current_resume.uploaded_at

        ↓

Return Cached Result

ELSE

        ↓

Call Gemini

        ↓

Generate

- Match Score
- Missing Skills
- Summary

        ↓

Update Job

- match_score
- missing_skills
- match_summary
- matched_at
- resume_uploaded_at

        ↓

Return Result
```

---

## Status Update

```text
PATCH /api/jobs/{id}

        ↓

job_service.update_job()

        ↓

Update:

- status
- notes

        ↓

Return Updated Record
```

---

# Dependency Versions

| Package           | Version |
| ----------------- | ------- |
| Python            | 3.12    |
| FastAPI           | 0.115.x |
| SQLAlchemy        | 2.x     |
| Alembic           | 1.13.x  |
| PyMuPDF           | 1.24.x  |
| Playwright        | 1.44.x  |
| httpx             | 0.27.x  |
| pydantic-settings | 2.x     |
| Node.js           | 20 LTS  |
| Next.js           | 15.x    |
| TypeScript        | 5.x     |
| Tailwind CSS      | 3.x     |

---

# Local Development

docker-compose runs PostgreSQL only.

Frontend and backend run directly on host machine.

### docker-compose.yml

```yaml
services:
  db:
    image: postgres:16

    environment:
      POSTGRES_DB: internship_hunter
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres

    ports:
      - "5432:5432"

    volumes:
      - postgres_data:/var/lib/postgresql/data
```

---

## Environment Variables

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/internship_hunter

GEMINI_API_KEY=your_api_key

NEXT_PUBLIC_API_URL=http://localhost:8000
```
