# AI Internship Hunter

Personal AI-powered internship acquisition system.

Discover internships, score them against your resume, and track applications from a single dashboard.

> Built for personal use. Not a SaaS. No authentication, no multi-tenancy, no scaling concerns.

---

# Project Goal

Finding internships is usually a manual process:

* Searching multiple job boards
* Reading job descriptions
* Comparing jobs against your skills
* Tracking applications in spreadsheets

AI Internship Hunter automates this workflow by collecting jobs, analyzing resume fit using Gemini, and tracking application progress in one place.

The project also serves as a portfolio-quality demonstration of:

* Full-stack development
* AI integration
* Web scraping
* FastAPI architecture
* PostgreSQL design
* Next.js frontend development

---

# Features

## Job Collection

Collect internships from:

* RemoteOK (public API)
* YC Jobs (Work at a Startup)

Features:

* Manual sync
* Duplicate detection
* Source tracking
* Scrape history logging

---

## Resume Upload

Upload a PDF resume.

Workflow:

```text
PDF
↓
PyMuPDF
↓
Raw Text
↓
Gemini
↓
Skills Extraction
```

Features:

* PDF validation
* Skill extraction
* Resume replacement
* Single active resume

---

## Job Scoring

Evaluate job fit using Gemini.

Outputs:

* Match score (0–100)
* Missing skills
* Two-sentence summary

Features:

* Cached results
* Re-score detection after resume updates
* Score-based sorting

---

## Application Tracking

Track progress for each opportunity.

Statuses:

```text
saved
applied
interview
offer
rejected
```

Additional support:

* Notes
* Status filters
* Source filters

---

# Tech Stack

## Frontend

* Next.js 15
* TypeScript
* Tailwind CSS
* shadcn/ui

## Backend

* FastAPI
* PostgreSQL
* SQLAlchemy 2.x
* Alembic

## AI

* Gemini API

## Scraping

* Playwright
* httpx

## Development

* Docker Compose
* Python 3.12
* Node.js 20

---

# Architecture

```text
Browser (Next.js)
        │
        ▼
FastAPI Backend
        │
 ┌──────┼──────┐
 │      │      │
 ▼      ▼      ▼
AI   Scrapers  DB
 │      │      │
 ▼      ▼      ▼
Gemini RemoteOK PostgreSQL
       YC Jobs
```

Detailed design:

```text
docs/ARCHITECTURE.md
```

---

# Project Structure

```text
ai-internship-hunter/
│
├── backend/
│   └── app/
│       ├── routers/
│       ├── services/
│       ├── models/
│       ├── schemas/
│       ├── scrapers/
│       └── ai/
│
├── frontend/
│   ├── app/
│   ├── components/
│   ├── lib/
│   └── types/
│
└── docs/
    ├── PRD.md
    ├── DATABASE.md
    ├── API_SPEC.md
    ├── ARCHITECTURE.md
    ├── TASKS.md
    └── PROMPTS.md
```

---

# Quick Start

## Prerequisites

* Docker
* Docker Compose
* Node.js 20+
* Python 3.12+
* Gemini API Key

---

## Clone Repository

```bash
git clone <your-repository-url>
cd ai-internship-hunter
```

---

## Configure Environment

```bash
cp .env.example .env
```

Update:

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/internship_hunter

GEMINI_API_KEY=your_key_here

NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Start PostgreSQL

```bash
docker compose up -d
```

---

## Start Backend

```bash
cd backend

pip install -e ".[dev]"

alembic upgrade head

uvicorn app.main:app --reload --port 8000
```

Backend:

```text
http://localhost:8000
```

Swagger Docs:

```text
http://localhost:8000/docs
```

---

## Start Frontend

```bash
cd frontend

npm install

npm run dev
```

Frontend:

```text
http://localhost:3000
```

---

# Environment Variables

| Variable            | Required | Description                  |
| ------------------- | -------- | ---------------------------- |
| DATABASE_URL        | Yes      | PostgreSQL connection string |
| GEMINI_API_KEY      | Yes      | Gemini API key               |
| GEMINI_MODEL        | No       | Gemini model name            |
| NEXT_PUBLIC_API_URL | Yes      | Backend URL                  |

See:

```text
.env.example
```

for full documentation.

---

# Documentation

| Document        | Description                    |
| --------------- | ------------------------------ |
| PRD.md          | Product requirements and goals |
| DATABASE.md     | Database schema and design     |
| API_SPEC.md     | REST API specification         |
| ARCHITECTURE.md | System architecture            |
| TASKS.md        | Development roadmap            |
| PROMPTS.md      | Gemini prompt definitions      |

---

# Development Status

Current Phase:

```text
Planning Complete
```

Completed:

* Product Design
* Database Design
* API Design
* Architecture Design
* Task Planning
* AI Prompt Design

Next:

```text
Phase 0A — Backend Foundation
```

---

# MVP Workflow

```text
Upload Resume
        ↓
Extract Skills
        ↓
Sync Jobs
        ↓
Browse Jobs
        ↓
Score Jobs
        ↓
Track Applications
```

---

# Future Roadmap

Possible post-MVP features:

* Automated daily sync
* Resume versioning
* Multiple job sources
* Recruiter discovery
* Email follow-ups
* Cover letter generation
* Auto-scoring after sync
* AI-powered application recommendations

Not part of MVP.

---

# Screenshots

Coming soon.

---

# License

MIT License

Feel free to fork and adapt for personal use.
