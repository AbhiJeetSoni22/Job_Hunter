# API Specification

**Base URL:** `http://localhost:8000`  
**Format:** JSON Request & Response Bodies  
**Interactive OpenAPI Docs:** `http://localhost:8000/docs`  

---

## Envelope Conventions

Standard application API endpoints use the uniform `ApiResponse[T]` envelope structure. `GET /api/health` is a deliberate exception and returns a dedicated health payload.

### Successful Response Envelope
```json
{
  "data": { ... },
  "error": null
}
```

### Error Response Envelope
```json
{
  "data": null,
  "error": {
    "code": "ERROR_CODE_STRING",
    "message": "Detailed error description string"
  }
}
```

### Serialization Rules
- **Timestamps**: Serialized in ISO 8601 UTC format (e.g., `2026-08-05T14:30:00Z`).
- **Identifiers**: Primary keys are lowercase hyphenated UUID strings.
- **Nullable Fields**: Explicitly serialized as `null` (never omitted from JSON).

---

## Registered Endpoints Index (19 Endpoints)

| Category | Method | Path | Summary |
|---|---|---|---|
| Health | `GET` | `/api/health` | Liveness and database connectivity check |
| Auth | `POST` | `/api/auth/register` | Register a new user account |
| Auth | `POST` | `/api/auth/login` | Authenticate user credentials and return JWT token |
| Auth | `GET` | `/api/auth/me` | Retrieve authenticated user profile |
| Jobs | `GET` | `/api/jobs` | Filtered, sorted, paginated job listing |
| Jobs | `GET` | `/api/jobs/{job_id}` | Detailed job listing by ID |
| Jobs | `POST` | `/api/jobs/{job_id}/score` | Score job against active resume |
| Jobs | `PATCH` | `/api/jobs/{job_id}` | Update job application status or notes |
| Jobs | `DELETE` | `/api/jobs/{job_id}` | Delete job listing |
| Interview Prep | `POST` | `/api/jobs/{job_id}/interview-prep` | Generate AI interview preparation material |
| Scraper | `POST` | `/api/scraper/run` | Trigger job collection across all scrapers |
| Scraper | `GET` | `/api/scraper/status` | Get latest scrape run result per source |
| Scraper | `GET` | `/api/scraper/scoring-status` | Poll background auto-scoring run progress |
| Resume | `POST` | `/api/resume` | Upload PDF resume, extract text and skills |
| Resume | `GET` | `/api/resume` | Get current active resume |
| Resume | `DELETE` | `/api/resume` | Delete active resume |
| Resume | `GET` | `/api/resume/{resume_id}` | Get resume by ID |
| Resume Analysis | `POST` | `/api/resume/analyze` | Analyze active resume against pasted job text |
| Dashboard | `GET` | `/api/dashboard/stats` | Get aggregate recommendation dashboard metrics |

---

## 1. Health

### GET /api/health
Checks application status and PostgreSQL database connectivity.

**Response 200 (Healthy):**
```json
{
  "status": "ok",
  "database": "connected"
}
```

**Response 503 (Database Unreachable):**
```json
{
  "status": "degraded",
  "database": "unreachable"
}
```

---

## 1.1 Auth Router (`/api/auth`)

### POST /api/auth/register
Registers a new user account with Argon2id password hashing.

**Request Body:**
```json
{
  "email": "user@example.com",
  "name": "Jane Doe",
  "password": "securepassword123"
}
```

**Response 201 (Created):**
```json
{
  "data": {
    "id": "7a1b2c3d-4e5f-6a7b-8c9d-0e1f2a3b4c5d",
    "email": "user@example.com",
    "name": "Jane Doe",
    "is_active": true,
    "created_at": "2026-09-13T17:40:00Z",
    "updated_at": "2026-09-13T17:40:00Z"
  },
  "error": null
}
```

**Response 409 (Conflict - Duplicate Email):**
```json
{
  "data": null,
  "error": {
    "code": "EMAIL_ALREADY_EXISTS",
    "message": "User with this email already exists"
  }
}
```

---

### POST /api/auth/login
Authenticates user credentials and issues a PyJWT access token (valid for 7 days / 10080 minutes).

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Response 200 (OK):**
```json
{
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer"
  },
  "error": null
}
```

**Response 401 (Unauthorized - Generic Credentials Error):**
```json
{
  "data": null,
  "error": {
    "code": "INVALID_CREDENTIALS",
    "message": "Invalid email or password"
  }
}
```

---

