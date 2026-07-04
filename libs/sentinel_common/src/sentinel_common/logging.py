"""Structured logging setup shared by every Sentinel service.

Emits single-line JSON records to stdout in non-local environments so logs
are directly consumable by log aggregators; falls back to a human-readable
format when `json_logs=False` (handy for local development).
"""

import json
import logging
import sys
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload)


_TEXT_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def configure_logging(service_name: str, level: str = "INFO", json_logs: bool = True) -> None:
    """Configure the root logger once at process startup."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter() if json_logs else logging.Formatter(_TEXT_FORMAT))

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())

    logging.getLogger(service_name).setLevel(level.upper())


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
