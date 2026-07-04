# API Specification

**Base URL:** `http://localhost:8000`
**Format:** JSON request/response bodies
**Interactive Docs:** `http://localhost:8000/docs`

---

# Conventions

All successful responses:

```json
{
  "data": {},
  "error": null
}
```

All error responses:

```json
{
  "data": null,
  "error": {
    "code": "NOT_FOUND",
    "message": "Job not found"
  }
}
```

Timestamps use ISO 8601 UTC format:

```text
2026-06-17T10:00:00Z
```

UUIDs are lowercase hyphenated strings.

Nullable fields are returned as `null` and never omitted.

---

# Health

## GET /api/health

Checks application and database health.

### Response 200

```json
{
  "status": "ok",
  "database": "connected"
}
```

### Response 503

```json
{
  "status": "degraded",
  "database": "unreachable"
}
```

---

# Scraper

## POST /api/scraper/run

Run all configured job sources synchronously.

Sources:

* RemoteOK API
* YC Jobs

### Response 200

```json
{
  "data": {
    "runs": [
      {
        "source": "remoteok",
        "jobs_found": 45,
        "jobs_new": 12,
        "error": null,
        "started_at": "2026-06-17T10:00:00Z",
        "completed_at": "2026-06-17T10:00:03Z"
      }
    ],
    "total_new": 12,
    "total_scored": 12
  },
  "error": null
}
```

One source failing must not stop other sources.

Newly inserted jobs are automatically scored against the active resume
(Phase 5 — Feature 4). `total_scored` reports how many of the newly
inserted jobs were scored. Pre-existing jobs are never rescored by a
sync. If no resume is uploaded, `total_scored` is `0` and the sync
still succeeds — auto-scoring is simply skipped.

---

## GET /api/scraper/status

Returns the latest scrape run for each source.

### Response 200

```json
{
  "data": [
    {
      "source": "remoteok",
      "jobs_found": 45,
      "jobs_new": 12,
      "error": null,
      "started_at": "2026-06-17T10:00:00Z",
      "completed_at": "2026-06-17T10:00:03Z"
    }
  ],
  "error": null
}
```

---

# Jobs

## GET /api/jobs

Returns jobs with filtering, sorting and pagination.

### Query Parameters

| Param     | Type    | Default    |
| --------- | ------- | ---------- |
| page      | integer | 1          |
| page_size | integer | 20         |
| sort_by   | string  | created_at |
| order     | string  | desc       |
| status    | string  | null       |
| source    | string  | null       |
| scored    | boolean | null       |

### Valid sort_by

```text
created_at
posted_at
match_score
```

### Response 200

```json
{
  "data": {
    "jobs": [],
    "total": 120,
    "page": 1,
    "page_size": 20
  },
  "error": null
}
```

### Notes

List endpoint intentionally omits:

* description
* notes
* match_summary

Use Job Detail endpoint for full information.

---

## GET /api/jobs/{id}

Returns a complete job record.

### Response 200

```json
{
  "data": {
    "id": "uuid",
    "title": "Backend Intern",
    "company": "Acme",
    "company_url": "https://example.com",
    "description": "Job description",
    "url": "https://job-url.com",
    "source": "remoteok",
    "location": "Remote",

    "status": "saved",
    "notes": null,

    "match_score": 82,
    "missing_skills": ["Docker"],
    "match_summary": "Strong backend fit.",
    "matched_at": "2026-06-17T10:00:00Z",

    "resume_uploaded_at": "2026-06-16T09:00:00Z",

    "posted_at": "2026-06-15T00:00:00Z",
    "created_at": "2026-06-17T10:00:00Z",
    "updated_at": "2026-06-17T10:00:00Z"
  },
  "error": null
}
```

### Response 404

```json
{
  "data": null,
  "error": {
    "code": "NOT_FOUND",
    "message": "Job not found"
  }
}
```

---

## POST /api/jobs/{id}/score

Runs Gemini job matching.

Uses cached results when available.

Requires an active resume.

### Response 200

```json
{
  "data": {
    "match_score": 82,
    "missing_skills": ["Docker", "GraphQL"],
    "match_summary": "Strong fit.",
    "matched_at": "2026-06-17T10:00:00Z",

    "cached": true,
    "needs_rescore": false,
    "recommendation_label": "Strong Match"
  },
  "error": null
}
```

### Example When Resume Changed

```json
{
  "data": {
    "match_score": 82,
    "missing_skills": ["Docker", "GraphQL"],
    "match_summary": "Strong fit.",
    "matched_at": "2026-06-10T10:00:00Z",

    "cached": true,
    "needs_rescore": true
  },
  "error": null
}
```

### Response 422

```json
{
  "data": null,
  "error": {
    "code": "NO_RESUME",
    "message": "Upload a resume before scoring jobs"
  }
}
```

### Response 404

```json
{
  "data": null,
  "error": {
    "code": "NOT_FOUND",
    "message": "Job not found"
  }
}
```

---

## PATCH /api/jobs/{id}

Updates status and/or notes.

### Request

```json
{
  "status": "applied",
  "notes": "Submitted application."
}
```

Both fields are optional.

### Valid Status Values

```text
saved
applied
interview
offer
rejected
```

### Response 200

```json
{
  "data": {
    "id": "uuid",
    "status": "applied",
    "notes": "Submitted application."
  },
  "error": null
}
```

### Response 422