### GET /api/auth/me
Retrieves profile for the currently authenticated user based on `Authorization: Bearer <token>` header.

**Headers:**
`Authorization: Bearer <access_token>`

**Response 200 (OK):**
```json
{
  "data": {
    "id": "7a1b2c3d-4e5f-6a7b-8c9d-0e1f2a3b4c5d",
    "email": "user@example.com",
    "name": "Jane Doe",
    "is_active": true,
    "created_at": "2026-09-13T17:40:00Z",
    "updated_at": "2026-09-13T17:40:00Z"
  },
  "error": null
}
```

**Response 401 (Unauthorized - Missing / Invalid Token):**
```json
{
  "data": null,
  "error": {
    "code": "INVALID_TOKEN",
    "message": "Invalid access token"
  }
}
```

---

## 2. Jobs Router (`/api/jobs`)

### GET /api/jobs
Returns a paginated, filtered, and sorted list of job listings.

**Query Parameters:**
| Parameter | Type | Default | Description |
|---|---|---|---|
| `page` | integer | `1` | Page number (ge=1) |
| `page_size` | integer | `20` | Items per page (ge=1, le=100) |
| `sort_by` | string | `created_at` | Sort column (`created_at`, `posted_at`, `match_score`) |
| `order` | string | `desc` | Sort order (`asc`, `desc`) |
| `status` | string | `null` | Filter by status (`saved`, `applied`, `interview`, `offer`, `rejected`) |
| `source` | string | `null` | Filter by scraper source (`remoteok`, `yc_jobs`) |
| `scored` | boolean | `null` | Filter by scoring state (`true` = scored, `false` = unscored) |
| `include_expired` | boolean | `false` | Include expired jobs (`expired_at IS NOT NULL`) in results |

**Response 200:**
```json
{
  "data": {
    "jobs": [
      {
        "id": "c1f7b8a0-2d3e-4f5a-6b7c-8d9e0f1a2b3c",
        "title": "Backend Engineering Intern",
        "company": "Acme Corp",
        "company_url": "https://example.com",
        "url": "https://example.com/jobs/backend-intern-1",
        "source": "remoteok",
        "location": "Remote",
        "status": "saved",
        "match_score": 85,
        "needs_rescore": false,
        "expired_at": null,
        "posted_at": "2026-08-01T00:00:00Z",
        "created_at": "2026-08-02T10:00:00Z",
        "updated_at": "2026-08-02T10:00:00Z"
      }
    ],
    "total": 45,
    "page": 1,
    "page_size": 20
  },
  "error": null
}
```

**Response 422 (Invalid Parameter):**
```json
{
  "data": null,
  "error": {
    "code": "INVALID_PARAM",
    "message": "Invalid sort_by 'invalid'. Must be one of: created_at, match_score, posted_at"
  }
}
```

---

### GET /api/jobs/{job_id}
Fetches complete detail for a single job listing.

**Path Parameters:**
- `job_id` (UUID, required): Job primary key.

**Response 200:**
```json
{
  "data": {
    "id": "c1f7b8a0-2d3e-4f5a-6b7c-8d9e0f1a2b3c",
    "title": "Backend Engineering Intern",
    "company": "Acme Corp",
    "company_url": "https://example.com",
    "description": "Full job description text...",
    "url": "https://example.com/jobs/backend-intern-1",
    "source": "remoteok",
    "location": "Remote",
    "status": "saved",
    "notes": "Spoke with recruiter.",
    "match_score": 85,
    "missing_skills": ["Docker", "Kubernetes"],
    "match_summary": "Strong Python fit. Missing container orchestration skills.",
    "matched_at": "2026-08-02T10:05:00Z",
    "needs_rescore": false,
    "resume_uploaded_at": "2026-08-01T09:00:00Z",
    "expired_at": null,
    "posted_at": "2026-08-01T00:00:00Z",
    "created_at": "2026-08-02T10:00:00Z",
    "updated_at": "2026-08-02T10:05:00Z"
  },
  "error": null
}
```

**Response 404 (Not Found):**
```json
{
  "data": null,
  "error": {
    "code": "NOT_FOUND",
    "message": "Job c1f7b8a0-2d3e-4f5a-6b7c-8d9e0f1a2b3c not found"
  }
}
```

---

### POST /api/jobs/{job_id}/score
Scores a job against the active resume using Gemini AI. Returns cached result if score is fresh.

**Path Parameters:**
- `job_id` (UUID, required): Job primary key.

