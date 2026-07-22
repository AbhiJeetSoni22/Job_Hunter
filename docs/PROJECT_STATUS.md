# Project Status

**Project:** AI Internship Hunter
**Type:** Personal use · Single-user · No auth · No SaaS
**Goal:** Automate internship discovery, AI-powered scoring, and application tracking

> This file tracks **what was built, why, and what's left** — a development log and roadmap. For **how the system works internally** (backend/frontend/AI/database architecture, request lifecycle, data flow, caching, retry logic, performance optimizations, folder organization, technical debt), see [`ARCHITECTURE.md`](ARCHITECTURE.md).

---

## Problem Statement

Internship hunting is manual and unstructured. Browsing job boards, reading descriptions, comparing them to your resume, and tracking what you applied to — all of it happens across browser tabs and spreadsheets. Good opportunities get missed, weak ones get time, and the process is slower than it needs to be.

---

## MVP Goal

A personal tool that:
1. Collects internship listings from RemoteOK and YC Jobs
2. Scores each job against your resume using Gemini AI
3. Tracks application status per job

Secondary: portfolio-quality code that demonstrates full-stack dev, AI integration, web scraping, FastAPI architecture, and PostgreSQL design.

> **Update (2026-07-22):** the MVP goal above describes the original three-capability scope. Two additional, independent AI capabilities have since shipped on top of it — a Resume Gap Analyzer and an AI Interview Preparation Generator (Phases 6 and 7 below). Both were built as isolated verticals that do not modify the three original capabilities.

---

## Completed Phases

### ✅ Phase 0A — Backend Foundation
**What:** Established the FastAPI backend, a PostgreSQL database (via Docker Compose), Alembic migrations, and a health-check endpoint.
**Why:** Needed a working, testable backend skeleton before building any feature.

### ✅ Phase 1A — Database Layer
**What:** Created the three core tables — `jobs`, `resumes`, `scrape_runs` — and applied the initial Alembic migration.
**Why:** Every downstream feature (scraping, scoring, tracking, dashboard) needed a persistent store first.
**Note:** this is still the only migration in the project — no schema changes were required for anything added after this phase. Phases 5, 6, and 7 all reuse these same three tables.

### ✅ Phase 1B — Service and Router Layer
**What:** Built the job-listing/CRUD capability and the scraper-orchestration capability, each as a service + router pair.
**Why:** Needed a place for business logic (services) separate from HTTP handling (routers) before adding any scraper or AI feature — this split became the pattern every later feature followed.

### ✅ Phase 1C — RemoteOK Scraper
**What:** Added the first job source — pulling internship/entry-level listings from RemoteOK's public API.
**Why:** Needed real job data before scoring or dashboard features had anything to operate on.

### ✅ Phase 1D — Resume Upload and PDF Extraction
**What:** Added resume upload (PDF), text extraction, and a single-active-resume storage model (a new upload replaces any existing resume).
**Why:** The whole point of the tool is scoring jobs against a resume — this had to exist before AI scoring could be built.
**Since expanded:** resume upload later grew additional content-quality validation (rejecting non-resume documents, oversized files, encrypted PDFs) beyond what this phase originally covered — not a separate phase, just an incremental hardening of this same feature.

### ✅ Phase 2A — Gemini Client
**What:** Integrated Google Gemini as the AI provider, behind a single shared client used by every AI feature.
**Why:** Centralizing all AI calls behind one client made it possible to add three more AI features later (Phases 2C, 6, 7) without duplicating retry/parsing logic per feature.

### ✅ Phase 2B — Resume Skill Extraction
**What:** Wired Gemini into the resume-upload flow to extract a normalized skills list from the resume text.
**Why:** Needed structured skills (not raw resume text) to score jobs against.
**Design choice:** if the AI call fails, the upload still succeeds with an empty skills list rather than failing outright — resume storage is treated as higher priority than AI enrichment.

