"""Creates the FastAPI app: startup, middleware, and routers. Endpoints live in routers/."""

import logging
import time
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse

from budgettracker.db import engine, init_db
from budgettracker.routers import auth, health, transactions

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
request_logger = logging.getLogger("budgettracker.requests")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    """Runs once at startup (before `yield`) and shutdown (after)."""
    init_db(engine)
    yield


app = FastAPI(title="Budget Tracker API", lifespan=lifespan)


@app.middleware("http")
async def log_requests(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Log every request, and turn unhandled errors into a generic 500 with the traceback logged.

    Only method, path, status, duration, and user id are logged; never bodies, headers, or tokens.
    """
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        request_logger.exception("Unhandled error in %s %s", request.method, request.url.path)
        response = JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"},
        )
    duration_ms = (time.perf_counter() - start) * 1000
    # get_current_user sets request.state.user_id; it's absent on unauthenticated requests.
    user_id = getattr(request.state, "user_id", None)
    request_logger.info(
        "%s %s %d %.1fms user=%s",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
        user_id,
    )
    return response


app.include_router(health.router)
app.include_router(transactions.router)
app.include_router(auth.router)