```json
{
  "data": null,
  "error": {
    "code": "INVALID_STATUS",
    "message": "Invalid status"
  }
}
```

---

## DELETE /api/jobs/{id}

Permanently removes a job record.

### Response 204

No response body.

### Response 404

```json
{
  "data": null,
  "error": {
    "code": "NOT_FOUND",
    "message": "Job not found"
  }
}
```

---

# Dashboard

## GET /api/dashboard/stats

Returns aggregate statistics for the AI-powered recommendation dashboard
(Phase 5). Computed with a single aggregate SQL query plus one indexed
top-N query — no N+1 queries regardless of job count.

### Response 200

```json
{
  "data": {
    "total_jobs": 120,
    "scored_jobs": 48,
    "average_match_score": 71.4,
    "best_match_score": 96,
    "applications_submitted": 5,
    "quality_breakdown": {
      "excellent": 6,
      "good": 14,
      "possible": 18,
      "weak": 10
    },
    "top_matches": [
      {
        "id": "uuid",
        "title": "Frontend Engineer",
        "company": "Acme",
        "match_score": 95,
        "source": "remoteok",
        "status": "saved",
        "recommendation_label": "Excellent Match"
      }
    ]
  },
  "error": null
}
```

### Notes

* `quality_breakdown` buckets every **scored** job: Excellent (>= 90),
  Good (75-89), Possible (60-74), Weak (< 60). Unscored jobs are excluded.
* `top_matches` returns the top 5 scored jobs sorted descending by
  `match_score`. Unscored jobs are excluded.
* `recommendation_label` is derived from `match_score`: 95-100
  "Excellent Match", 80-94 "Strong Match", 65-79 "Potential Match",
  below 65 "Low Match". It is also returned on `JobListItem`,
  `JobResponse`, and the score endpoint response below.

---

# Resume

## POST /api/resume

Uploads a PDF resume.

> **Known issue:** `routers/resume.py` currently has a stray duplicate route decorator left over from a previous edit (see `TASKS.md`, Phase 2). It has not been observed to change actual behavior — `POST /api/resume` still correctly reaches the upload handler in testing — but it's a code smell worth fixing before this file is considered final.

Process:

```text
PDF
↓
PyMuPDF
↓
Extract Text
↓
Gemini
↓
Skills
↓
Save Resume
```

### Validation

* PDF only
* Maximum file size: 5 MB

### Request

```text
multipart/form-data
```

Field:

```text
file
```

### Response 200

```json
{
  "data": {
    "id": "uuid",
    "filename": "resume.pdf",
    "skills": [
      "Python",
      "FastAPI",
      "PostgreSQL",
      "Next.js"
    ],
    "uploaded_at": "2026-06-17T10:00:00Z"
  },
  "error": null
}
```

### Response 422

```json
{
  "data": null,
  "error": {
    "code": "INVALID_FILE",
    "message": "File must be a PDF under 5 MB"
  }
}
```

---

## GET /api/resume

Returns the active resume.

### Response 200

```json
{
  "data": {
    "id": "uuid",
    "filename": "resume.pdf",
    "skills": [
      "Python",
      "FastAPI",
      "PostgreSQL"
    ],
    "uploaded_at": "2026-06-17T10:00:00Z"
  },
  "error": null
}
```

### Response 404

```json
{
  "data": null,
  "error": {
    "code": "NO_RESUME",
    "message": "No resume uploaded"
  }
}
```

---

## DELETE /api/resume

Deletes the active resume.

### Response 204

No response body.

### Response 404

```json
{
  "data": null,
  "error": {
    "code": "NO_RESUME",
    "message": "No resume uploaded"
  }
}
```

---

## GET /api/resume/{id}

Returns a specific resume by ID. Since only one resume ever exists at a time, this is mainly useful for confirming a specific upload's ID after the fact — `GET /api/resume` (no ID) is the endpoint the frontend uses day-to-day.

### Response 200

Same shape as `GET /api/resume`.

### Response 404

```json
{
  "data": null,
  "error": {
    "code": "NOT_FOUND",
    "message": "Resume {id} not found"
  }
}
```

---

# Error Codes

| Code           | Status | Where it's raised                                    |
| -------------- | ------ | ------------------------------------------------------ |
| NOT_FOUND      | 404    | Job or job ID not found                                |
| NO_RESUME      | 404    | `GET/DELETE /api/resume` when no resume is uploaded    |
| NO_RESUME      | 422    | `POST /api/jobs/{id}/score` when no resume is uploaded — scoring is a write operation that requires a resume as input, so it's treated as a validation failure rather than a missing resource |
| INVALID_FILE   | 422    | Resume upload — not a PDF, or over 5 MB                |
| INVALID_STATUS | 422    | `PATCH /api/jobs/{id}` with an invalid status value    |
| INVALID_PARAM  | 422    | `GET /api/jobs` with an invalid `sort_by`/`order`      |
| VALIDATION_ERROR | 422  | Request body fails Pydantic validation                 |
| EXTRACTION_ERROR | 500  | PyMuPDF or Gemini extraction failure during upload      |
| AI_ERROR       | 502    | Gemini API call failed after all retries                |
| INTERNAL_ERROR | 500    | Unhandled exception (message never leaks internals)     |

Note: `NO_RESUME` intentionally maps to two different status codes depending on context — this is not a bug. On the resume resource itself, "no resume" is a 404 (the resource doesn't exist). On the scoring endpoint, "no resume" is a 422 (the request can't be validated without one).