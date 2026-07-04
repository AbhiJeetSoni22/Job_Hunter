# Database

**Engine:** PostgreSQL 16
**ORM:** SQLAlchemy 2.x (mapped classes)
**Migrations:** Alembic

---

## Design Decisions

**Match data lives on `jobs`, not a separate table.** Single resume, single user — a join table adds complexity with zero benefit. Extract to a `matches` table only if resume versioning is added later.

**`status` and `notes` live on `jobs`.** An `applications` table is the right abstraction for multi-user systems. For personal use, the job record *is* the application record.

**Three tables total.** `jobs`, `resumes`, `scrape_runs`. No junction tables, no soft-delete columns, no audit trail — all out of MVP scope.

---

## Enums

### JobStatus

Stored as plain `VARCHAR(20)` — **not** a PostgreSQL enum type. This is a deliberate choice: adding a new status value later is a simple deploy, not a migration that locks the table. Validation happens at the Pydantic schema layer instead.

Allowed values:

* saved
* applied
* interview
* offer
* rejected

Default:

```text
saved
```

---

## Tables

### `jobs`

Stores every collected job listing, plus match results and application tracking state.

| Column               | Type           | Constraints                   | Description                          |
| -------------------- | -------------- | ----------------------------- | ------------------------------------ |
| `id`                 | UUID           | PK, default gen_random_uuid() | Primary key                          |
| `title`              | VARCHAR(500)   | NOT NULL                      | Job title                            |
| `company`            | VARCHAR(500)   | NOT NULL                      | Company name                         |
| `company_url`        | TEXT           | NULLABLE                      | Company website URL                  |
| `description`        | TEXT           | NOT NULL                      | Full job description                 |
| `url`                | TEXT           | NOT NULL, UNIQUE              | Source URL — dedup key               |
| `source`             | VARCHAR(50)    | NOT NULL                      | `remoteok` or `yc_jobs` — validated against `JOB_SOURCE_VALUES` in `models/job.py`, not a DB-level constraint |
| `location`           | VARCHAR(200)   | NULLABLE                      | Location string from source          |
| `status`             | VARCHAR(20)    | NOT NULL, default `saved`     | Application tracking status (see JobStatus values below) |
| `notes`              | TEXT           | NULLABLE                      | Free-text user notes                 |
| `match_score`        | INTEGER        | NULLABLE                      | 0–100, null until scored             |
| `missing_skills`     | JSONB          | NULLABLE                      | Array of skill strings               |
| `match_summary`      | TEXT           | NULLABLE                      | 2-sentence Gemini summary            |
| `matched_at`         | TIMESTAMPTZ    | NULLABLE                      | When scoring last ran                |
| `resume_uploaded_at` | TIMESTAMPTZ    | NULLABLE                      | Resume timestamp used during scoring |
| `posted_at`          | TIMESTAMPTZ    | NULLABLE                      | Original posting date from source    |
| `created_at`         | TIMESTAMPTZ    | NOT NULL, default now()       | When we ingested this job            |
| `updated_at`         | TIMESTAMPTZ    | NOT NULL, default now()       | Last update timestamp                |

---

### Why `resume_uploaded_at`?

Example:

```text
Resume A
↓
Job Score = 78

Upload Resume B
↓
Old score becomes stale
```

If:

```text
resume_uploaded_at > matched_at
```

then the UI can show:

```text
Needs Re-score
```

without automatically recalculating every job.

---

### Indexes

```sql
CREATE INDEX idx_jobs_status
ON jobs(status);

CREATE INDEX idx_jobs_source
ON jobs(source);

CREATE INDEX idx_jobs_score
ON jobs(match_score DESC NULLS LAST);

CREATE UNIQUE INDEX idx_jobs_url
ON jobs(url);
```

---

### `resumes`

Holds the single active resume.

Row is replaced on every upload — only one row is expected to exist at any time.

| Column        | Type         | Constraints                   | Description                        |
| ------------- | ------------ | ----------------------------- | ---------------------------------- |
| `id`          | UUID         | PK, default gen_random_uuid() | Primary key                        |
| `filename`    | VARCHAR(255) | NOT NULL                      | Original uploaded filename         |
| `raw_text`    | TEXT         | NOT NULL                      | Full extracted text from PDF       |
| `skills`      | JSONB        | NOT NULL                      | Array of skill strings from Gemini |
| `uploaded_at` | TIMESTAMPTZ  | NOT NULL, default now()       | Upload timestamp                   |

No foreign keys — resume is standalone. Job scoring reads from the active resume at call time; result is stored on the job, so there's no live dependency after scoring runs.

---

### `scrape_runs`

Log of every sync attempt.

Gives visibility into what ran, when, and whether it succeeded.

| Column         | Type        | Constraints                   | Description                                    |
| -------------- | ----------- | ----------------------------- | ---------------------------------------------- |
| `id`           | UUID        | PK, default gen_random_uuid() | Primary key                                    |
| `source`       | VARCHAR(50) | NOT NULL                      | `remoteok` or `yc_jobs`                        |
| `jobs_found`   | INTEGER     | NOT NULL, default 0           | Total jobs returned by source                  |
| `jobs_new`     | INTEGER     | NOT NULL, default 0           | Jobs actually inserted (deduped)               |
| `error`        | TEXT        | NULLABLE                      | Error message if run failed, else null         |
| `started_at`   | TIMESTAMPTZ | NOT NULL                      | When scrape began                              |
| `completed_at` | TIMESTAMPTZ | NULLABLE                      | When scrape finished (null if errored mid-run) |

---

### Index

```sql
CREATE INDEX idx_scrape_runs_source_started
ON scrape_runs(source, started_at DESC);
```

---

## Migration Workflow

```bash
# Create new migration
alembic revision --autogenerate -m "describe the change"

# Apply all pending migrations
alembic upgrade head

# Roll back one step
alembic downgrade -1

# Show current state
alembic current
```

Migrations live in:

```text
backend/alembic/versions/
```

Never edit a migration that has already been executed.

Always create a new migration for schema changes.