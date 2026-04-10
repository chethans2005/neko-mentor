"""middleware.py — request tracing middleware.

Adds an X-Request-ID header, measures request duration, and emits structured
logs for request start and completion including `request_id` for correlation.
"""
from __future__ import annotations

import time
import uuid
import logging
from typing import Awaitable, Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

# Canonical header value used throughout the app
HEADER_X_REQUEST_ID = "X-Request-ID"


class TracingMiddleware(BaseHTTPMiddleware):
    """HTTP middleware that attaches a request id, times requests, and logs.

    Notes:
    - Uses a monotonic clock for duration measurement.
    - Adds `request_id` to `request.state` so handlers can access it.
    - Uses parameterized logging to avoid eager string interpolation.
    """

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]):
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        start = time.monotonic()

        # Attach request_id to request.state for handlers to use
        request.state.request_id = request_id

        logger.info("request.start %s %s", request.method, request.url.path, extra={"request_id": request_id})

        try:
            response: Response = await call_next(request)
        except Exception:
            # Log exception with request_id and re-raise for upstream handling
            logger.exception("request.error", extra={"request_id": request_id})
            raise

        duration = time.monotonic() - start
        # Ensure header uses canonical casing
        response.headers[HEADER_X_REQUEST_ID] = request_id

        logger.info(
            "request.finish %s %s %d %.3fs",
            request.method,
            request.url.path,
            response.status_code,
            duration,
            extra={"request_id": request_id},
        )

        return response


def register_tracing(app) -> None:
    """Register the tracing middleware on the FastAPI/Starlette app.

    Example:
        register_tracing(app)
    """

    app.add_middleware(TracingMiddleware)
