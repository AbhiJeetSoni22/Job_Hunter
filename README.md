# AI Internship Hunter

An AI-powered job discovery platform that discovers software-engineering internships and jobs from multiple sources, scores them against each user's resume with Google Gemini, and tracks application pipelines with complete multi-user data isolation.

> This README is generated from the actual codebase (backend `app/`, frontend `app/`, `alembic/versions/`, `tests/`). All descriptions reflect the current implementation.

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running Locally](#running-locally)
- [Cleanup Management Command](#cleanup-management-command)
- [Running Tests](#running-tests)
- [Deployment](#deployment)
- [Screenshots](#screenshots)
- [Documentation Index](#documentation-index)
- [Roadmap](#roadmap)

## Overview

AI Internship Hunter is a FastAPI + Next.js application built with multi-user data isolation and authentication. It:

1. Accepts a PDF resume, extracts text (PyMuPDF), and extracts a normalized skills list from it using Gemini AI.
2. Scrapes internship and entry-level job listings from RemoteOK and Y Combinator's Work at a Startup, deduplicating listings by canonical URL.
3. Automatically scores newly inserted jobs against the active resume in the background, persisting progress in a `scoring_runs` table that frontends poll via `GET /api/scraper/scoring-status`.
4. Manages job expiration tracking (`last_seen_at`, `missing_sync_count`, `expired_at`) and excludes expired jobs from default listings and dashboard metrics.
5. Provides an application status workflow: `saved -> applied -> interview -> offer` (or `rejected`) with notes.
6. Surfaces a recommendation dashboard (`GET /api/dashboard/stats`) with aggregate metrics, match quality breakdowns, and top matches.
7. Executes on-demand AI tools: a **Resume Gap Analyzer** (`POST /api/resume/analyze`) and an **AI Interview Prep Generator** (`POST /api/jobs/{job_id}/interview-prep`).

There is no multi-user authentication layer by design — the system is optimized for a single user's personal job search.

## Key Features

| Feature | Summary |
|---|---|
| Resume Upload & Parsing | PDF upload -> PyMuPDF text extraction -> Gemini skill extraction. Uploading replaces the previous active resume. |
| Multi-Source Job Scraping | RemoteOK API + YC "Work at a Startup" (Playwright). Deduplicated by canonical URL across sources. |
| Persistent Background Scoring | Scraper sync creates a `ScoringRun` row (`running` \| `completed`) tracked via FastAPI `BackgroundTasks`. Polled via `GET /api/scraper/scoring-status`. |
| Job Lifecycle & Expiration | Tracks missing sync occurrences. Jobs missing for 2 consecutive syncs are marked expired. Filtered via `include_expired` flag. |
| Cleanup CLI Command | Executable management script (`python -m app.cleanup [--days 30]`) to purge un-annotated, saved expired jobs older than N days. |
| Application Tracking | PATCH job status and notes (`saved`, `applied`, `interview`, `offer`, `rejected`). |
| Recommendation Dashboard | Aggregate metrics computed via optimized SQL queries: active job totals, scored count, average/best score, match tiers, top 5 matches. |
| Resume Gap Analyzer | Paste a job description to get a fit score, missing skills, strengths, resume improvement suggestions, and ATS tips. |
| AI Interview Prep Generator | Generates grounded project questions, technical questions, behavioral questions, revision topics, and interview tips per job. |

See [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md) for detailed implementation status and [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for technical design details.

## Architecture

```mermaid
flowchart LR
    A[Next.js Frontend] -->|"/api/* (rewrite proxy)"| B[FastAPI Routers]
    B --> C[Service Layer]
    C --> D[GeminiClient]
    C --> E[SQLAlchemy ORM]
    E --> F[(PostgreSQL Database)]
    D --> G[(Google Gemini API)]
    C --> H[Scrapers: RemoteOK / YC Jobs]
    H --> I[(External Job Sources)]
```

Routers contain no business logic or database access — they validate HTTP requests and delegate to services. Services raise Python exceptions (`ValueError`, `LookupError`, `AIError`) which global FastAPI handlers format into standard `ApiResponse` envelopes (`{ "data": ..., "error": ... }`). Full details in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Tech Stack

**Backend**
- Python 3.12+, FastAPI 0.115+, Uvicorn
- SQLAlchemy 2.x (typed `Mapped[...]` models) + Alembic migrations
- PostgreSQL (JSONB + native UUID columns; required for runtime and tests)
- PyMuPDF (`fitz`) for PDF text extraction
- `google-generativeai` (Gemini API) for all AI capabilities
- `httpx` (RemoteOK scraper) and Playwright (YC Jobs scraper)
- pytest, ruff, mypy

**Frontend**
- Next.js 15 (App Router), React 19, TypeScript
- Vanilla CSS + Tailwind CSS 4
- Centralized fetch client (`lib/api.ts`) + Next.js rewrite proxy

## Project Structure

```
Job_Hunter/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app factory, CORS, exception handlers, router registration
│   │   ├── config.py               # Application settings (pydantic-settings)
│   │   ├── database.py             # Engine, SessionLocal, Base, health check
│   │   ├── dependencies.py         # DbSession alias, get_active_resume dependency
│   │   ├── cleanup.py              # Management command script for purging expired jobs
│   │   ├── models/                 # SQLAlchemy models: Job, Resume, ScrapeRun, ScoringRun
│   │   ├── schemas/                # Pydantic schemas + ApiResponse envelope
│   │   ├── routers/                # 7 Routers: health, jobs, scraper, resume, resume_analysis, interview_prep, dashboard
│   │   ├── services/               # 7 Services: job, resume, match, resume_analysis, interview_prep, scraper, dashboard
│   │   ├── scrapers/               # BaseScraper ABC + RemoteOKScraper + YCJobsScraper
│   │   └── ai/                     # gemini_client.py (GeminiClient, AIError) + prompts.py (4 prompts)
│   ├── alembic/                    # 3 Migrations: initial_schema, add_job_lifecycle_fields, add_scoring_runs_table
│   ├── tests/                      # Pytest suite (123 tests total; requires PostgreSQL TEST_DATABASE_URL)
│   └── pyproject.toml
├── frontend/
│   ├── app/                        # Next.js App Router routes: /, /dashboard, /jobs, /jobs/[id], /resume, /resume-review
│   ├── components/                 # dashboard/, jobs/, resume/, resume-review/, interview-prep/, ui/
│   ├── lib/api.ts                  # Centralized API fetch client
│   ├── lib/types.ts                # TypeScript interfaces
│   └── next.config.ts              # Proxy rewrites /api/* to backend
├── docker-compose.yml               # PostgreSQL service container
└── docs/                            # Documentation directory (see index below)
```

## Installation

Prerequisites: Python 3.12+, Node.js 18+, Docker (for PostgreSQL), and a Google Gemini API key.

```bash
git clone <repository-url>
cd Job_Hunter

# 1. Start PostgreSQL
docker compose up -d

# 2. Setup Backend
cd backend
python -m venv venv
# Windows: venv\Scripts\activate | Linux/macOS: source venv/bin/activate
pip install -e ".[dev]"
playwright install chromium
cp .env.example .env   # Configure GEMINI_API_KEY and DATABASE_URL
alembic upgrade head

# 3. Setup Frontend
cd ../frontend
npm install
```

## Configuration

Backend configuration is managed via environment variables (`backend/.env`):

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | - *(required)* | PostgreSQL DSN string (e.g., `postgresql://postgres:postgres@localhost:5432/internship_hunter`) |
| `GEMINI_API_KEY` | - *(required)* | Google Gemini API key |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Gemini model identifier |
| `APP_ENV` | `development` | One of `development`, `production`, `test` |
| `LOG_LEVEL` | `INFO` | One of `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated list of allowed origins |

Frontend configuration (`frontend/next.config.ts`):

| Variable | Default | Description |
|---|---|---|
| `API_BASE_URL` | `http://localhost:8000` | Backend target URL used by the Next.js rewrite proxy |

## Running Locally

```bash
# Terminal 1 — Database
docker compose up -d

# Terminal 2 — Backend
cd backend
uvicorn app.main:app --reload --port 8000

# Terminal 3 — Frontend
cd frontend
npm run dev
```

- Application UI: `http://localhost:3000`
- FastAPI OpenAPI Docs: `http://localhost:8000/docs`
- Health Endpoint: `GET http://localhost:8000/api/health`

## Cleanup Management Command

To remove un-annotated, saved expired jobs older than N days (default 30 days):

```bash
cd backend
python -m app.cleanup --days 30
```

This operation deletes only expired jobs with status `"saved"` and no user notes.

## Running Tests

The backend test suite consists of **123 tests** written for pytest:

```bash
cd backend
export TEST_DATABASE_URL="postgresql://postgres:postgres@localhost:5432/test_db"
python -m pytest
```

> **Note on test environment**: Database tests require PostgreSQL (`TEST_DATABASE_URL`). When `TEST_DATABASE_URL` is omitted, 110 database-dependent tests are automatically skipped, and the 13 non-database unit tests execute and pass. All Gemini API calls are mocked during testing (`mock_gemini` fixture).

See [`docs/TESTING.md`](docs/TESTING.md) for full test details.

## Deployment

There is currently no production deployment containerization in this repository:
- `docker-compose.yml` configures PostgreSQL only.
- Backend and frontend are run locally via Uvicorn and Next.js.
- CORS origins are configured via `CORS_ORIGINS` in backend configuration.

## Screenshots

*(UI screenshots of Dashboard, Job Listing, Job Detail with Interview Prep, Resume Management, and Resume Review pages to be added).*

## Documentation Index

| Document | Description |
|---|---|
| [`docs/PRD.md`](docs/PRD.md) | Product vision, target persona, core capabilities, and non-functional requirements |
| [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md) | Completed capabilities, limitations, tech debt, and future roadmap |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | System architecture, layers, scoring run lifecycle, job expiration, and data flow |
| [`docs/API_SPEC.md`](docs/API_SPEC.md) | Specification of all 16 FastAPI HTTP endpoints, envelopes, and error codes |
| [`docs/DATABASE.md`](docs/DATABASE.md) | Database schema specification for all 4 tables, indexes, and Alembic migrations |
| [`docs/PROMPTS.md`](docs/PROMPTS.md) | Design, structure, parsing, and retry strategy for all 4 Gemini prompts |
| [`docs/TESTING.md`](docs/TESTING.md) | Pytest test suite documentation, fixtures, PostgreSQL requirements, and manual test flows |
| [`docs/TASKS.md`](docs/TASKS.md) | Historical task implementation log synchronized with current codebase |

## Roadmap

See [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md) for the authoritative status of completed features, current limitations, technical debt, and planned work.

## License

MIT License.