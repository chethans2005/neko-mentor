"""
logging_config.py — structured JSON logging configuration.

Provides `configure_logging()` to set up a JSON log formatter that includes
timestamp, level, message, logger name and optional `request_id` when
present in the `extra` dict. Designed to be lightweight with zero external
dependencies so it works in minimal environments.
"""
import logging
import os
import json
from datetime import datetime


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Include request_id if provided in extra
        if hasattr(record, "request_id") and record.request_id:
            payload["request_id"] = record.request_id
        # Include exception info if present
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging():
    """Configure root logger with JSONFormatter to stdout."""
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())

    root = logging.getLogger()
    # Avoid adding duplicate handlers during repeated calls
    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        root.addHandler(handler)
    root.setLevel(level)

    # Configure uvicorn and other noisy loggers to propagate
    logging.getLogger("uvicorn.error").handlers = root.handlers
    logging.getLogger("uvicorn.access").handlers = root.handlers
