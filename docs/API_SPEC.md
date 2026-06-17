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
    "total_new": 12
  },
  "error": null
}
```

One source failing must not stop other sources.

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
    "needs_rescore": false
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

# Resume

## POST /api/resume

Uploads a PDF resume.

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

# Error Codes

| Code           | Status |
| -------------- | ------ |
| NOT_FOUND      | 404    |
| NO_RESUME      | 422    |
| INVALID_FILE   | 422    |
| INVALID_STATUS | 422    |
| SCRAPER_ERROR  | 500    |
| AI_ERROR       | 502    |
