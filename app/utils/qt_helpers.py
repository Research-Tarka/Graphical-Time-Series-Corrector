"""Small Qt helper functions."""

from __future__ import annotations

from PyQt6 import QtGui


def color_from_hex(value: str | None, alpha: int = 255, default: str = "#888888") -> QtGui.QColor:
    """Parse a "#rrggbb" string into a QColor, falling back to ``default``."""

    text = value or default
    color = QtGui.QColor(text)
    if not color.isValid():
        color = QtGui.QColor(default)
    color.setAlpha(alpha)
    return color
