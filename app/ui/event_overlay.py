"""Render event annotations (punctual markers / period bands) on the plot."""

from __future__ import annotations

import numpy as np
import polars as pl
import pyqtgraph as pg
from PyQt6 import QtCore, QtWidgets, QtGui

from app.utils.qt_helpers import color_from_hex

EPOCH = np.datetime64("1970-01-01T00:00:00", "us")


class EventOverlayManager(QtCore.QObject):
    """Adds/removes InfiniteLine and LinearRegionItem items for events."""

    def __init__(self, plot_widget: pg.PlotWidget, parent=None):
        super().__init__(parent)
        self.plot = plot_widget
        self._items: list[tuple[pg.GraphicsObject, dict]] = []
        self._visible = True
        self.plot.scene().sigMouseMoved.connect(self._on_mouse_moved)

    def set_visible(self, visible: bool) -> None:
        self._visible = visible
        for item, _ in self._items:
            item.setVisible(visible)

    def clear(self) -> None:
        for item, _ in self._items:
            self.plot.removeItem(item)
        self._items.clear()

    def set_events(self, events: pl.DataFrame | None) -> None:
        self.clear()
        if events is None or events.height == 0:
            return

        for row in events.iter_rows(named=True):
            color = color_from_hex(row.get("color"))
            start_dt = row.get("_start_dt")
            end_dt = row.get("_end_dt")
            is_punctual = row.get("_is_punctual")
            if start_dt is None:
                continue
            start_epoch = (np.datetime64(start_dt, "us") - EPOCH) / np.timedelta64(1, "s")

            info = {
                "label": row.get("label") or "",
                "category": row.get("category") or "",
                "description": row.get("description") or "",
            }

            if is_punctual or end_dt is None:
                line = pg.InfiniteLine(
                    pos=float(start_epoch),
                    angle=90,
                    pen=pg.mkPen(color, width=2, style=QtCore.Qt.PenStyle.DashLine),
                    movable=False,
                )
                line.setZValue(5)
                line.setVisible(self._visible)
                self.plot.addItem(line)
                self._items.append((line, info))
            else:
                end_epoch = (np.datetime64(end_dt, "us") - EPOCH) / np.timedelta64(1, "s")
                region = pg.LinearRegionItem(
                    values=(float(start_epoch), float(end_epoch)),
                    brush=pg.mkBrush(color.red(), color.green(), color.blue(), 60),
                    pen=pg.mkPen(color, width=1),
                    movable=False,
                )
                region.setZValue(-10)
                region.setVisible(self._visible)
                self.plot.addItem(region)
                self._items.append((region, info))

    # ------------------------------------------------------------------
    def _on_mouse_moved(self, scene_pos) -> None:
        if not self._items or not self._visible:
            QtWidgets.QToolTip.hideText()
            return

        view_box = self.plot.getViewBox()
        if not view_box.sceneBoundingRect().contains(scene_pos):
            QtWidgets.QToolTip.hideText()
            return

        view_pos = view_box.mapSceneToView(scene_pos)
        x = view_pos.x()

        # pixel-width tolerance for InfiniteLine hover
        (x0, x1), _ = view_box.viewRange()
        width_px = max(view_box.size().width(), 1)
        tol = (x1 - x0) / width_px * 6

        for item, info in self._items:
            hit = False
            if isinstance(item, pg.InfiniteLine):
                hit = abs(item.value() - x) <= tol
            elif isinstance(item, pg.LinearRegionItem):
                lo, hi = item.getRegion()
                hit = lo <= x <= hi
            if hit:
                text = info["label"]
                if info["category"]:
                    text += f"  [{info['category']}]"
                if info["description"]:
                    text += f"\n{info['description']}"
                QtWidgets.QToolTip.showText(QtGui.QCursor.pos(), text, self.plot)
                return

        QtWidgets.QToolTip.hideText()
