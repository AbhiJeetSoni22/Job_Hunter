# Testing Strategy & Verification Guide

This document covers the automated test suite (pytest) and manual verification procedures for **AI Internship Hunter**.

---

## 1. Automated Test Suite (Pytest)

The backend includes a comprehensive pytest suite located in `backend/tests/`.

### 1.1 Test Suite Summary

- **Total Test Items Collected**: **123 tests**
- **Test Framework**: `pytest 8.3+` with `pytest-asyncio`, `pytest-mock`, `pytest-cov`
- **Execution State without `TEST_DATABASE_URL`**:
  - **13 Passed** (Non-database unit tests)
  - **110 Skipped** (Database-dependent tests using PostgreSQL)
- **Full Execution Requirement**: Running all 123 tests requires setting `TEST_DATABASE_URL` to a valid PostgreSQL instance.

### 1.2 Test Modules

| Test File | Service / Area Tested | Key Coverage |
|---|---|---|
| `test_job_service.py` | `JobService` | Paginated listing, sorting, status/notes updates, deduplication (`upsert_jobs`), lifecycle aging, and expired job cleanup (`cleanup_expired_jobs`). |
| `test_match_service.py` | `match_service` | Job match scoring, score cache hits/misses, stale score detection (`needs_rescore`), and recommendation label mapping. |
| `test_resume_service.py` | `ResumeService` | PDF validation, text extraction mocking, Gemini skill extraction, single active resume replacement, and resume deletion. |
| `test_scraper_service.py` | `ScraperService` | Scraper orchestration, error handling resilience, `ScrapeRun` logging, `ScoringRun` creation, and background auto-scoring lifecycle. |
| `test_dashboard_service.py` | `DashboardService` | Single-pass aggregate metric calculation, match quality breakdown tiers, top matches filtering, and expired job exclusion. |
| `test_resume_analysis_service.py` | `ResumeAnalysisService` | Resume Gap Analyzer prompt input handling, structured response validation, and active resume requirement checks. |

### 1.3 Test Fixtures & External Mocks (`tests/conftest.py`)

- **Database Fixtures**:
  - `db_engine` (Session-scoped): Creates tables on PostgreSQL test database specified by `TEST_DATABASE_URL`.
  - `db` (Function-scoped): Wraps each test in a transaction and rolls back on teardown for test isolation.
  - `needs_db` marker: Automatically skips DB-dependent tests when `TEST_DATABASE_URL` is omitted.
- **External Dependency Mocks**:
  - `mock_gemini`: Mocks `GeminiClient` in `app.ai.gemini_client.GeminiClient` returning predictable skills or match scores. No real network or Gemini API calls occur during testing.
  - `mock_fitz`: Mocks PyMuPDF `fitz` module for PDF text extraction.
  - `fake_scraper`: Stub implementation of `BaseScraper` for testing scraper orchestration.

### 1.4 Running Backend Tests

```bash
cd backend

# Option A: Run unit tests only (13 passed, 110 skipped)
python -m pytest

# Option B: Run full test suite against PostgreSQL database (all 123 tests)
export TEST_DATABASE_URL="postgresql://postgres:postgres@localhost:5432/test_db"
python -m pytest
```

### 1.5 Current Automated Test Suite Gaps
- **Router / HTTP Integration Tests**: HTTP endpoints in `app/routers/` are not currently covered by FastAPI `TestClient` integration tests.
- **Interview Prep Service Unit Tests**: `InterviewPrepService` currently lacks a dedicated `test_interview_prep_service.py` test file.
- **Frontend Automated Tests**: Frontend does not contain automated Jest or React Testing Library suites (`npm run lint` and type checks available).

---

## 2. Manual Verification Workflows

### 2.1 Interview Preparation Generator Flow
1. Start PostgreSQL (`docker compose up -d`), FastAPI backend, and Next.js frontend.
2. Upload a valid PDF resume at `/resume`.
3. Open a saved job detail page (`/jobs/[id]`).
4. Click **Generate Interview Prep**.
5. Verify inline rendering of:
   - Project Questions
   - Technical Questions
   - Behavioral Questions
   - Topics To Revise
   - Interview Tips
6. Verify failure behavior when no resume exists (HTTP 422 `NO_RESUME`).

### 2.2 Resume Gap Analyzer Flow
1. Navigate to `/resume-review`.
2. Confirm active resume detection.
3. Paste an external job description into the text area.
4. Click **Analyze**.
5. Confirm match score, summary, missing skills, strengths, improvement suggestions, and ATS tips render correctly.

### 2.3 Background Scoring & Polling Flow
1. Navigate to `/dashboard`.
2. Click **Sync Jobs**.
3. Confirm `ScoringRun` progress indicator shows live scoring progress.
4. Verify polling stops automatically when status reaches `completed`.
