from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from platformdirs import user_log_path

from raucous.config import APP_AUTHOR, APP_NAME


def configure_logging(*, debug: bool) -> Path:
    log_dir = user_log_path(APP_NAME, APP_AUTHOR)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "raucous.log"

    root = logging.getLogger()
    root.setLevel(logging.DEBUG if debug else logging.INFO)
    root.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    )

    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG if debug else logging.INFO)
    console.setFormatter(formatter)
    root.addHandler(console)

    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    return log_path