### ✅ Phase 2C — Job Match Scoring
**What:** Added AI-powered job-to-resume match scoring, with a caching mechanism so re-viewing an already-scored job doesn't needlessly re-call Gemini.
**Why:** Automated fit-scoring is the core value proposition of the tool.

### ✅ Phase 2D — Backend Hardening and API Cleanup
**What:** Standardized error responses across the whole API and added a "stale score" flag so the UI can tell the user when a job's score no longer reflects the current resume.
**Why:** Needed a consistent, predictable contract for the frontend to build against.

### ✅ Phase 3A — YC Jobs Scraper
**What:** Added a second job source — a browser-automation-based scraper for Y Combinator's "Work at a Startup" listings.
**Why:** One source wasn't enough breadth of listings for a real job search.
**Since optimized:** the original page-scraping approach was slow (roughly 8-12 seconds per sync); it was later reworked for speed without changing what data gets extracted.
**Confirmed (2026-07-22):** a debug-logging call originally flagged as a future cleanup item no longer exists in the scraper — that cleanup has already happened, ahead of when it was scheduled.

### ✅ Phase 3B — Frontend Foundation
**What:** Built the Next.js 15 frontend shell — a typed API client, layout/navbar, and the first set of shared UI components.
**Why:** Needed a browser-based UI before any feature could be used interactively.

### ✅ Phase 3C — Frontend Interactivity
**What:** Converted every page into a fully interactive client experience — live dashboard stats, a filterable job list, job-detail actions (score/status/notes), resume upload/delete — with loading and toast feedback throughout.
**Why:** A backend API alone isn't a usable product for a personal tool; this phase made every backend capability actually usable from the browser.
**Known issue carried forward:** a cleanup item logged in this phase (a leftover dead code block in the resume upload endpoint) was noted here as fixed at the time, but was reconfirmed still present in a later audit pass — see Current Limitations below.

---

### ✅ Phase 5 — AI Recommendation Dashboard
**What:** Added a dashboard summarizing job-search progress — total/scored jobs, average/best match score, applications submitted, a match-quality breakdown, and a top-5-matches list. Newly scraped jobs are now automatically scored in the background right after a sync, so the dashboard has fresh data without a manual scoring step per job.
**Why:** With scraping and scoring both working, there was no single view of overall progress — this phase closed that gap.
**Note:** this is where the dashboard moved off the site's home page onto its own `/dashboard` route — the home page was later repurposed as a static landing page (see the routing correction under Current Limitations / folder structure in `ARCHITECTURE.md`).

### ✅ Phase 6 — Resume Gap Analyzer
*(New, isolated feature — does not modify any existing Phase 1-5 logic.)*

**What:** An independent feature — paste any job description (not just ones already scraped) and get a match score plus concrete resume-improvement suggestions and ATS tips, evaluated against the active resume.
**Why:** Job-match scoring only works on jobs already in the system; this gives the user a tool to evaluate their resume against any posting they find elsewhere, without needing it scraped first.
**How it was built:** as an isolated vertical — its own schema, service, router, and prompt — specifically so it could not affect the existing scoring/tracking/dashboard features.
**Status:** fully working end-to-end. Nothing it produces is saved — every analysis is a fresh call, and the result is lost on page refresh.

### ✅ Phase 7 — AI Interview Preparation Generator
*(New, isolated feature — reuses the existing active-resume lookup and Gemini client without introducing persistence, caching, or background jobs.)*

**What:** A second independent feature — generates interview prep material (project questions, technical questions, behavioral questions, topics to revise, interview tips) for a specific job, tailored to the user's actual resume.
**Why:** Getting a match score isn't the end of the job-search process — this extends the tool into interview preparation.
**How it was built:** the same way as Phase 6 — an isolated vertical that doesn't touch existing scoring or tracking logic.
**Status:** fully working end-to-end. Like Phase 6, nothing is persisted. Unlike every other service in the project, this one currently has no dedicated automated test file — see Current Limitations below.

