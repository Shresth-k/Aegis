"""Structured JSON logging for the AcmeCloud checkout service."""

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any


class JsonFormatter(logging.Formatter):
    """Format log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        """Convert a log record into a structured JSON document."""
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "service": getattr(record, "service", "checkout-service"),
            "version": getattr(record, "version", "unknown"),
            "message": record.getMessage(),
        }

        for field in (
            "request_id",
            "method",
            "path",
            "status_code",
            "duration_ms",
            "error",
        ):
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value

        return json.dumps(payload, default=str)


def configure_logging() -> None:
    """Configure the checkout service root logger."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)
