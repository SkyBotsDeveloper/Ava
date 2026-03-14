from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

from ava.config.paths import AppPaths

_STANDARD_RECORD_FIELDS = set(logging.makeLogRecord({}).__dict__.keys())


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "event"):
            payload["event"] = record.event
        extras = {
            key: self._json_safe(value)
            for key, value in record.__dict__.items()
            if key not in _STANDARD_RECORD_FIELDS and key not in {"event"}
        }
        if extras:
            payload["details"] = extras
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=True)

    @staticmethod
    def _json_safe(value):
        if isinstance(value, str | int | float | bool) or value is None:
            return value
        if isinstance(value, dict):
            return {str(key): JsonFormatter._json_safe(item) for key, item in value.items()}
        if isinstance(value, list | tuple | set):
            return [JsonFormatter._json_safe(item) for item in value]
        return str(value)


def configure_logging(*, paths: AppPaths, level: str, debug: bool) -> None:
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(level.upper())

    formatter = JsonFormatter()

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG if debug else level.upper())
    console_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(paths.logs_dir / "ava.log", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG if debug else level.upper())
    file_handler.setFormatter(formatter)

    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
