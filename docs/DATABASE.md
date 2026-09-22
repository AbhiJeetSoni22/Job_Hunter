# Database Specification

**Engine:** PostgreSQL 16  
**ORM:** SQLAlchemy 2.x (Mapped Types)  
**Migration Tool:** Alembic  

---

## 1. Overview & Architectural Design Decisions

- **Six Core Tables**: `users`, `jobs`, `user_jobs`, `resumes`, `scrape_runs`, `scoring_runs`.
- **Multi-User Data Isolation**: User accounts own their `user_jobs`, `resumes`, and `scoring_runs` through foreign keys referencing `users.id` with `ON DELETE CASCADE`.
- **Global Shared Listings (`jobs`)**: The `jobs` table stores deduplicated job listings from scrapers, deduplicated globally by canonical `url` (`UNIQUE` constraint). Global jobs contain no user-specific columns.
- **Per-User Application Tracking (`user_jobs`)**: User-specific interaction state (`status`, `notes`, `match_score`, `missing_skills`, `match_summary`, `matched_at`, `resume_uploaded_at`) lives in the `user_jobs` junction table linking `(user_id, job_id)` with a composite unique constraint.
- **Single Active Resume Per User**: The `resumes` table stores candidate resumes scoped strictly per user (`user_id` foreign key). Each user has their own active resume.
- **User-Scoped Scoring Runs**: The `scoring_runs` table tracks persistent background auto-scoring batches scheduled for an authenticated user (`user_id` foreign key).
- **Safe Job Deletion**: When a user deletes a job (`DELETE /jobs/{id}`), only their `user_jobs` record is removed. The global `Job` listing is never deleted and remains accessible to other users.
- **String Constants over DB Enums**: Enum-like fields (`status`, `source`, `scoring_runs.status`) are stored as `VARCHAR` rather than PostgreSQL native enum types, preventing database locks during schema updates. Pydantic schemas enforce runtime validation.

---

## 2. Table Specifications

### 2.1 Table: `jobs`

Stores collected global job listings and lifecycle expiration fields.

| Column | Data Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | UUID | No | `gen_random_uuid()` | Primary Key |
| `title` | `VARCHAR(500)` | No | - | Job title from source |
| `company` | `VARCHAR(500)` | No | - | Company name |
| `company_url` | `TEXT` | Yes | `NULL` | Company website URL |
| `description` | `TEXT` | No | - | Full job listing text |
| `url` | `TEXT` | No | - | Canonical source URL (UNIQUE constraint, dedup key) |
| `source` | `VARCHAR(50)` | No | - | Scraper source (`remoteok`, `yc_jobs`) |
| `location` | `VARCHAR(200)` | Yes | `NULL` | Location string |
| `posted_at` | `TIMESTAMPTZ` | Yes | `NULL` | Original listing post date from source |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | Record insertion timestamp |
| `updated_at` | `TIMESTAMPTZ` | No | `now()` | Record update timestamp |
| `last_seen_at` | `TIMESTAMPTZ` | Yes | `NULL` | Timestamp when job URL was last seen during scraper sync |
| `missing_sync_count` | `INTEGER` | No | `0` | Consecutive scraper syncs where job URL was missing |
| `expired_at` | `TIMESTAMPTZ` | Yes | `NULL` | Expiration timestamp (set when `missing_sync_count >= 2`) |

**Indexes & Constraints on `jobs`:**
- `idx_jobs_source` ON `jobs(source)`
- `idx_jobs_expired_at` ON `jobs(expired_at)`
- UNIQUE constraint on `url`

---

### 2.2 Table: `user_jobs`

Stores per-user application pipeline tracking, notes, and AI match results.

| Column | Data Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | UUID | No | `gen_random_uuid()` | Primary Key |
| `user_id` | UUID | No | - | Foreign Key (`users.id`, ON DELETE CASCADE) |
| `job_id` | UUID | No | - | Foreign Key (`jobs.id`, ON DELETE CASCADE) |
| `status` | `VARCHAR(20)` | No | `'saved'` | Pipeline status (`saved`, `applied`, `interview`, `offer`, `rejected`) |
| `notes` | `TEXT` | Yes | `NULL` | Candidate notes |
| `match_score` | `INTEGER` | Yes | `NULL` | Gemini fit score (0–100) for this user |
| `missing_skills` | `JSONB` | Yes | `NULL` | JSON array of missing skill strings |
| `match_summary` | `TEXT` | Yes | `NULL` | Two-sentence fit summary |
| `matched_at` | `TIMESTAMPTZ` | Yes | `NULL` | Timestamp when score was computed |
| `resume_uploaded_at` | `TIMESTAMPTZ` | Yes | `NULL` | Timestamp of user's resume used during scoring |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | Record creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | No | `now()` | Record update timestamp |

**Indexes & Constraints on `user_jobs`:**
- UNIQUE constraint `uq_user_jobs_user_id_job_id` ON `user_jobs(user_id, job_id)`
- `idx_user_jobs_user_id` ON `user_jobs(user_id)`
- `idx_user_jobs_job_id` ON `user_jobs(job_id)`
- `idx_user_jobs_user_score` ON `user_jobs(user_id, match_score)`
- `idx_user_jobs_user_status` ON `user_jobs(user_id, status)`

---

### 2.3 Table: `resumes`

