from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

from ava.config.paths import AppPaths


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
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=True)


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
