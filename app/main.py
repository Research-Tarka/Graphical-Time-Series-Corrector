"""Entry point: launches the correction application."""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running as `python app/main.py` (not just `python -m app.main`)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PyQt6 import QtWidgets

from app.utils.logging_setup import setup_logging, install_excepthook
from app.ui.main_window import MainWindow


def main() -> int:
    setup_logging()
    install_excepthook()

    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("Time Series Correction")

    window = MainWindow()
    window.showMaximized()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
