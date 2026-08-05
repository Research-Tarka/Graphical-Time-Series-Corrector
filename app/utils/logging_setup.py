"""Crash/log file setup, since the app runs without a visible console."""

from __future__ import annotations

import logging
import sys
import traceback

from .config import LOG_DIR

LOG_FILE = LOG_DIR / "app.log"
CRASH_FILE = LOG_DIR / "crash.log"


def setup_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def install_excepthook() -> None:
    def _hook(exc_type, exc_value, exc_tb):
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CRASH_FILE, "a", encoding="utf-8") as fh:
            fh.write("=" * 60 + "\n")
            traceback.print_exception(exc_type, exc_value, exc_tb, file=fh)
        traceback.print_exception(exc_type, exc_value, exc_tb)

    sys.excepthook = _hook