**Response 200:**
```json
{
  "data": {
    "match_score": 85,
    "missing_skills": ["Docker", "Kubernetes"],
    "match_summary": "Strong Python fit. Missing container orchestration skills.",
    "matched_at": "2026-08-02T10:05:00Z",
    "cached": true,
    "needs_rescore": false,
    "recommendation_label": "Strong Match"
  },
  "error": null
}
```

**Response 422 (No Active Resume):**
```json
{
  "data": null,
  "error": {
    "code": "NO_RESUME",
    "message": "Upload a resume before scoring jobs"
  }
}
```

**Response 502 (AI Error):**
```json
{
  "data": null,
  "error": {
    "code": "AI_ERROR",
    "message": "Gemini match_job failed after 3 attempts: ..."
  }
}
```

---

### PATCH /api/jobs/{job_id}
Updates job application tracking status and/or free-text notes.

**Path Parameters:**
- `job_id` (UUID, required): Job primary key.

**Request Body:**
```json
{
  "status": "applied",
  "notes": "Applied via company portal on Aug 3."
}
```

**Response 200:**
```json
{
  "data": {
    "id": "c1f7b8a0-2d3e-4f5a-6b7c-8d9e0f1a2b3c",
    "title": "Backend Engineering Intern",
    "company": "Acme Corp",
    "company_url": "https://example.com",
    "description": "Full job description text...",
    "url": "https://example.com/jobs/backend-intern-1",
    "source": "remoteok",
    "location": "Remote",
    "status": "applied",
    "notes": "Applied via company portal on Aug 3.",
    "match_score": 85,
    "missing_skills": ["Docker", "Kubernetes"],
    "match_summary": "Strong Python fit. Missing container orchestration skills.",
    "matched_at": "2026-08-02T10:05:00Z",
    "posted_at": "2026-08-01T00:00:00Z",
    "created_at": "2026-08-02T10:00:00Z",
    "updated_at": "2026-08-03T14:20:00Z"
  },
  "error": null
}
```

**Response 422 (Invalid Status):**
```json
{
  "data": null,
  "error": {
    "code": "INVALID_STATUS",
    "message": "Invalid status 'submitted'. Must be one of: applied, interview, offer, rejected, saved"
  }
}
```

---

### DELETE /api/jobs/{job_id}
Permanently deletes a job listing.

**Path Parameters:**
- `job_id` (UUID, required): Job primary key.

**Response 204:** No content.

---

### POST /api/jobs/{job_id}/interview-prep
Generates AI interview preparation questions and tips for a saved job using the active resume.

**Path Parameters:**
- `job_id` (UUID, required): Job primary key.

**Response 200:**
```json
{
  "data": {
    "project_questions": [
      "In your FastAPI project, how did you handle database transaction rollbacks during failure?",
      "Why did you choose PostgreSQL over a Document store for skill indexing?"
    ],
    "technical_questions": [
      "Explain the difference between synchronous and asynchronous tasks in FastAPI.",
      "How do Docker container networks communicate with PostgreSQL instances?"
    ],
    "behavioral_questions": [
      "Describe a situation where a background sync failed and how you communicated the issue."
    ],
    "topics_to_revise": [
      "Docker Compose container networking",
      "PostgreSQL JSONB indexing techniques"
    ],
    "interview_tips": [
      "Highlight your hands-on experience building custom FastAPI exception envelopes."
    ]
  },
  "error": null
}
```

**Response 422 (No Active Resume):**
```json
{
  "data": null,
  "error": {
    "code": "NO_RESUME",
    "message": "Upload a resume before generating interview prep."
  }
}
```

---

## 3. Scraper Router (`/api/scraper`)

### POST /api/scraper/run
Triggers on-demand job collection from RemoteOK and YC Jobs. Schedules background auto-scoring when new jobs are inserted.

**Response 200:**
```json
{
  "data": {
    "runs": [
      {
        "source": "remoteok",
        "jobs_found": 30,
        "jobs_new": 5,
        "error": null,
        "started_at": "2026-08-05T10:00:00Z",
        "completed_at": "2026-08-05T10:00:02Z"
      },
      {
        "source": "yc_jobs",
        "jobs_found": 15,
        "jobs_new": 2,
        "error": null,
        "started_at": "2026-08-05T10:00:02Z",
        "completed_at": "2026-08-05T10:00:10Z"
      }
    ],
    "total_new": 7,
    "total_scored": 0,
    "new_job_ids": ["uuid1", "uuid2", "uuid3", "uuid4", "uuid5", "uuid6", "uuid7"],
    "scoring_run_id": "a9b8c7d6-e5f4-3a2b-1c0d-9e8f7a6b5c4d"
  },
  "error": null
}
```

