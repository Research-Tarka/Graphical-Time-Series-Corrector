"""Persisted user preferences (currently just the light/dark theme)."""

from __future__ import annotations

from PyQt6.QtCore import QSettings

ORG = "PROJECT-LOGGERNET"
APP = "GraphicalTimeSeriesCorrector"


def get_theme() -> str:
    return QSettings(ORG, APP).value("theme", "light", type=str)


def set_theme(theme: str) -> None:
    QSettings(ORG, APP).setValue("theme", theme)
