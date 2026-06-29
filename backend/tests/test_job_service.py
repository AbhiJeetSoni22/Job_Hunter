"""
test_job_service.py

Tests for app.services.job_service.JobService.

Coverage:
  - list_jobs() — filters, pagination, sort, scored flag, needs_rescore
  - get_job()   — hit, not-found
  - update_job()— status, notes, invalid status, not-found
  - delete_job()— hit, not-found
  - upsert_jobs()— new, duplicate skip, mixed batch

All tests require a live PostgreSQL database (JSONB + UUID).
Skip gracefully when TEST_DATABASE_URL is absent.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from tests.conftest import needs_db

pytestmark = needs_db


# ---------------------------------------------------------------------------
# list_jobs
# ---------------------------------------------------------------------------

class TestListJobs:

    def test_returns_paginated_job_list(self, job_service, sample_job):
        result = job_service.list_jobs()
        assert result.total >= 1
        assert len(result.jobs) >= 1
        assert result.page == 1
        assert result.page_size == 20

    def test_filter_by_status(self, job_service, sample_job):
        result = job_service.list_jobs(status="saved")
        assert all(j.status == "saved" for j in result.jobs)

    def test_filter_by_source(self, job_service, sample_job):
        result = job_service.list_jobs(source="remoteok")
        assert all(j.source == "remoteok" for j in result.jobs)

    def test_filter_scored_true(self, job_service, sample_job, scored_job):
        result = job_service.list_jobs(scored=True)
        assert all(j.match_score is not None for j in result.jobs)

    def test_filter_scored_false(self, job_service, sample_job, scored_job):
        result = job_service.list_jobs(scored=False)
        assert all(j.match_score is None for j in result.jobs)

    def test_pagination(self, job_service, sample_job, scored_job):
        result = job_service.list_jobs(page=1, page_size=1)
        assert len(result.jobs) == 1
        assert result.page_size == 1

    def test_sort_by_match_score(self, job_service, sample_job, scored_job):
        result = job_service.list_jobs(sort_by="match_score", order="desc")
        scores = [j.match_score for j in result.jobs if j.match_score is not None]
        assert scores == sorted(scores, reverse=True)

    def test_invalid_sort_by_raises_value_error(self, job_service):
        with pytest.raises(ValueError, match="Invalid sort_by"):
            job_service.list_jobs(sort_by="invalid_col")

    def test_invalid_order_raises_value_error(self, job_service):
        with pytest.raises(ValueError, match="Invalid order"):
            job_service.list_jobs(order="sideways")

    def test_needs_rescore_false_when_no_score(self, job_service, sample_job):
        now = datetime.now(timezone.utc)
        result = job_service.list_jobs(current_resume_uploaded_at=now)
        unscored = [j for j in result.jobs if j.id == sample_job.id]
        assert len(unscored) == 1
        assert unscored[0].needs_rescore is False

    def test_needs_rescore_false_when_score_matches_resume(
        self, job_service, scored_job
    ):
        result = job_service.list_jobs(
            current_resume_uploaded_at=scored_job.resume_uploaded_at
        )
        match = [j for j in result.jobs if j.id == scored_job.id]
        assert len(match) == 1
        assert match[0].needs_rescore is False

    def test_needs_rescore_true_when_resume_changed(self, job_service, scored_job):
        newer_ts = datetime(2099, 1, 1, tzinfo=timezone.utc)
        result = job_service.list_jobs(current_resume_uploaded_at=newer_ts)
        match = [j for j in result.jobs if j.id == scored_job.id]
        assert len(match) == 1
        assert match[0].needs_rescore is True


# ---------------------------------------------------------------------------
# get_job
# ---------------------------------------------------------------------------

class TestGetJob:

    def test_returns_job_response(self, job_service, sample_job):
        from app.schemas.job import JobResponse  # noqa: PLC0415

        result = job_service.get_job(sample_job.id)
        assert isinstance(result, JobResponse)
        assert str(result.id) == str(sample_job.id)
        assert result.title == "Backend Engineer"
        assert result.company == "Acme Corp"

    def test_not_found_raises_lookup_error(self, job_service):
        with pytest.raises(LookupError, match="not found"):
            job_service.get_job(uuid.uuid4())

    def test_needs_rescore_propagated(self, job_service, scored_job):
        newer_ts = datetime(2099, 1, 1, tzinfo=timezone.utc)
        result = job_service.get_job(
            scored_job.id,
            current_resume_uploaded_at=newer_ts,
        )
        assert result.needs_rescore is True

    def test_full_fields_present(self, job_service, scored_job):
        result = job_service.get_job(scored_job.id)
        assert result.match_score == 82
        assert result.missing_skills == ["Rust", "CUDA"]
        assert result.match_summary is not None
        assert result.description is not None


# ---------------------------------------------------------------------------
# update_job
# ---------------------------------------------------------------------------

class TestUpdateJob:

    def test_update_status(self, job_service, sample_job):
        from app.schemas.job import JobUpdateRequest  # noqa: PLC0415

        result = job_service.update_job(
            sample_job.id,
            JobUpdateRequest(status="applied"),
        )
        assert result.status == "applied"

    def test_update_notes(self, job_service, sample_job):
        from app.schemas.job import JobUpdateRequest  # noqa: PLC0415

        result = job_service.update_job(
            sample_job.id,
            JobUpdateRequest(notes="Called recruiter"),
        )
        assert result.notes == "Called recruiter"

    def test_update_both_fields(self, job_service, sample_job):
        from app.schemas.job import JobUpdateRequest  # noqa: PLC0415

        result = job_service.update_job(
            sample_job.id,
            JobUpdateRequest(status="interview", notes="Tech screen scheduled"),
        )
        assert result.status == "interview"
        assert result.notes == "Tech screen scheduled"

    def test_empty_body_is_noop(self, job_service, sample_job):
        from app.schemas.job import JobUpdateRequest  # noqa: PLC0415

        result = job_service.update_job(
            sample_job.id,
            JobUpdateRequest(),
        )
        assert result.status == "saved"  # unchanged default

    def test_invalid_status_raises_value_error(self, job_service, sample_job):
        from app.schemas.job import JobUpdateRequest  # noqa: PLC0415

        with pytest.raises(ValueError, match="Invalid status"):
            job_service.update_job(
                sample_job.id,
                JobUpdateRequest.model_construct(status="ghost"),
            )

    def test_not_found_raises_lookup_error(self, job_service):
        from app.schemas.job import JobUpdateRequest  # noqa: PLC0415

        with pytest.raises(LookupError, match="not found"):
            job_service.update_job(uuid.uuid4(), JobUpdateRequest(status="applied"))

    def test_returns_job_update_response(self, job_service, sample_job):
        from app.schemas.job import JobUpdateRequest, JobUpdateResponse  # noqa: PLC0415

        result = job_service.update_job(
            sample_job.id,
            JobUpdateRequest(status="offer"),
        )
        assert isinstance(result, JobUpdateResponse)
        assert str(result.id) == str(sample_job.id)


# ---------------------------------------------------------------------------
# delete_job
# ---------------------------------------------------------------------------

class TestDeleteJob:

    def test_delete_removes_job(self, job_service, sample_job):
        job_service.delete_job(sample_job.id)
        with pytest.raises(LookupError):
            job_service.get_job(sample_job.id)

    def test_delete_returns_none(self, job_service, sample_job):
        result = job_service.delete_job(sample_job.id)
        assert result is None

    def test_not_found_raises_lookup_error(self, job_service):
        with pytest.raises(LookupError, match="not found"):
            job_service.delete_job(uuid.uuid4())


# ---------------------------------------------------------------------------
# upsert_jobs
# ---------------------------------------------------------------------------

class TestUpsertJobs:

    def test_inserts_new_jobs(self, job_service):
        from app.schemas.job import JobUpsertData  # noqa: PLC0415

        jobs = [
            JobUpsertData(
                title="SWE",
                company="Acme",
                description="Build stuff",
                url="https://upsert-test.example.com/job/1",
                source="remoteok",
            ),
        ]
        count = job_service.upsert_jobs(jobs)
        assert count == 1

    def test_skips_duplicate_url(self, job_service):
        from app.schemas.job import JobUpsertData  # noqa: PLC0415

        data = JobUpsertData(
            title="SWE",
            company="Acme",
            description="Build stuff",
            url="https://upsert-dedup.example.com/job/1",
            source="remoteok",
        )
        first = job_service.upsert_jobs([data])
        second = job_service.upsert_jobs([data])
        assert first == 1
        assert second == 0

    def test_mixed_batch(self, job_service):
        from app.schemas.job import JobUpsertData  # noqa: PLC0415

        url_existing = "https://upsert-mixed.example.com/existing"
        existing = JobUpsertData(
            title="Existing",
            company="Co",
            description="desc",
            url=url_existing,
            source="remoteok",
        )
        job_service.upsert_jobs([existing])

        new_job = JobUpsertData(
            title="New",
            company="Co",
            description="desc",
            url="https://upsert-mixed.example.com/new",
            source="remoteok",
        )
        count = job_service.upsert_jobs([existing, new_job])
        assert count == 1

    def test_empty_list_returns_zero(self, job_service):
        count = job_service.upsert_jobs([])
        assert count == 0

    def test_upserted_job_has_saved_status(self, job_service, db):
        from app.models.job import Job  # noqa: PLC0415
        from app.schemas.job import JobUpsertData  # noqa: PLC0415
        from sqlalchemy import select  # noqa: PLC0415

        url = "https://upsert-status.example.com/job/1"
        job_service.upsert_jobs([
            JobUpsertData(
                title="X",
                company="Y",
                description="desc",
                url=url,
                source="yc_jobs",
            )
        ])
        row = db.scalar(select(Job).where(Job.url == url))
        assert row is not None
        assert row.status == "saved"