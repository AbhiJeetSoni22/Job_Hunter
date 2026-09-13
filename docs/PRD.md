# Product Requirements Document (PRD)

**Project:** AI Internship Hunter / Job Hunter  
**Version:** 1.0  
**Scope:** Personal Use  

---

## 1. Problem Statement

Internship hunting is manually intensive and fragmented. Candidates spend hours across multiple job boards, manually scanning listings, evaluating technical fit against their resume in their heads, and tracking applications in disconnected spreadsheets or browser tabs.

This leads to missed high-alignment opportunities, wasted time on low-fit roles, and disorganized application tracking.

---

## 2. Product Vision & Goals

Build an intelligent personal job discovery and application management system that:
1. **Automates Discovery**: Aggregates entry-level and internship listings from multiple sources in one place.
2. **Ranks by Compatibility**: Evaluates job descriptions against the candidate's resume using AI to surface match scores and technical skill gaps.
3. **Streamlines Application Tracking**: Provides a unified pipeline (`saved` → `applied` → `interview` → `offer` / `rejected`) with notes and status management.
4. **Accelerates Preparation**: Offers on-demand AI tools for resume gap analysis and job-specific interview preparation.

**Secondary Goal**: Maintain a clean, production-grade architectural baseline suitable for personal portfolio demonstration and future multi-tenant expansion.

---

## 3. User Persona

- **Target User**: Single candidate / student / early-career software engineer.
- **Scope**: Single-user deployment. No authentication, multi-tenancy, or multi-user accounts in current scope.

---

## 4. Product Capabilities

### 4.1 Job Collection & Synchronization (Implemented)
- **Source Aggregation**: Collect job listings from RemoteOK and Y Combinator Work at a Startup.
- **Canonical Deduplication**: Deduplicate listings across sources using canonical job URLs.
- **On-Demand Sync**: Trigger synchronization on demand via the UI.
- **Metadata Storage**: Store title, company, company URL, location, source, description, and source posting dates.

### 4.2 Resume Upload & Parsing (Implemented)
- **PDF Upload**: Single active resume supported (uploading a new resume replaces the active resume).
- **Text & Skill Extraction**: Automatically extract plain text and normalized technical skills via AI.
- **Validation**: Enforce valid PDF file type and non-empty text extraction requirements.

### 4.3 Persistent Match Scoring (Implemented)
- **Fit Evaluation**: Generate fit scores (0–100), missing technical skills (up to 5 items), and two-sentence alignment summaries using AI.
- **Background Processing**: Persistently track and schedule auto-scoring in a FastAPI background task without blocking the initial sync response.
- **Batch Tracking**: Persist scoring progress and terminal states so frontends can display live progress and stop polling cleanly upon completion.
- **Stale Score Detection**: Detect when a job score was generated against an older resume version ("Needs Re-score").

### 4.4 Job Lifecycle & Expiration (Implemented)
- **Missing Sync Tracking**: Track consecutive scraper syncs where a job's URL was no longer present.
- **Expiration Flagging**: Mark jobs as expired after 2 consecutive missing syncs.
- **Filtered Display**: Exclude expired jobs from default job listings and recommendation dashboard calculations while allowing explicit inclusion via filters.
- **Un-annotated Job Cleanup**: Support an on-demand management command to purge un-annotated, saved expired jobs older than N days.

### 4.5 Application Pipeline Tracking (Implemented)
- **Pipeline Stages**: Support status transitions: `saved` → `applied` → `interview` → `offer` / `rejected`.
- **User Annotations**: Allow free-text notes per job listing for recruiter contact information, interview dates, and notes.

### 4.6 Recommendation Dashboard (Implemented)
- **Aggregate Analytics**: Display key application metrics: total active jobs, scored job count, average/best match score, and applications submitted.
- **Match Quality Breakdown**: Categorize scored jobs into tiers (Excellent, Good, Possible, Weak).
- **Top Matches**: Surface the top 5 highest-scoring active jobs with recommendation labels.

### 4.7 Resume Gap Analyzer (Implemented)
- **On-Demand Analysis**: Allow candidate to paste any job description and compare it against their active resume.
- **Actionable Feedback**: Provide match score, overall fit summary, missing skills, existing strengths, concrete resume improvement suggestions, and ATS optimization tips.
- **Stateless Execution**: Operate independently without creating persistent job records or modifying existing match scores.

### 4.8 AI Interview Preparation Generator (Implemented)
- **Job-Grounded Material**: Generate tailored interview preparation material for a saved job using the candidate's active resume and the job listing.
- **Structured Categories**: Provide project-based questions, technical questions, behavioral questions, technical revision topics, and strategic interview tips.
- **Inline Display**: Render results directly on the job detail page without requiring persistent storage.

---

## 5. User Flows

### Flow 1: Resume Setup & Synchronization
1. Candidate uploads PDF resume.
2. Candidate triggers job synchronization.
3. System scrapers run, insert new job listings, and launch background scoring.
4. Candidate views live scoring progress until completed.

### Flow 2: Evaluating & Tracking Jobs
1. Candidate views top matches on Recommendation Dashboard (`/dashboard`).
2. Candidate filters job listing (`/jobs`) by match score or status.
3. Candidate reviews detailed breakdown, updates status to `applied`, and adds application notes.

### Flow 3: Tailoring Resume & Preparing for Interviews
1. Candidate uses Resume Gap Analyzer (`/resume-review`) with external job text for instant improvement feedback.
2. Candidate opens saved job detail page (`/jobs/[id]`) and generates tailored interview preparation guidance.

---

## 6. Success Criteria

| Criterion | Target Metric |
|---|---|
| Discovery Efficiency | Aggregates >20 listings per sync attempt across active sources |
| Parsing Accuracy | Extracts technical skills cleanly from standard PDF resume layouts |
| Scoring Responsiveness | Background scoring tracks progress to completion without stalling |
| Pipeline Integrity | Job status transitions and notes persist reliably across sessions |
| Error Resilience | Scraper or AI service degradation fails gracefully without breaking app UI |

---

## 7. Explicit Out-of-Scope Capabilities (Future Phase Candidates)

- Multi-user authentication & user account isolation
- ATS Resume Optimizer (auto-editing/tailoring resume PDFs)
- Automated application auto-fill / browser extension submitters
- Cover letter generation
- Scheduled cron syncing built into main app server process
- Email / SMS application reminder notifications