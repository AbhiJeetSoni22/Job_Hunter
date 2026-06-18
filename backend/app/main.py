"""
FastAPI application factory.

Responsibilities:
  - Create and configure the FastAPI app instance
  - Register middleware (CORS)
  - Register all routers under /api prefix
  - Add global exception handlers

Pattern: import create_app() in tests to get a clean instance.
In production, uvicorn imports the `app` object at module level.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.routers import health

settings = get_settings()


# ── Lifespan ───────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan handler.

    Startup: log configuration, verify DB connection.
    Shutdown: cleanup (none needed at this scale).
    """
    import logging

    logging.basicConfig(level=settings.LOG_LEVEL)
    logger = logging.getLogger(__name__)

    logger.info("Starting AI Internship Hunter API")
    logger.info("Environment: %s", settings.APP_ENV)
    logger.info("Gemini model: %s", settings.GEMINI_MODEL)

    yield

    logger.info("Shutting down AI Internship Hunter API")


# ── App factory ────────────────────────────────────────────────────────────
def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Called once at module level (see bottom of file).
    Also called in tests to get isolated instances.
    """
    application = FastAPI(
        title="AI Internship Hunter",
        description="Personal AI-powered internship acquisition system",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # ── CORS ───────────────────────────────────────────────────────────────
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Global exception handlers ──────────────────────────────────────────
    @application.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        """
        Catch-all handler for unhandled exceptions.

        Returns a consistent error envelope instead of a raw 500 traceback.
        In development, the detail is included for debugging.
        """
        import logging

        logger = logging.getLogger(__name__)
        logger.exception("Unhandled exception on %s %s", request.method, request.url)

        detail = str(exc) if settings.is_development else "Internal server error"

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "data": None,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": detail,
                },
            },
        )

    # ── Routers ────────────────────────────────────────────────────────────
    # All routes are prefixed with /api to match the frontend's api.ts client.
    application.include_router(health.router, prefix="/api")

    # Phase 1+ routers registered here as they're built:
    # application.include_router(jobs.router,    prefix="/api")
    # application.include_router(resumes.router, prefix="/api")
    # application.include_router(scraper.router, prefix="/api")

    return application


# ── Module-level app instance ──────────────────────────────────────────────
# uvicorn references this: uvicorn app.main:app
app = create_app()