Stores candidate PDF text and AI-extracted skills for a user's active resume.

| Column | Data Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | UUID | No | `gen_random_uuid()` | Primary Key |
| `user_id` | UUID | No | - | Foreign Key (`users.id`, ON DELETE CASCADE) |
| `filename` | `VARCHAR(255)` | No | - | Original uploaded PDF filename |
| `raw_text` | `TEXT` | No | - | Plain text extracted via PyMuPDF |
| `skills` | `JSONB` | No | `'[]'::jsonb` | JSON array of normalized technical skills |
| `uploaded_at` | `TIMESTAMPTZ` | No | `now()` | Upload timestamp |

**Indexes & Constraints on `resumes`:**
- `idx_resumes_user_uploaded` ON `resumes(user_id, uploaded_at)`

---

### 2.4 Table: `scrape_runs`

Append-only execution log for scraper runs per source.

| Column | Data Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | UUID | No | `gen_random_uuid()` | Primary Key |
| `source` | `VARCHAR(50)` | No | - | Scraper source identifier (`remoteok`, `yc_jobs`) |
| `jobs_found` | `INTEGER` | No | `0` | Raw jobs retrieved from source |
| `jobs_new` | `INTEGER` | No | `0` | Newly inserted jobs after deduplication |
| `error` | `TEXT` | Yes | `NULL` | Error log message if scraper failed |
| `started_at` | `TIMESTAMPTZ` | No | - | Scrape start timestamp |
| `completed_at` | `TIMESTAMPTZ` | Yes | `NULL` | Scrape completion timestamp |

**Indexes on `scrape_runs`:**
- `idx_scrape_runs_source_started` ON `scrape_runs(source, started_at)`

---

### 2.5 Table: `scoring_runs`

Tracks persistent background auto-scoring batches scheduled after job ingestion for a specific user.

| Column | Data Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | UUID | No | `gen_random_uuid()` | Primary Key |
| `user_id` | UUID | No | - | Foreign Key (`users.id`, ON DELETE CASCADE) |
| `status` | `VARCHAR(20)` | No | `'running'` | Batch status (`running`, `completed`) |
| `total_jobs` | `INTEGER` | No | - | Total jobs scheduled for scoring in batch |
| `scored_jobs` | `INTEGER` | No | `0` | Count of jobs successfully scored |
| `failed_jobs` | `INTEGER` | No | `0` | Count of jobs that failed scoring permanently |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | Batch creation timestamp |
| `completed_at` | `TIMESTAMPTZ` | Yes | `NULL` | Timestamp when status flipped to `'completed'` |

**Indexes on `scoring_runs`:**
- `idx_scoring_runs_user_created` ON `scoring_runs(user_id, created_at)`
- `idx_scoring_runs_status` ON `scoring_runs(status)`

---

### 2.6 Table: `users`

Stores user identity, profile details, and authentication credentials (email/password and Google OAuth).

| Column | Data Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | UUID | No | `gen_random_uuid()` | Primary Key |
| `email` | `VARCHAR(255)` | No | - | User email address (UNIQUE constraint, normalized) |
| `name` | `VARCHAR(255)` | No | - | User display name |
| `password_hash` | `VARCHAR(255)` | Yes | `NULL` | Encoded Argon2id password hash (nullable for OAuth-only) |
| `google_id` | `VARCHAR(255)` | Yes | `NULL` | Google Subject ID for OAuth login |
| `avatar_url` | `VARCHAR(1024)` | Yes | `NULL` | User profile picture URL |
| `is_active` | `BOOLEAN` | No | `true` | User account active flag |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | Registration timestamp |
| `updated_at` | `TIMESTAMPTZ` | No | `now()` | Account update timestamp |

**Indexes on `users`:**
- `idx_users_email` ON `users(email)`
- `idx_users_google_id` ON `users(google_id)`
- UNIQUE constraint on `email`
- UNIQUE constraint on `google_id`

---

## 3. Migration History

All migrations are located in `backend/alembic/versions/`:

1. **`cc9c2e74a08d_initial_schema.py`** (Revision `cc9c2e74a08d`)
   - Created initial `jobs`, `resumes`, and `scrape_runs` tables.
2. **`63d3ec745a23_add_job_lifecycle_fields.py`** (Revision `63d3ec745a23`)
   - Added `last_seen_at`, `missing_sync_count`, and `expired_at` columns to `jobs`.
3. **`68abbd5b8e5a_add_scoring_runs_table.py`** (Revision `68abbd5b8e5a`)
   - Created `scoring_runs` table and `idx_scoring_runs_status` index.
4. **`7a1b2c3d4e5f_add_users_table.py`** (Revision `7a1b2c3d4e5f`)
   - Created `users` table and `idx_users_email` index.
5. **`8c3d4e5f6a7b_add_google_oauth_to_users.py`** (Revision `8c3d4e5f6a7b`)
   - Added `google_id` and `avatar_url` columns to `users` with unique index.
6. **`9d4e5f6a7b8c_multi_user_data_isolation.py`** (Revision `9d4e5f6a7b8c`)
   - Created `user_jobs` junction table with foreign keys to `users` and `jobs`.
   - Added `user_id` foreign keys to `resumes` and `scoring_runs`.
   - Relocated user-specific fields from `jobs` to `user_jobs`.
   - Safe deterministic backfill of existing single-user data and reversible downgrade.