---

## Pending Phases

> **Renumbering note (2026-07-22):** the original roadmap below used the numbers "Phase 5" (Application Tracking Workflows) and "Phase 6" (Recommendation Engine) for *future* work. Those numbers have since been claimed by real, completed, differently-scoped work above (Phase 5 = AI Recommendation Dashboard, Phase 6 = Resume Gap Analyzer). The pending items originally described under those numbers are kept below under their original working titles, and each has been checked against the current state rather than assumed still-open.

### 🔲 Phase 4 — Polish and Hardening
- ~~Loading skeletons for job list and detail~~ — **done.**
- ~~Remove YC Jobs debug dump~~ — **done.**
- Empty state improvements (first-run experience) — partially addressed, not fully audited page-by-page.
- Pytest service tests with mocked Gemini and DB — **done** for 6 of 7 services. **Still open** for the Interview Prep service, and for every router (no HTTP-layer tests exist anywhere in the suite yet).
- **New cleanup items surfaced by the 2026-07-22 documentation audit** are tracked in `docs/TASKS.md`.

### 🔲 Application Tracking Workflows *(originally slotted as "Phase 5" — number now reassigned, see renumbering note)*
- Status filtering on the list view — **already done**, shipped as part of the base job-listing feature ahead of when this line was originally written.
- Status history / timeline — **still not implemented.** Only the current status is stored; there is no audit trail of prior statuses.
- Bulk status update — **still not implemented.** Status/notes updates operate on one job at a time.

### 🔲 Recommendation Engine *(originally slotted as "Phase 6" — number now reassigned, see renumbering note)*
- Auto-score after sync — **already done**, shipped as part of Phase 5 above, ahead of when this line was originally written.
- Surface top-N jobs by score on dashboard — **already done** (Top Matches, Phase 5).
- Configurable threshold alerts — **still not implemented.** No notification/alerting mechanism of any kind exists.

---

## Current Feature Inventory

| Area | Status |
|---|---|
| Health check | ✅ Working |
| RemoteOK job scraping | ✅ Working |
| YC Jobs scraping | ✅ Working |
| Job storage, deduplication, listing/filtering/pagination, detail view, status/notes update, delete | ✅ Working |
| Stale-score flag on jobs whose resume has since changed | ✅ Working |
| Resume upload, delete, PDF text extraction, AI skill extraction | ✅ Working |
| AI job match scoring, with caching | ✅ Working |
| Consistent API error format | ✅ Working |
| Recommendation dashboard (stats, quality breakdown, top matches) | ✅ Working |
| Auto-scoring of newly scraped jobs | ✅ Working |
| Resume Gap Analyzer (`/resume-review`) | ✅ Working |
| AI Interview Preparation Generator (job detail page) | ✅ Working |
| Landing page, dashboard, job list/detail, resume, resume-review — all interactive with loading states, toasts, and skeletons | ✅ Working |

Full endpoint-by-endpoint and table-by-table detail lives in `API_SPEC.md` and `DATABASE.md`; internal implementation lives in `ARCHITECTURE.md`.

---

## Current Limitations

- **Skill extraction degrades gracefully but silently.** If the AI is unavailable at upload time, the resume is still saved with an empty skills list — the user isn't prompted to retry.
- **Scoring, gap analysis, and interview prep all require an active resume** — each returns a clear error until one is uploaded.
- **RemoteOK jobs are delayed ~24h** vs. the live web listing — expected source behavior, not a bug.
- **The internship keyword filter may miss non-standard job titles.**
- **No background workers or task queue** — the only asynchronous work in the whole system is the post-sync auto-scoring step.
- **No router/integration tests** — the service-layer test suite is thorough, but nothing exercises the API end-to-end at the HTTP layer.
- **No test coverage for the Interview Prep service** — every other service has a dedicated test file; this one does not.
- **The Resume Gap Analyzer and Interview Prep Generator are uncached and unpersisted** — unlike job-match scoring, every call re-invokes the AI and nothing is saved; refreshing the page loses the last result.
- **A stale job score does not resolve itself.** Replacing the active resume does not retroactively re-score existing jobs — each must be re-scored individually. Auto-scoring after a sync only covers jobs newly inserted by that sync.
- **A configured CORS-origins setting exists but isn't actually used** — the CORS middleware is currently hardcoded to `localhost:3000` instead.
- **Known dead code not yet cleaned up:** the details are tracked in `docs/TASKS.md` under Technical Debt.
- **No production deployment configuration** — only the database is containerized; both apps are run locally.
- **No frontend automated test suite** — only lint/type-check run on the frontend.

