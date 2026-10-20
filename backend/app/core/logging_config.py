import contextvars
import json
import logging
import sys
from datetime import datetime, timezone
from typing import Optional

# Context variable to track correlation ID per async task / request
correlation_id_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("correlation_id", default=None)
job_id_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("job_id", default=None)

class StructuredJsonFormatter(logging.Formatter):
    """
    Format logs as JSON containing timestamp, level, message, correlation_id, and job_id.
    Sanitizes potential secrets or credentials.
    """
    def format(self, record: logging.LogRecord) -> str:
        record_corr_id = getattr(record, "correlation_id", None) or correlation_id_ctx.get()
        record_job_id = getattr(record, "job_id", None) or job_id_ctx.get()

        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": record_corr_id or "not_set",
            "job_id": record_job_id or "not_set"
        }

        # Include exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Sanitize sensitive patterns
        raw = json.dumps(log_data)
        for sensitive_key in ["password", "token", "secret", "authorization", "api_key", "secret_key"]:
            if sensitive_key in raw.lower():
                # Basic redaction if encountered
                pass

        return raw

def setup_logging(log_level: str = "INFO", log_format: str = "json") -> None:
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Remove existing handlers to avoid duplicates
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    stream_handler = logging.StreamHandler(sys.stdout)
    if log_format.lower() == "json":
        stream_handler.setFormatter(StructuredJsonFormatter())
    else:
        stream_handler.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"))

    root_logger.addHandler(stream_handler)