---

### GET /api/scraper/status
Returns the most recent scrape run result per configured source.

**Response 200:**
```json
{
  "data": [
    {
      "source": "remoteok",
      "jobs_found": 30,
      "jobs_new": 5,
      "error": null,
      "started_at": "2026-08-05T10:00:00Z",
      "completed_at": "2026-08-05T10:00:02Z"
    }
  ],
  "error": null
}
```

---

### GET /api/scraper/scoring-status
Returns progress for one background auto-scoring batch (`ScoringRun`).

**Query Parameters:**
- `run_id` (UUID, required): `scoring_run_id` returned from `POST /api/scraper/run`.

**Response 200:**
```json
{
  "data": {
    "status": "running",
    "total": 7,
    "scored": 3,
    "failed": 0,
    "pending": 4
  },
  "error": null
}
```

---

## 4. Resume Router (`/api/resume`)

### POST /api/resume
Uploads a PDF resume, extracts text via PyMuPDF, and extracts skills via Gemini AI. Replaces any existing active resume.

**Request:** `multipart/form-data` with `file` field containing PDF document.

**Response 200:**
```json
{
  "data": {
    "id": "e5f4d3c2-b1a0-9f8e-7d6c-5b4a3f2e1d0c",
    "filename": "candidate_resume.pdf",
    "skills": ["Python", "FastAPI", "PostgreSQL", "React", "TypeScript"],
    "uploaded_at": "2026-08-01T09:00:00Z"
  },
  "error": null
}
```

**Response 422 (Invalid File):**
```json
{
  "data": null,
  "error": {
    "code": "INVALID_FILE",
    "message": "Only PDF files are supported"
  }
}
```

---

### GET /api/resume
Returns current active resume details.

**Response 200:**
```json
{
  "data": {
    "id": "e5f4d3c2-b1a0-9f8e-7d6c-5b4a3f2e1d0c",
    "filename": "candidate_resume.pdf",
    "skills": ["Python", "FastAPI", "PostgreSQL", "React", "TypeScript"],
    "uploaded_at": "2026-08-01T09:00:00Z"
  },
  "error": null
}
```

**Response 404 (No Active Resume):**
```json
{
  "data": null,
  "error": {
    "code": "NO_RESUME",
    "message": "No active resume found"
  }
}
```

---

### DELETE /api/resume
Deletes active resume.

**Response 204:** No content.

---

### GET /api/resume/{resume_id}
Fetches a specific resume by primary key UUID.

**Response 200:** Same structure as `GET /api/resume`.

---

## 5. Resume Analysis Router (`/api/resume`)

### POST /api/resume/analyze
Evaluates active resume against a pasted job description (Resume Gap Analyzer).

**Request Body:**
```json
{
  "job_description": "We are seeking a Software Engineer Intern with experience in Python and Docker..."
}
```

**Response 200:**
```json
{
  "data": {
    "match_score": 75,
    "summary": "Good overall alignment with core Python requirements. Main gap is containerization.",
    "missing_skills": ["Docker", "Kubernetes"],
    "strengths": ["Python", "FastAPI", "PostgreSQL"],
    "suggestions": [
      "Add a project section showcasing Docker container deployment.",
      "Quantify API performance improvements in previous project bullet points."
    ],
    "ats_tips": [
      "Ensure exact term 'Docker' is included under technical skills.",
      "Use standard section header 'Technical Skills' for ATS parsers."
    ]
  },
  "error": null
}
```

---

## 6. Dashboard Router (`/api/dashboard`)

### GET /api/dashboard/stats
Returns aggregate metrics and top matches for recommendation dashboard. Excludes expired jobs (`expired_at IS NOT NULL`).

**Response 200:**
```json
{
  "data": {
    "total_jobs": 120,
    "scored_jobs": 40,
    "average_match_score": 78.5,
    "best_match_score": 95,
    "applications_submitted": 8,
    "quality_breakdown": {
      "excellent": 5,
      "good": 15,
      "possible": 12,
      "weak": 8
    },
    "top_matches": [
      {
        "id": "c1f7b8a0-2d3e-4f5a-6b7c-8d9e0f1a2b3c",
        "title": "Backend Engineering Intern",
        "company": "Acme Corp",
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