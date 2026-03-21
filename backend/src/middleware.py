"""
middleware.py — request tracing middleware.

Adds an X-Request-ID header, measures request duration, and emits structured
logs for request start and completion including `request_id` for correlation.
"""
import time
import uuid
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


class TracingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        start = time.time()

        # Attach request_id to request.state for handlers to use
        request.state.request_id = request_id

        logger.info(f"request.start {request.method} {request.url.path}", extra={"request_id": request_id})

        try:
            response: Response = await call_next(request)
        except Exception as exc:
            # Log exception with request_id
            logger.exception("request.error", extra={"request_id": request_id})
            raise

        duration = time.time() - start
        response.headers["X-Request-ID"] = request_id

        logger.info(
            f"request.finish {request.method} {request.url.path} {response.status_code} {duration:.3f}s",
            extra={"request_id": request_id},
        )

        return response


def register_tracing(app):
    """Register the tracing middleware on the FastAPI app."""
    app.add_middleware(TracingMiddleware)
