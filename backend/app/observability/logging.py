
# app/observability/logging.py

import json
import logging
import sys
from datetime import datetime, timezone

from app.observability.context import get_request_id

from opentelemetry import trace


class JsonFormatter(logging.Formatter):

    def format(
        self,
        record: logging.LogRecord,
    ) -> str:

        current_span = trace.get_current_span()
        span_context = current_span.get_span_context()

        trace_id = None
        span_id = None

        if span_context.is_valid:

            trace_id = format(
                span_context.trace_id,
                "032x",
            )

            span_id = format(
                span_context.span_id,
                "016x",
            )

        payload = {
            "timestamp": datetime.now(
                timezone.utc
            ).isoformat(),

            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "trace_id": trace_id,
            "span_id": span_id,
            "request_id": get_request_id(),
        }

        if record.exc_info:

            payload["exception"] = self.formatException(
                record.exc_info
            )

        return json.dumps(
            payload,
            default=str,
        )


def configure_logging() -> None:

    handler = logging.StreamHandler(
        sys.stdout
    )

    handler.setFormatter(
        JsonFormatter()
    )

    root_logger = logging.getLogger()

    root_logger.setLevel(
        logging.INFO
    )

    # Prevent duplicate handlers during reload.
    root_logger.handlers.clear()

    root_logger.addHandler(
        handler
    )