---

## Project Completion

| Layer | % Complete |
|---|---|
| Database schema + migrations | 100% |
| AI integration (skill extraction, job matching, gap analysis, interview prep) | 100% |
| RemoteOK scraper | 100% |
| YC Jobs scraper | 100% |
| Backend services + API contract | 100% |
| Frontend foundation + interactivity | 100% |
| Recommendation Dashboard | 100% |
| Resume Gap Analyzer | 100% |
| AI Interview Preparation Generator | 100% |
| Tests (service layer) | 100% for 6 of 7 services — Interview Prep service untested |
| Tests (router/integration layer) | 0% — no HTTP-layer tests exist |
| Housekeeping (dead-code cleanup) | 0% — all items still open as of 2026-07-22 |
| **Overall MVP (original 3-capability scope)** | **100%** |
| **Overall, including Phases 5-7** | **~95%** (functionality 100% shipped; test coverage and housekeeping gaps keep this below full completion) |

---

## Next Recommended Phase

**Phase 4 — Polish and Hardening** (still the right next phase, scope refined 2026-07-22)

The core product — collection, scoring, tracking, dashboard, gap analysis, and interview prep — is functionally complete end-to-end. What remains is housekeeping and test-coverage completeness, not new features.

Priority order:
1. Fix the dead-code/config cleanup items identified in the 2026-07-22 audit — all are small, low-risk, high-clarity fixes.
2. Add test coverage for the Interview Prep service, closing the one remaining service-layer gap.
3. Add HTTP-layer (router/integration) tests — currently the only layer with zero automated coverage.
4. Consolidate the two overlapping database-session dependencies.
5. Finish the empty-state audit across all pages.

---

## Long-Term Roadmap

| Phase | Feature | Priority | Status (2026-07-22) |
|---|---|---|---|
| 4 | Dead-code/config cleanup + remaining test coverage | High | Open — see above |
| — | Application status history / timeline | Medium | Not started |
| — | Bulk status update | Medium | Not started |
| — | Configurable score-threshold alerts | Low | Not started |
| Post-MVP | Resume versioning / history | Low | Not started |
| Post-MVP | Cover letter generation | Low | Not started |
| Post-MVP | Additional job sources (e.g. Wellfound) | Low | Not started |
| Post-MVP | Caching for Resume Gap Analyzer / Interview Prep | Low | Not started |
| Post-MVP | Containerized deployment (Dockerfiles, CI/CD) | Low | Not started |
| Post-MVP | Multi-user support / authentication | Low | Not started (explicitly out of scope per PRD) |

> Rows for "Auto-score after sync" and "Recommendation dashboard" have been removed from this table — both shipped as part of Phase 5 and are now tracked as completed above, not as roadmap items.

---

## Last Updated

**Phase:** Phases 5-7 complete (AI Recommendation Dashboard, Resume Gap Analyzer, AI Interview Preparation Generator); documentation restructuring pass
**Date:** 2026-07-22
**Updated by:** Documentation audit — split implementation detail out into `ARCHITECTURE.md`, keeping this file focused on progress/history only
**Next update due:** After Phase 4 housekeeping items (dead-code cleanup + Interview Prep service tests + router tests) are addressed