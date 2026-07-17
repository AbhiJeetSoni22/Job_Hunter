# AI Internship Hunter

A full-stack, AI-powered job search assistant. It scrapes internship listings from multiple sources, scores each one against your resume using Google Gemini, and tracks your application pipeline — all from a single dashboard.

> Built as a personal tool and portfolio project. Single-user by design: no authentication, no multi-tenancy, no scaling concerns. The architecture is intentionally simple where simplicity is correct, and AI-driven where AI adds real value.

---

## What It Does

Manually hunting for internships means juggling multiple job boards, reading descriptions one by one, guessing how well you fit each role, and tracking applications in a spreadsheet. AI Internship Hunter automates the first three and gives you a clean place to do the fourth:

1. **Collects** internship listings from RemoteOK and YC's Work at a Startup with one click.
2. **Scores** every new listing against your resume with Gemini — a 0–100 fit score, the skills you're missing, and a two-sentence rationale — automatically, right after each sync.
3. **Tracks** your pipeline (saved → applied → interview → offer/rejected) with notes per job.
4. **Surfaces** your best-fit opportunities on a dashboard: top matches, score distribution, and sync history.

Who it's for: anyone tired of manually cross-referencing job descriptions against their own resume. It's built for internship search specifically, but the scoring and tracking pattern generalizes to any job search.

### How AI is used

Gemini (`gemini-2.5-flash`) does three jobs, all as structured JSON with a low temperature (0.1) to keep output deterministic:

- **Resume parsing** — turns an uploaded PDF's raw text into a normalized list of technical skills.
- **Job matching** — compares those skills against a job description and returns a fit score, up to five missing skills, and a two-sentence summary. Scores are cached and only recomputed when the resume changes.
- **Interview preparation generation** — uses the active resume text plus a job's title, company, and description to return tailored technical, behavioral, and project questions, topics to revise, and interview tips. The generation is stateless and never persisted.

---

## Technical Highlights

- **Next.js 15 (App Router) + React 19 + TypeScript** — client-rendered dashboard, job list/detail, and resume pages, all talking to the backend through a single typed `lib/api.ts` fetch wrapper.
- **FastAPI** backend with a strict layering discipline: routers handle HTTP only, all business logic lives in services, and every error response is normalized into one `{data, error}` envelope.
- **PostgreSQL + SQLAlchemy 2.x + Alembic** — three tables (`jobs`, `resumes`, `scrape_runs`), one migration, JSONB for skill arrays, indexed for the actual query patterns the API uses.
- **Playwright** drives a headless Chromium browser to scrape YC's JS-rendered job board; **httpx** hits RemoteOK's public JSON API directly — no browser needed there.
- **Gemini AI** for skill extraction, job-fit scoring, resume-gap analysis, and interview-prep generation, with retry + exponential backoff on transient API errors.
- **Docker Compose** for PostgreSQL in local dev.
- **Pytest** — 104 service-layer tests with Gemini mocked out, gated behind a live test database.

---

## Features

### Job Collection
- Manual sync pulls from RemoteOK (public API) and YC Jobs (Playwright)
- Duplicate detection by canonical URL
- Per-source scrape history (jobs found, jobs new, errors) in `scrape_runs`
- One source failing never blocks the other

### Resume Upload
- PDF upload → PyMuPDF text extraction → Gemini skill extraction
- 5 MB size limit, PDF-only validation
- Single active resume; uploading a new one replaces the old one
- Validation includes corrupted PDF detection, password-protected PDF detection, image-only PDF detection, page limit validation (3 pages max), and resume heuristics checking

### AI Job Scoring
- Match score (0–100), missing skills (up to 5), two-sentence summary
- Automatic scoring of newly synced jobs right after a sync completes (skipped cleanly if no resume is uploaded)
- Results cached on the job record; re-scoring only happens if the resume changed since the last score
- "Needs Re-score" flag surfaced in the UI when the active resume is newer than a job's last score

### Resume Gap Analyzer
- Paste any job description (not just from the database) into the analyzer
- Get detailed feedback: match score, summary, missing skills, existing strengths
- Receive concrete resume improvement suggestions specific to the role
- Get ATS optimization tips for that specific job description
- Powered by Gemini, with the same caching and retry logic as job scoring

### Interview Preparation Generator
- Open a saved job and generate interview prep from the active resume plus the job's title, company, and description
- Receive structured guidance across technical questions, behavioral questions, project questions, topics to revise, and interview tips
- No database persistence, no caching, and no background jobs; generation is stateless and runs on demand
- Reuses the existing Gemini integration already used by scoring and resume analysis

### Application Tracking
- Status per job: `saved → applied → interview → offer / rejected`
- Free-text notes per job
- Filter jobs by status, source, and scored/unscored

### Recommendation Dashboard
- Total jobs, scored jobs, average/best match score, applications submitted
- Match-quality breakdown (Excellent / Good / Possible / Weak)
- Top 5 matches by score, with a plain-language recommendation label per job

---

## Architecture

```
Browser (Next.js 15, client components)
        │  HTTP/JSON via lib/api.ts
        ▼
FastAPI Backend
    ├── routers/     ← HTTP only, no business logic
    ├── services/    ← all business logic, independently testable
    ├── scrapers/    ← RemoteOK (httpx) + YC Jobs (Playwright)
    └── ai/           ← Gemini client + prompts
        │
        ▼
PostgreSQL 16  (jobs · resumes · scrape_runs)
```

