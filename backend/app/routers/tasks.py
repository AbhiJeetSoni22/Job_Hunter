"""
Tasks router for inspecting and managing background queue jobs.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Query, status

from app.dependencies import CurrentUser, DbSession
from app.schemas.job import ApiResponse
from app.schemas.task import TaskResponse
from app.services.task_queue_service import (
    InvalidTaskTransitionError,
    TaskNotFoundError,
    TaskQueueService,
)

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _not_found(task_id: uuid.UUID) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": "NOT_FOUND", "message": f"Task {task_id} not found"},
    )


@router.get(
    "/{task_id}",
    response_model=ApiResponse[TaskResponse],
    summary="Get background task status",
    description="Fetch current execution status, progress, and result of a background task for the authenticated user.",
)
def get_task(
    task_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
) -> ApiResponse[TaskResponse]:
    service = TaskQueueService(db, user_id=user.id)
    task = service.get_task(task_id, user_id=user.id)
    if task is None:
        raise _not_found(task_id)

    return ApiResponse(data=TaskResponse.model_validate(task))


@router.get(
    "",
    response_model=ApiResponse[list[TaskResponse]],
    summary="List background tasks",
    description="List recent background tasks owned by the authenticated user.",
)
def list_tasks(
    user: CurrentUser,
    db: DbSession,
    task_type: str | None = Query(default=None, description="Optional filter by task_type"),
    status_filter: str | None = Query(default=None, alias="status", description="Optional filter by status"),
    limit: int = Query(default=20, ge=1, le=100),
) -> ApiResponse[list[TaskResponse]]:
    service = TaskQueueService(db, user_id=user.id)
    tasks = service.list_tasks(
        user_id=user.id,
        task_type=task_type,
        status=status_filter,
        limit=limit,
    )
    return ApiResponse(data=[TaskResponse.model_validate(t) for t in tasks])


@router.post(
    "/{task_id}/cancel",
    response_model=ApiResponse[TaskResponse],
    summary="Cancel a queued background task",
    description="Cancel a task before it starts running. Returns 422 if task has already started or completed.",
)
def cancel_task(
    task_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
) -> ApiResponse[TaskResponse]:
    service = TaskQueueService(db, user_id=user.id)
    try:
        task = service.cancel_task(task_id, user_id=user.id)
        return ApiResponse(data=TaskResponse.model_validate(task))
    except TaskNotFoundError as exc:
        raise _not_found(task_id) from exc
    except InvalidTaskTransitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "INVALID_TRANSITION", "message": str(exc)},
        ) from exc

