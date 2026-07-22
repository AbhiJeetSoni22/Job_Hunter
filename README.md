# AI Internship Hunter

A personal, single-user tool that discovers software-engineering internships from multiple sources, scores them against your resume with Google Gemini, and tracks your application pipeline end to end.

> This README is generated from the actual codebase (backend `app/`, frontend `app/`, `alembic/versions/`, `tests/`). Nothing below describes a feature that isn't implemented.

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running Locally](#running-locally)
- [Running Tests](#running-tests)
- [Deployment](#deployment)
- [Screenshots](#screenshots)
- [Documentation Index](#documentation-index)
- [Roadmap](#roadmap)

## Overview

AI Internship Hunter is a FastAPI + Next.js application built for one user, one resume at a time. It:

1. Accepts a PDF resume, extracts text (PyMuPDF), and pulls a normalized skills list from it (Gemini).
2. Scrapes internship/entry-level listings from RemoteOK and Y Combinator's Work at a Startup, de-duplicating by URL.
3. Scores each job against the active resume with Gemini (0-100 fit score, missing skills, two-sentence summary), with a resume-keyed cache.
4. Lets you track each job through a status pipeline: `saved -> applied -> interview -> offer` (or `rejected`).
5. Surfaces a dashboard of aggregate stats (total/scored jobs, average/best score, applications submitted, match-quality breakdown, top 5 matches).
6. Runs two additional, independent AI features on demand: a **Resume Gap Analyzer** (paste any JD, get a score + resume-improvement suggestions) and an **AI Interview Prep Generator** (per-job, project/technical/behavioral questions and tips).

There is no user authentication and no multi-user support - the data model assumes exactly one resume exists at a time.

## Key Features

| Feature | Summary |
|---|---|
| Resume Upload & Parsing | PDF upload -> PyMuPDF text extraction -> Gemini skill extraction. Single active resume (upload replaces the previous one). |
| Multi-Source Job Scraping | RemoteOK JSON API + YC "Work at a Startup" (Playwright). Deduplicated by canonical URL. |
| AI Job Match Scoring | Gemini scores each job 0-100 against resume skills, with a resume-version-aware cache and stale-score ("Needs Re-score") detection. |
| Application Tracking | PATCH job status/notes; status values: `saved`, `applied`, `interview`, `offer`, `rejected`. |
| Dashboard | Aggregate metrics computed in two SQL queries: totals, average/best score, match-quality tiers, top 5 matches. |
| Auto-Scoring on Sync | After a scraper run, newly inserted jobs are scored in the background (FastAPI `BackgroundTasks`) without blocking the HTTP response. |
| Resume Gap Analyzer | Paste a job description; get a match score, summary, missing skills, strengths, resume suggestions, and ATS tips - independent of the jobs table. |
| AI Interview Prep Generator | Per job, generates project questions, technical questions, behavioral questions, topics to revise, and interview tips from the resume + job description. |

See [`docs/FEATURES.md`](docs/FEATURES.md) for full detail on each feature (workflow, endpoints, DB tables, AI usage).

## Architecture

```mermaid
flowchart LR
    A[Next.js Frontend] -->|"/api/* (rewrite proxy)"| B[FastAPI Routers]
    B --> C[Service Layer]
    C --> D[GeminiClient]
    C --> E[SQLAlchemy ORM]
    E --> F[(PostgreSQL)]
    D --> G[(Google Gemini API)]
    C --> H[Scrapers: RemoteOK / YC Jobs]
    H --> I[(External job sites)]
```

Routers contain no business logic or DB access - they translate HTTP <-> service calls only. Services own all business rules and raise plain Python exceptions (`ValueError`, `LookupError`, custom `*Error` classes) that routers convert to the `{ data, error }` API envelope. Full detail in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) and [`docs/SYSTEM_DESIGN.md`](docs/SYSTEM_DESIGN.md).

## Tech Stack

**Backend**
- Python 3.12, FastAPI 0.115, Uvicorn
- SQLAlchemy 2.x (typed `Mapped[...]` models) + Alembic migrations
- PostgreSQL (JSONB + native UUID columns - SQLite is not compatible)
- PyMuPDF (`fitz`) for PDF text extraction
- `google-generativeai` (Gemini) for all AI features
- `httpx` (RemoteOK) and Playwright/Chromium (YC Jobs) for scraping
- pytest, ruff, mypy (strict)

**Frontend**
- Next.js 15 (App Router), React 19, TypeScript
- Tailwind CSS 4
- No state-management library - plain `useState`/`useEffect` + a centralized `lib/api.ts` fetch client

## Project Structure

```
Job_Hunter-main/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app factory, CORS, exception handlers, router registration
│   │   ├── config.py               # Settings (env vars) via pydantic-settings
│   │   ├── database.py             # Engine, SessionLocal, Base, get_db, health check
│   │   ├── dependencies.py         # DbSession alias, get_active_resume dependency
│   │   ├── models/                 # SQLAlchemy ORM: Job, Resume, ScrapeRun
│   │   ├── schemas/                # Pydantic request/response schemas + ApiResponse envelope
│   │   ├── routers/                # HTTP layer only: health, jobs, resume, resume_analysis,
│   │   │                           #   interview_prep, scraper, dashboard
│   │   ├── services/               # Business logic: job_service, resume_service, match_service,
│   │   │                           #   resume_analysis_service, interview_prep_service,
│   │   │                           #   scraper_service, dashboard_service
│   │   ├── scrapers/               # BaseScraper ABC + RemoteOKScraper + YCJobsScraper
│   │   └── ai/                     # gemini_client.py (GeminiClient, AIError) + prompts.py
│   ├── alembic/                    # Migrations (one initial-schema revision)
│   ├── tests/                      # pytest suite, PostgreSQL-backed, Gemini mocked
│   └── pyproject.toml
├── frontend/
│   ├── app/                        # Next.js App Router pages: /, /dashboard, /jobs, /jobs/[id],
│   │                                #   /resume, /resume-review
│   ├── components/                 # dashboard/, jobs/, resume/, resume-review/, interview-prep/, ui/
│   ├── lib/api.ts                  # Single fetch client - all HTTP calls go through here
│   ├── lib/types.ts                # Shared TS types mirroring backend schemas
│   └── next.config.ts              # Rewrites /api/* to the backend
├── docker-compose.yml               # PostgreSQL only (see Deployment)
└── docs/                            # See Documentation Index below
```

## Installation

Prerequisites: Python 3.12, Node.js 18+, Docker (for PostgreSQL), a Google Gemini API key.

```bash
git clone <this-repo>
cd Job_Hunter-main

# Database
docker compose up -d

# Backend
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
playwright install chromium                          # required for the YC Jobs scraper
cp .env.example .env                                  # then fill in GEMINI_API_KEY
alembic upgrade head

# Frontend
cd ../frontend
npm install
```

## Configuration

Backend configuration is read from `backend/.env` (see `backend/.env.example`) via `app/config.py`:

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | - (required) | PostgreSQL DSN, e.g. `postgresql://postgres:postgres@localhost:5432/internship_hunter` |
| `GEMINI_API_KEY` | - (required) | Google Gemini API key |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Gemini model name |
| `APP_ENV` | `development` | One of `development`, `production`, `test` |
| `LOG_LEVEL` | `INFO` | One of `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated allowed origins |

Frontend configuration (`frontend/next.config.ts`, `frontend/lib/api.ts`):

| Variable | Default | Purpose |
|---|---|---|
| `API_BASE_URL` | `http://localhost:8000` | Server-side base URL used by the Next.js rewrite proxy and by server components |

The browser never calls the backend directly - requests to `/api/*` are rewritten by Next.js to `API_BASE_URL`.

## Running Locally

```bash
# Terminal 1 - database (if not already running)
docker compose up -d

# Terminal 2 - backend
cd backend
uvicorn app.main:app --reload --port 8000

# Terminal 3 - frontend
cd frontend
npm run dev
```

Visit `http://localhost:3000`. The backend serves interactive OpenAPI docs at `http://localhost:8000/docs`.

Health check: `GET http://localhost:8000/api/health` -> `200 {"status":"ok","database":"connected"}` or `503` if PostgreSQL is unreachable.

## Running Tests

```bash
cd backend
export TEST_DATABASE_URL="postgresql://postgres:postgres@localhost:5432/test_db"
pytest
```

Tests require a **real PostgreSQL** database (JSONB/UUID columns are not SQLite-compatible) - every DB-dependent fixture is skipped automatically if `TEST_DATABASE_URL` is unset. All Gemini calls are mocked (`GeminiClient` is patched in `conftest.py`); no test makes a real network or AI call. See [`docs/TESTING.md`](docs/TESTING.md).

Frontend has no automated test suite; `npm run lint` and `npm run type-check` are available.

## Deployment

There is currently no production deployment configuration in this repository:

- `docker-compose.yml` only defines the PostgreSQL service - there are **no Dockerfiles** for the backend or frontend.
- Both apps are intended to be run locally (`uvicorn` / `next dev` or `next start`) against the Dockerized database.
- CORS is hardcoded to `http://localhost:3000` in `app/main.py`'s middleware (in addition to the configurable `CORS_ORIGINS` setting, which is not currently wired into that middleware - see [Known Limitations](docs/PROJECT_STATUS.md#known-limitations)).

Anyone wanting to deploy this to a server will need to add their own Dockerfiles/process manager and reconcile the two CORS configuration paths first.

## Screenshots

_No screenshots are currently included in this repository. (Placeholder - add UI screenshots of the Dashboard, Jobs list, Job detail/Interview Prep panel, Resume page, and Resume Review page here.)_

## Documentation Index

| Document | Contents |
|---|---|
| [`docs/FEATURES.md`](docs/FEATURES.md) | Every implemented feature: workflow, backend/frontend implementation, APIs, DB tables, AI usage |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Layered architecture, layer responsibilities, request lifecycle |
| [`docs/SYSTEM_DESIGN.md`](docs/SYSTEM_DESIGN.md) | High-level design, data flow, deployment architecture, trade-offs |
| [`docs/WORKFLOW.md`](docs/WORKFLOW.md) | End-to-end workflows with Mermaid diagrams (resume upload -> interview prep) |
| [`docs/API_SPEC.md`](docs/API_SPEC.md) | Every endpoint: method, path, auth, request/response, errors |
| [`docs/DATABASE.md`](docs/DATABASE.md) | Tables, columns, relationships, constraints, indexes, migrations |
| [`docs/PROMPTS.md`](docs/PROMPTS.md) | All four Gemini prompts, output schemas, retry/caching/validation logic |
| [`docs/TESTING.md`](docs/TESTING.md) | Test strategy, fixtures, coverage, how to run |
| [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md) | Completed / in progress / planned / known limitations / tech debt |
| [`docs/PRD.md`](docs/PRD.md) | Product requirements (original intent) |
| [`docs/TASKS.md`](docs/TASKS.md) | Phase-by-phase build log |

## Roadmap

See [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md) for the authoritative, code-derived roadmap (Completed / In Progress / Planned / Future Ideas / Known Limitations / Technical Debt).

## License

MIT License. Feel free to fork and adapt for personal use.