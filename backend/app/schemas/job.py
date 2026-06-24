"""
Pydantic schemas for jobs and scrape runs.

Naming convention:
  - *Request  : inbound payload (router ← client)
  - *Response : outbound payload (router → client)
  - *Internal : used only between service and router, never serialised to JSON

Three categories of schema:
  1. Job schemas      — list item, full detail, update request, score result
  2. Scrape schemas   — run result and status
  3. API envelope     — consistent { data, error } wrapper used on every response

Relationship to models:
  - Schemas never import from models directly (avoids circular imports).
  - Services convert ORM model instances to schemas using model_validate().
  - All schemas use model_config = ConfigDict(from_attributes=True) so
    Pydantic can read values from SQLAlchemy model instances directly.
"""

import uuid
from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.job import JOB_SOURCE_VALUES, JOB_STATUS_VALUES

# ---------------------------------------------------------------------------
# Generic API envelope
# ---------------------------------------------------------------------------

DataT = TypeVar("DataT")


class ApiResponse(BaseModel, Generic[DataT]):
    """
    Standard response envelope for all endpoints.

    Success:  { "data": <payload>, "error": null }
    Failure:  { "data": null, "error": { "code": "...", "message": "..." } }

    Usage in a router:
        return ApiResponse(data=some_schema_instance)
    """

    data: DataT | None = None
    error: "ApiError | None" = None


class ApiError(BaseModel):
    """Error detail embedded in ApiResponse on failure."""

    code: str = Field(..., description="Machine-readable error code, e.g. NOT_FOUND")
    message: str = Field(..., description="Human-readable description of the error")


# Rebuild ApiResponse after ApiError is defined to resolve forward reference
ApiResponse.model_rebuild()


# ---------------------------------------------------------------------------
# Job status and source literals
# ---------------------------------------------------------------------------

# Reuse the canonical values from the model — single source of truth.
JobStatus = str   # "saved" | "applied" | "interview" | "offer" | "rejected"
JobSource = str   # "remoteok" | "yc_jobs"


# ---------------------------------------------------------------------------
# Job — list item
# Returned by GET /api/jobs.
# Intentionally omits heavy fields: description, notes, match_summary.
# ---------------------------------------------------------------------------

class JobListItem(BaseModel):
    """
    Compact job representation for the job list view.

    Omits description, notes, and match_summary — these are only needed
    on the detail page. Keeping the list payload small improves
    perceived performance when displaying 50+ jobs.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    company: str
    company_url: str | None
    url: str
    source: str
    location: str | None

    # Tracking
    status: str
    match_score: int | None

    # Stale-score flag — computed by service, not stored as a column
    needs_rescore: bool = False

    posted_at: datetime | None
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Job — full detail
# Returned by GET /api/jobs/{id} and POST /api/jobs/{id}/score.
# ---------------------------------------------------------------------------

class JobResponse(BaseModel):
    """
    Complete job record including description, notes, and match analysis.

    Returned by the job detail endpoint and after scoring.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    company: str
    company_url: str | None
    description: str
    url: str
    source: str
    location: str | None

    # Tracking
    status: str
    notes: str | None

    # Match results (null until scored)
    match_score: int | None
    missing_skills: list[Any] | None
    match_summary: str | None
    matched_at: datetime | None
    resume_uploaded_at: datetime | None

    # Stale-score flag — computed by service
    needs_rescore: bool = False

    posted_at: datetime | None
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Job — update request
# Accepted by PATCH /api/jobs/{id}.
# Only status and notes are mutable by the user.
# ---------------------------------------------------------------------------

class JobUpdateRequest(BaseModel):
    """
    Mutable fields on a job record.

    Both fields are optional — send only what you're changing.
    Sending an empty body {} is valid (no-op update).
    """

    status: str | None = Field(
        default=None,
        description=f"Application status. Must be one of: {JOB_STATUS_VALUES}",
    )
    notes: str | None = Field(
        default=None,
        description="Free-text notes. Set to empty string to clear.",
    )

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if v not in JOB_STATUS_VALUES:
            raise ValueError(
                f"Invalid status '{v}'. Must be one of: {', '.join(JOB_STATUS_VALUES)}"
            )
        return v


class JobUpdateResponse(BaseModel):
    """Minimal response returned after a successful PATCH /api/jobs/{id}."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: str
    notes: str | None


# ---------------------------------------------------------------------------
# Job — internal upsert data
# Used by scrapers to pass normalised job data to job_service.upsert_jobs().
# Never serialised to JSON — internal contract between scraper and service.
# ---------------------------------------------------------------------------

class JobUpsertData(BaseModel):
    """
    Normalised job data produced by a scraper and consumed by job_service.

    All fields a scraper can provide. The service maps this to the Job ORM
    model. Required fields must be populated by every scraper — optional
    fields are source-dependent.
    """

    title: str = Field(..., max_length=500)
    company: str = Field(..., max_length=500)
    company_url: str | None = None
    description: str
    url: str = Field(..., description="Canonical URL — used as dedup key")
    source: str = Field(..., description=f"Must be one of: {JOB_SOURCE_VALUES}")
    location: str | None = Field(default=None, max_length=200)
    posted_at: datetime | None = None

    @field_validator("source")
    @classmethod
    def validate_source(cls, v: str) -> str:
        if v not in JOB_SOURCE_VALUES:
            raise ValueError(
                f"Invalid source '{v}'. Must be one of: {', '.join(JOB_SOURCE_VALUES)}"
            )
        return v


# ---------------------------------------------------------------------------
# Paginated job list
# Returned by GET /api/jobs.
# ---------------------------------------------------------------------------

class PaginatedJobList(BaseModel):
    """Paginated wrapper for the job list endpoint."""

    jobs: list[JobListItem]
    total: int = Field(..., description="Total matching jobs (before pagination)")
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1, le=100)


# ---------------------------------------------------------------------------
# Scrape run schemas
# ---------------------------------------------------------------------------

class ScrapeRunResponse(BaseModel):
    """
    Result of a single scraper execution against one source.

    One of these is produced per source per POST /api/scraper/run call.
    Also returned by GET /api/scraper/status (one per source).
    """

    model_config = ConfigDict(from_attributes=True)

    source: str
    jobs_found: int
    jobs_new: int
    error: str | None
    started_at: datetime
    completed_at: datetime | None


class ScraperRunSummary(BaseModel):
    """
    Aggregate result of POST /api/scraper/run.

    Contains one ScrapeRunResponse per source, plus a total_new count.
    """

    runs: list[ScrapeRunResponse]
    total_new: int = Field(..., description="Sum of jobs_new across all sources")




class ScoreResponse(BaseModel):
    """Response shape for POST /api/jobs/{id}/score."""
 
    match_score: int
    missing_skills: list[str]
    match_summary: str
    matched_at: datetime
    cached: bool
    needs_rescore: bool
 
    model_config = {"from_attributes": True}