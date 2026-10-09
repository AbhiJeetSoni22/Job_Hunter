"""
Pydantic schemas for the task queue.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TaskResponse(BaseModel):
    """Outbound representation of a background task."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    task_type: str
    status: str
    user_id: uuid.UUID | None = None
    attempt_count: int = 0
    max_attempts: int = 3
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result: dict[str, Any] | None = None
    error_message: str | None = None


class EnqueueTaskRequest(BaseModel):
    """Inbound request to enqueue a task."""

    task_type: str = Field(..., description="Type of task: 'scrape', 'scoring', 'bulk_score'")
    payload: dict[str, Any] = Field(default_factory=dict, description="Task execution parameters")
