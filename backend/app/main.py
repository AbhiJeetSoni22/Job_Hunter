"""
main.py

FastAPI application factory.
Registers all routers and configures global exception handlers.
All error responses conform to ApiResponse envelope per api_spec.md.
"""

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import get_settings
from app.routers import dashboard, health, jobs, resume, resume_analysis, scraper,interview_prep



# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

app = FastAPI(
    title="AI Internship Hunter",
    description="Automate internship discovery, AI-powered scoring, and application tracking.",
    version="0.1.0",
)


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Global exception handlers
# ---------------------------------------------------------------------------

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Reformat all HTTPException responses into the ApiResponse envelope:
        {"data": null, "error": {"code": "...", "message": "..."}}

    exc.detail may be:
        - a dict with "code" and "message" keys  (our raise style)
        - a plain string                          (FastAPI built-ins, e.g. 404 from path params)
    """
    detail = exc.detail

    if isinstance(detail, dict) and "code" in detail and "message" in detail:
        code = detail["code"]
        message = detail["message"]
    else:
        # FastAPI built-in errors (e.g. validation, path not found)
        code = _status_to_code(exc.status_code)
        message = str(detail)

    return JSONResponse(
        status_code=exc.status_code,
        content={"data": None, "error": {"code": code, "message": message}},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Reformat Pydantic/FastAPI request validation errors into ApiResponse envelope.
    Preserves HTTP 422. Concatenates all field errors into a single message string.

    Example input error:
        [{"loc": ["body", "status"], "msg": "field required", "type": "missing"}]

    Example output:
        {"data": null, "error": {"code": "VALIDATION_ERROR", "message": "status: field required"}}
    """
    messages = []
    for error in exc.errors():
        loc = " → ".join(str(part) for part in error["loc"] if part != "body")
        messages.append(f"{loc}: {error['msg']}" if loc else error["msg"])

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "data": None,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "; ".join(messages),
            },
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unhandled exceptions. Never leaks stack traces."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "data": None,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred.",
            },
        },
    )


def _status_to_code(status_code: int) -> str:
    """Map HTTP status codes to API error code strings for built-in FastAPI errors."""
    mapping = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        422: "UNPROCESSABLE_ENTITY",
        429: "TOO_MANY_REQUESTS",
        500: "INTERNAL_ERROR",
        501: "NOT_IMPLEMENTED",
        502: "BAD_GATEWAY",
        503: "SERVICE_UNAVAILABLE",
    }
    return mapping.get(status_code, "ERROR")


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(health.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")
app.include_router(scraper.router, prefix="/api")
app.include_router(resume.router, prefix="/api")
app.include_router(resume_analysis.router, prefix="/api")
app.include_router(interview_prep.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")