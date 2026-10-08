"""
Rate limiting and execution cooldown service.

Provides PostgreSQL-backed abuse protection for:
  1. AI operations: enforces AI_RATE_LIMIT_PER_MINUTE scoped to CurrentUser.
  2. Scraper operations: enforces SCRAPER_COOLDOWN_SECONDS and concurrency locking per CurrentUser.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.rate_limit import RateLimitEvent

logger = logging.getLogger(__name__)


class RateLimitService:
    """Service managing per-user rate limits and execution cooldowns."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def check_ai_rate_limit(
        self,
        user_id: uuid.UUID,
        custom_now: datetime | None = None,
    ) -> None:
        """
        Enforce per-user rate limit for expensive AI operations.

        Uses PostgreSQL transaction-scoped advisory locking (pg_advisory_xact_lock)
        scoped deterministically to the user_id to eliminate race conditions where
        concurrent requests could read the same count and bypass AI_RATE_LIMIT_PER_MINUTE.

        Counts 'ai_operation' events recorded for this user within the last 60 seconds.
        If the count reaches or exceeds AI_RATE_LIMIT_PER_MINUTE, raises HTTP 429.
        Otherwise, records the event in the database.
        """
        settings = get_settings()
        limit = settings.AI_RATE_LIMIT_PER_MINUTE
        now = custom_now or datetime.now(UTC)
        window_start = now - timedelta(seconds=60)

        is_pg = (
            self._db.bind is not None
            and getattr(self._db.bind.dialect, "name", "") == "postgresql"
        )

        # 1. Transaction-level advisory lock serializes concurrent rate-limit checks
        # for this specific user. Automatically released on COMMIT or ROLLBACK.
        if is_pg:
            self._db.execute(
                text("SELECT pg_advisory_xact_lock(hashtext(:lock_key))"),
                {"lock_key": f"ai_rate_limit:{user_id}"},
            )

        try:
            # 2. Count events in the 1-minute window
            stmt = (
                select(func.count(RateLimitEvent.id))
                .where(
                    RateLimitEvent.user_id == user_id,
                    RateLimitEvent.event_type == "ai_operation",
                    RateLimitEvent.created_at >= window_start,
                )
            )
            count = self._db.execute(stmt).scalar() or 0

            if count >= limit:
                logger.warning(
                    "RateLimitService: AI rate limit exceeded for user %s (%d/%d in last 60s)",
                    user_id,
                    count,
                    limit,
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "code": "AI_RATE_LIMIT_EXCEEDED",
                        "message": (
                            f"AI rate limit of {limit} requests per minute exceeded. "
                            "Please wait before making more requests."
                        ),
                    },
                )

            # 3. Record event and commit atomically within the advisory lock
            event = RateLimitEvent(
                id=uuid.uuid4(),
                user_id=user_id,
                event_type="ai_operation",
                status="completed",
                created_at=now,
                completed_at=now,
            )
            self._db.add(event)
            self._db.commit()
        except HTTPException:
            raise
        except Exception:
            if is_pg:
                self._db.rollback()
            raise

    @contextmanager
    def scraper_run_guard(
        self,
        user_id: uuid.UUID,
        custom_now: datetime | None = None,
    ) -> Generator[RateLimitEvent, None, None]:
        """
        Context manager enforcing concurrency serialization and cooldown for scraper runs.

        Raises HTTP 429 SCRAPER_RATE_LIMITED if:
          - A scraper run is currently active for this user.
          - The cooldown period (SCRAPER_COOLDOWN_SECONDS) has not elapsed since the last run.
        """
        settings = get_settings()
        cooldown = settings.SCRAPER_COOLDOWN_SECONDS
        now = custom_now or datetime.now(UTC)

        is_pg = (
            self._db.bind is not None
            and getattr(self._db.bind.dialect, "name", "") == "postgresql"
        )
        lock_acquired = False

        # 1. Concurrency protection via PostgreSQL advisory lock
        if is_pg:
            try:
                res = self._db.execute(
                    text("SELECT pg_try_advisory_lock(hashtext(:lock_key))"),
                    {"lock_key": f"scraper_run:{user_id}"},
                ).scalar()
                lock_acquired = bool(res)
                if not lock_acquired:
                    logger.warning(
                        "RateLimitService: concurrent scraper run rejected via advisory lock for user %s",
                        user_id,
                    )
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail={
                            "code": "SCRAPER_RATE_LIMITED",
                            "message": "A scraper run is already in progress for your account.",
                        },
                    )
            except HTTPException:
                raise
            except Exception as exc:
                logger.debug("Advisory lock check exception: %s", exc)

        # 2. Concurrency check via database records (safety fallback & multi-instance check)
        active_run_stmt = (
            select(RateLimitEvent)
            .where(
                RateLimitEvent.user_id == user_id,
                RateLimitEvent.event_type == "scraper_run",
                RateLimitEvent.status == "in_progress",
                RateLimitEvent.created_at >= (now - timedelta(minutes=15)),
            )
            .limit(1)
        )
        active_run = self._db.execute(active_run_stmt).scalar_one_or_none()
        if active_run is not None:
            if is_pg and lock_acquired:
                self._release_advisory_lock(user_id)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "code": "SCRAPER_RATE_LIMITED",
                    "message": "A scraper run is already in progress for your account.",
                },
            )

        # 3. Cooldown check since last completed run
        if cooldown > 0:
            latest_run_stmt = (
                select(RateLimitEvent)
                .where(
                    RateLimitEvent.user_id == user_id,
                    RateLimitEvent.event_type == "scraper_run",
                    RateLimitEvent.status == "completed",
                )
                .order_by(RateLimitEvent.created_at.desc())
                .limit(1)
            )
            latest_run = self._db.execute(latest_run_stmt).scalar_one_or_none()
            if latest_run is not None:
                ref_time = latest_run.completed_at or latest_run.created_at
                if ref_time.tzinfo is None:
                    ref_time = ref_time.replace(tzinfo=UTC)
                elapsed = (now - ref_time).total_seconds()
                if elapsed < cooldown:
                    remaining = max(1, int(cooldown - elapsed))
                    logger.info(
                        "RateLimitService: scraper cooldown active for user %s (%ds remaining)",
                        user_id,
                        remaining,
                    )
                    if is_pg and lock_acquired:
                        self._release_advisory_lock(user_id)
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail={
                            "code": "SCRAPER_RATE_LIMITED",
                            "message": (
                                f"Scraper cooldown active. Please wait {remaining} "
                                "second(s) before running scrapers again."
                            ),
                        },
                    )

        # 4. Mark run in_progress in DB
        event = RateLimitEvent(
            id=uuid.uuid4(),
            user_id=user_id,
            event_type="scraper_run",
            status="in_progress",
            created_at=now,
        )
        self._db.add(event)
        self._db.commit()
        self._db.refresh(event)

        try:
            yield event
            # Success: mark completed
            event.status = "completed"
            event.completed_at = datetime.now(UTC)
            self._db.commit()
        except Exception:
            event.status = "failed"
            event.completed_at = datetime.now(UTC)
            self._db.commit()
            raise
        finally:
            if is_pg and lock_acquired:
                self._release_advisory_lock(user_id)

    def _release_advisory_lock(self, user_id: uuid.UUID) -> None:
        try:
            self._db.execute(
                text("SELECT pg_advisory_unlock(hashtext(:lock_key))"),
                {"lock_key": f"scraper_run:{user_id}"},
            )
        except Exception as exc:
            logger.debug("Failed to release advisory lock for user %s: %s", user_id, exc)
