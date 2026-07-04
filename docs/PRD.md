# Product Requirements Document

**Project:** AI Internship Hunter  
**Version:** 1.0 MVP  
**Scope:** Personal use

---

## Problem

Internship hunting is manual and unstructured. Browsing job boards, reading descriptions, mentally comparing them to your resume, and then remembering which ones you applied to — all of it happens in your head or across a mess of browser tabs and spreadsheet rows.

The result: good opportunities get missed, weak ones get time, and the overall process is slower than it needs to be.

---

## Goal

Build a personal tool that automates job discovery, ranks opportunities by resume fit using AI, and tracks application status — replacing the browser-tab-and-spreadsheet workflow with one focused system.

Secondary goal: produce a portfolio-quality project that demonstrates full-stack development, AI integration, and thoughtful system design.

---

## Users

One user. You. No auth, no accounts, no multi-tenancy.

---

## MVP Scope

Four capabilities and nothing else.

## Technology Stack

Frontend:
- Next.js 15
- TypeScript
- Tailwind CSS
- Custom component library (no shadcn/ui — built by hand)

Backend:
- FastAPI
- PostgreSQL
- SQLAlchemy
- Alembic

AI:
- Gemini API

Scraping:
- RemoteOK API
- Playwright (YC Jobs)

## MVP Constraints

- Single user only
- Single active resume only
- Manual sync only
- No background workers
- No authentication
- No scheduled jobs

### 1. Job Collection

**What:** Pull job listings from two sources on demand.

**Sources:**
- RemoteOK — via their public JSON API (`remoteok.com/api`). No scraping, no ToS concerns.
- YC Jobs (Work at a Startup) — via Playwright headless browser.

**Behaviour:**
- User triggers a sync manually via a "Sync Jobs" button in the UI.
- Each source runs sequentially. Results are saved. Duplicate URLs are skipped.
- After sync, a status summary shows: source, jobs found, jobs new, any errors.
- Fields stored per job: `title`, `company`, `description`, `url`, `source`, `location`, `posted_at`.

**Out of scope:** Scheduled/automatic syncing. Wellfound. LinkedIn. Any source requiring login.

---

### 2. Resume Upload

**What:** Upload a PDF resume. Extract skills. Store for use in scoring.

**Behaviour:**
- User uploads a PDF on the `/resume` page.
- Backend extracts raw text using PyMuPDF.
- Gemini receives the raw text and returns a flat list of skills.
- Skills and raw text are saved. Previous resume is replaced.
- Only one resume exists at any time. No versioning.

**Out of scope:** Resume editing in UI. Multiple versions. Resume builder.

---

### 3. Job Scoring

**What:** For any job, run an AI match analysis against the current resume.

**Behaviour:**
- User clicks "Score" on a job (in list or detail view).
- Backend checks if score already exists → returns cached result if yes.
- If no cache: sends job description + resume skills to Gemini.
- Gemini returns: `match_score` (0–100), `missing_skills` (up to 5), `match_summary` (2 sentences).
- Results stored on the job record. Displayed in job detail view.
- Job list is sortable by score.
- **Implemented beyond original scope:** newly synced jobs are scored automatically right after a sync completes, so the dashboard has fresh data without a manual click per job. This runs after the sync response is returned; it doesn't block the sync itself.

**Out of scope:** Score history over time. Multiple resume comparisons.

---

### 4. Application Tracking

**What:** Track status and notes per job.

**Statuses:** `saved` → `applied` → `interview` → `offer` / `rejected`

**Behaviour:**
- Every job has a `status` field, defaulting to `saved`.
- User changes status via dropdown in the job card or detail view.
- Free-text `notes` field per job for anything relevant (contact name, next step, etc.).
- No kanban board. Status lives on the job card directly.

**Out of scope:** Reminders, calendar integration, email tracking, follow-up automation.

---

### 5. Recommendation Dashboard

*(Added after the original 4-capability MVP scope was defined; implemented once auto-scoring made a summary view worthwhile.)*

**What:** A landing page (`/`) summarizing the whole pipeline at a glance.

**Behaviour:**
- Total jobs, scored jobs, average match score, best match score, applications submitted.
- Match-quality breakdown: Excellent (≥90) / Good (75-89) / Possible (60-74) / Weak (<60), computed over scored jobs only.
- Top 5 matches by score, each with a plain-language recommendation label (Excellent/Strong/Potential/Low Match).
- Sync Jobs button lives here, not just on the jobs page.

**Out of scope:** Configurable alert thresholds. Historical trend charts.

---

## User Flows

### Flow 1 — First time setup
1. Open app (lands on `/`, the dashboard)
2. Navigate to `/resume`
3. Upload PDF
4. View extracted skills list
5. Navigate to `/jobs`, or click "Sync Jobs" from the dashboard
6. Jobs appear in list; new jobs are scored automatically in the background

### Flow 2 — Daily use
1. Open `/` — check dashboard for new top matches since last visit
2. Click "Sync Jobs" if needed
3. Browse `/jobs`, sorted by score, or drill into a specific job
4. Click a job → read match analysis
5. Update status / add notes

### Flow 3 — Scoring a job
1. On job card or detail: click "Score"
2. Loading state while Gemini runs (or instant if cached)
3. Score badge, missing skills list, and summary appear

---

## Success Criteria

| Criterion | Measure |
|---|---|
| Jobs collected | Sync pulls at least 20 relevant jobs per run |
| Skills extracted | Gemini returns ≥10 skills from a standard resume PDF |
| Scoring works | Match score + missing skills display for any scored job |
| Caching works | Re-clicking "Score" returns instantly with no new API call |
| Tracking works | Status and notes update persists across page refreshes |
| No crashes | Scraper failure on one source doesn't prevent the other from completing |

---

## Non-Requirements

These are explicitly not part of this MVP:

- Authentication or user accounts
- Mobile-optimised layout
- Email or notification system
- Auto-apply functionality
- Browser extension
- Wellfound scraping
- Resume version history
- Cover letter generation
- Scheduled background jobs