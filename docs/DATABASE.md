# Database Specification

**Engine:** PostgreSQL 16  
**ORM:** SQLAlchemy 2.x (Mapped Types)  
**Migration Tool:** Alembic  

---

## 1. Overview & Architectural Design Decisions

- **Five Core Tables**: `jobs`, `resumes`, `scrape_runs`, `scoring_runs`, `users`.
- **No Foreign Key Constraints**: No junction tables or foreign keys exist between tables. In Phase 1 Authentication Foundation, `users` table is introduced for user identity and credentials without modifying ownership of existing tables.
- **Single Active Resume Model**: The `resumes` table stores at most one active resume row. A new PDF upload replaces the existing row.
- **Application Tracking on `Job`**: Application pipeline state (`status`) and user notes (`notes`) live directly on the `Job` record.
- **String Constants over DB Enums**: Enum-like fields (`status`, `source`, `scoring_runs.status`) are stored as `VARCHAR` rather than PostgreSQL native enum types, preventing database locks during schema updates. Pydantic schemas enforce runtime validation.

---

## 2. Table Specifications

### 2.1 Table: `jobs`

Stores collected job listings, match scores, application status, and lifecycle expiration fields.

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
| `status` | `VARCHAR(20)` | No | `'saved'` | Application status (`saved`, `applied`, `interview`, `offer`, `rejected`) |
| `notes` | `TEXT` | Yes | `NULL` | Free-text candidate notes |
| `match_score` | `INTEGER` | Yes | `NULL` | Gemini fit score (0–100) |
| `missing_skills` | `JSONB` | Yes | `NULL` | JSON array of missing skill strings |
| `match_summary` | `TEXT` | Yes | `NULL` | Two-sentence fit summary |
| `matched_at` | `TIMESTAMPTZ` | Yes | `NULL` | Timestamp when Gemini match score was generated |
| `resume_uploaded_at` | `TIMESTAMPTZ` | Yes | `NULL` | Timestamp of resume version used during scoring |
| `posted_at` | `TIMESTAMPTZ` | Yes | `NULL` | Original listing post date from source |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | Record insertion timestamp |
| `updated_at` | `TIMESTAMPTZ` | No | `now()` | Record update timestamp |
| `last_seen_at` | `TIMESTAMPTZ` | Yes | `NULL` | Timestamp when job URL was last seen during scraper sync |
| `missing_sync_count` | `INTEGER` | No | `0` | Consecutive scraper syncs where job URL was missing |
| `expired_at` | `TIMESTAMPTZ` | Yes | `NULL` | Expiration timestamp (set when `missing_sync_count >= 2`) |

**Indexes on `jobs`:**
- `idx_jobs_status` ON `jobs(status)`
- `idx_jobs_source` ON `jobs(source)`
- `idx_jobs_score` ON `jobs(match_score)`
- `idx_jobs_expired_at` ON `jobs(expired_at)`
- UNIQUE constraint on `url`

---

### 2.2 Table: `resumes`

Stores candidate PDF text and AI-extracted skills for the single active resume.

| Column | Data Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | UUID | No | `gen_random_uuid()` | Primary Key |
| `filename` | `VARCHAR(255)` | No | - | Original uploaded PDF filename |
| `raw_text` | `TEXT` | No | - | Plain text extracted via PyMuPDF |
| `skills` | `JSONB` | No | `'[]'::jsonb` | JSON array of normalized technical skills |
| `uploaded_at` | `TIMESTAMPTZ` | No | `now()` | Upload timestamp |

---

### 2.3 Table: `scrape_runs`

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

### 2.4 Table: `scoring_runs`

Tracks persistent background auto-scoring batches scheduled after job ingestion.

| Column | Data Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | UUID | No | `gen_random_uuid()` | Primary Key |
| `status` | `VARCHAR(20)` | No | `'running'` | Batch status (`running`, `completed`) |
| `total_jobs` | `INTEGER` | No | - | Total jobs scheduled for scoring in batch |
| `scored_jobs` | `INTEGER` | No | `0` | Count of jobs successfully scored |
| `failed_jobs` | `INTEGER` | No | `0` | Count of jobs that failed scoring permanently |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | Batch creation timestamp |
| `completed_at` | `TIMESTAMPTZ` | Yes | `NULL` | Timestamp when status flipped to `'completed'` |

**Indexes on `scoring_runs`:**
- `idx_scoring_runs_status` ON `scoring_runs(status)`

---

### 2.5 Table: `users`

Stores user identity, profile details, and Argon2id password hashes for Phase 1 Authentication Foundation.

| Column | Data Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | UUID | No | `gen_random_uuid()` | Primary Key |
| `email` | `VARCHAR(255)` | No | - | User email address (UNIQUE constraint, normalized) |
| `name` | `VARCHAR(255)` | No | - | User display name |
| `password_hash` | `VARCHAR(255)` | No | - | Encoded Argon2id password hash |
| `is_active` | `BOOLEAN` | No | `true` | User account active flag |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | Registration timestamp |
| `updated_at` | `TIMESTAMPTZ` | No | `now()` | Account update timestamp |

**Indexes on `users`:**
- `idx_users_email` ON `users(email)`
- UNIQUE constraint on `email`

---

## 3. Migration History

All migrations are located in `backend/alembic/versions/`:

1. **`cc9c2e74a08d_initial_schema.py`** (Revision `cc9c2e74a08d`)
   - Created `jobs`, `resumes`, and `scrape_runs` tables with initial indexes.
2. **`63d3ec745a23_add_job_lifecycle_fields.py`** (Revision `63d3ec745a23`)
   - Added `last_seen_at`, `missing_sync_count`, and `expired_at` columns to `jobs`.
   - Created `idx_jobs_expired_at` index.
3. **`68abbd5b8e5a_add_scoring_runs_table.py`** (Revision `68abbd5b8e5a`)
   - Created `scoring_runs` table and `idx_scoring_runs_status` index.
4. **`7a1b2c3d4e5f_add_users_table.py`** (Revision `7a1b2c3d4e5f`)
   - Created `users` table and `idx_users_email` index.