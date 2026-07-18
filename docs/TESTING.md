# Testing

This document covers the current manual verification flow for the Interview Preparation Generator feature.

## Scope

The Interview Preparation Generator is a stateless, on-demand AI flow that runs from the job detail page.

It should be verified against:

- a saved job record
- an uploaded active resume
- the existing Gemini integration
- the job detail page UI

No database writes, no caching, and no background jobs are expected as part of this feature.

---

## Manual Test Instructions

### 1. Prepare the environment

1. Start PostgreSQL with Docker Compose.
2. Start the FastAPI backend.
3. Start the Next.js frontend.
4. Upload a valid PDF resume.
5. Sync or create at least one saved job.

### 2. Run the interview-prep flow

1. Open the job detail page for a saved job.
2. Confirm the active resume exists.
3. Click "Generate Interview Prep".
4. Confirm the UI renders the result sections:
   - Technical Questions
   - Behavioral Questions
   - Project Questions
   - Topics To Revise
   - Interview Tips

### 3. Validate expected behavior

The API should:

- return HTTP 200 on a successful request
- return a JSON envelope with `data` and `error: null`
- use the current job row for `job_id`, `title`, `company`, and `description`
- use the active uploaded resume text for generation
- return the result directly without saving or caching it

### 4. Validate failure cases

The feature should fail gracefully in these scenarios:

- No active resume uploaded → HTTP 422 with `NO_RESUME`
- Job ID does not exist → HTTP 404 with `NOT_FOUND`
- Gemini request fails after retries → HTTP 502 with `INTERVIEW_PREP_ERROR`

---

## Expected Outcome

A successful run should produce a tailored, job-specific set of interview-prep guidance grounded in the resume and job description. The response should stay concise, structured, and immediately usable from the job detail page.

## Notes

This feature is intentionally V1 and isolated. It reuses the existing Gemini path and the active resume lookup; it does not introduce new persistence, infrastructure, or async processing.