Everything runs synchronously and on-demand — no task queue, no scheduler, no background workers beyond a single FastAPI `BackgroundTasks` call that scores newly-synced jobs after the sync response has already been returned. That's a deliberate scope decision for a single-user tool, not an oversight — see `docs/ARCHITECTURE.md` for the full request-lifecycle breakdown and the reasoning behind it.

---

## Project Structure

```
ai-internship-hunter/
│
├── backend/
│   ├── alembic/               # one migration: initial schema
│   └── app/
│       ├── routers/           # health, jobs, resume, resume_analysis, scraper, dashboard
│       ├── services/          # job, resume, resume_analysis, match, scraper, dashboard
│       ├── models/            # Job, Resume, ScrapeRun (SQLAlchemy)
│       ├── schemas/           # Pydantic request/response models
│       ├── scrapers/          # RemoteOKScraper, YCJobsScraper
│       └── ai/                 # GeminiClient, prompt templates
│   └── tests/                 # 104 pytest tests (service layer)
│
├── frontend/
│   ├── app/                   # dashboard ("/"), /jobs, /jobs/[id], /resume, /resume-review
│   ├── components/            # ui/, jobs/, resume/, resume-review/, dashboard/
│   └── lib/                   # api.ts (fetch wrapper), types.ts
│
└── docs/
    ├── PRD.md
    ├── DATABASE.md
    ├── API_SPEC.md
    ├── ARCHITECTURE.md
    ├── TASKS.md
    ├── PROMPTS.md
    ├── DEPLOYMENT.md
    └── TESTING.md
```

---

## Quick Start

### Prerequisites
- Docker + Docker Compose
- Node.js 20+
- Python 3.12+
- A Gemini API key ([Google AI Studio](https://aistudio.google.com/))

### 1. Clone and configure

```bash
git clone <your-repository-url>
cd ai-internship-hunter
cp .env.example .env   # then fill in GEMINI_API_KEY at minimum
```

### 2. Start PostgreSQL

```bash
docker compose up -d
```

### 3. Start the backend

```bash
cd backend
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

- API: `http://localhost:8000`
- Interactive docs (Swagger): `http://localhost:8000/docs`

### 4. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

- App: `http://localhost:3000`

Full walkthrough, including environment variables and production notes, is in [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).

---

## Environment Variables

| Variable            | Where            | Required | Description                                      |
| -------------------- | ---------------- | -------- | ------------------------------------------------- |
| `DATABASE_URL`       | backend          | Yes      | PostgreSQL connection string                       |
| `GEMINI_API_KEY`     | backend          | Yes      | Gemini API key                                     |
| `GEMINI_MODEL`       | backend          | No       | Defaults to `gemini-2.5-flash`                     |
| `APP_ENV`            | backend          | No       | `development` / `production` / `test`             |
| `LOG_LEVEL`          | backend          | No       | Defaults to `INFO`                                 |
| `CORS_ORIGINS`       | backend          | No       | Comma-separated allowed origins                    |
| `API_BASE_URL`       | frontend (server) | No      | Backend URL used server-side; defaults to `http://localhost:8000` |

See [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) for the complete list and setup instructions.

---

## Documentation

| Document                            | Description                                  |
| ------------------------------------ | --------------------------------------------- |
| [`PRD.md`](docs/PRD.md)             | Product requirements and scope                |
| [`DATABASE.md`](docs/DATABASE.md)   | Schema, indexes, design decisions             |
| [`API_SPEC.md`](docs/API_SPEC.md)   | Full REST API reference                       |
| [`ARCHITECTURE.md`](docs/ARCHITECTURE.md) | System design, layering rules, data flows |
| [`TASKS.md`](docs/TASKS.md)         | Build history by phase                        |
| [`PROMPTS.md`](docs/PROMPTS.md)     | Gemini prompt templates and design rules      |
| [`DEPLOYMENT.md`](docs/DEPLOYMENT.md) | Local setup and production deployment notes |
| [`TESTING.md`](docs/TESTING.md)     | Running the test suite                        |

---

## Development Status

**MVP Complete.** All core flows — sync, score, track, the recommendation dashboard, and resume gap analysis — work end-to-end in the browser against a live PostgreSQL database and the real RemoteOK/YC Jobs sources.

**Completed:**
- Job collection from both sources, with dedup and per-source error isolation
- Resume upload, PDF text extraction, AI skill extraction
- AI job scoring with caching and stale-score detection
- Automatic scoring of new jobs after every sync
- Application status and notes tracking
- Recommendation dashboard with match-quality breakdown and top matches
- Resume Gap Analyzer for analyzing any job description against the active resume
- Interview Preparation Generator on the job detail page, powered by the active resume and job content
- 104 passing pytest tests across all services

**In progress / next up:**
- Loading skeletons (currently spinners) for perceived-performance polish
- Delete-confirmation dialog on resume removal
- Removing a leftover debug-dump call in the YC scraper now that selectors are confirmed stable

See [`TASKS.md`](docs/TASKS.md) for the full phase-by-phase breakdown.

---

## Roadmap

Ideas beyond the current MVP, roughly in priority order:

- Loading skeletons and further UI polish
- Application status history / timeline view
- Bulk status updates
- Additional job sources (e.g. Wellfound)
- Resume versioning
- Cover letter generation
- Scheduled (rather than manual) syncing

Interview Preparation Generator is now part of the shipped V1 workflow and is no longer a roadmap item.

---

## License

MIT License. Feel free to fork and adapt for personal use.