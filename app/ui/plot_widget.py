"""Main time-series plot widget (pyqtgraph based)."""

from __future__ import annotations

import datetime

import numpy as np
import pyqtgraph as pg
from PyQt6 import QtCore

from app.utils.config import RAW_COLOR, CORRECTED_COLOR, SELECTION_COLOR, SPIKE_COLOR, FREEZE_COLOR

# Below this distance (in pixels) from the mouse, a data point is considered "hovered".
HOVER_PIXEL_RADIUS = 15

# Cap on rendered selection markers: drawing thousands of overlapping circles
# slows down every repaint during pan/zoom, with no visible benefit.
MAX_SELECTION_POINTS = 3000


class TimeSeriesPlot(pg.PlotWidget):
    """Plot a variable over time, with raw/corrected curves and overlays."""

    # Emits the Y value of the hovered data point, or None when not hovering one.
    hoverValueChanged = QtCore.pyqtSignal(object)

    def __init__(self, parent=None):
        axis = pg.DateAxisItem(orientation="bottom")
        super().__init__(parent=parent, axisItems={"bottom": axis})

        self.showGrid(x=True, y=True, alpha=0.25)
        self.setLabel("bottom", "Time")

        self._x: np.ndarray = np.array([])
        self._y: np.ndarray = np.array([])

        self.raw_curve = pg.PlotDataItem(pen=pg.mkPen(RAW_COLOR, width=1), name="Raw")
        self.corrected_curve = pg.PlotDataItem(pen=pg.mkPen(CORRECTED_COLOR, width=1.3), name="Corrected")
        for curve in (self.raw_curve, self.corrected_curve):
            curve.setDownsampling(auto=True, method="peak")
            curve.setClipToView(True)
        self.addItem(self.raw_curve)
        self.addItem(self.corrected_curve)

        self.selection_scatter = pg.ScatterPlotItem(
            size=4, brush=pg.mkBrush(*SELECTION_COLOR, 220), pen=None
        )
        self.selection_scatter.setZValue(10)
        self.addItem(self.selection_scatter)

        self.spike_scatter = pg.ScatterPlotItem(
            size=10, symbol="t1", brush=pg.mkBrush(*SPIKE_COLOR, 220), pen=None
        )
        self.spike_scatter.setZValue(9)
        self.addItem(self.spike_scatter)

        self.freeze_scatter = pg.ScatterPlotItem(
            size=9, symbol="s", brush=pg.mkBrush(*FREEZE_COLOR, 200), pen=None
        )
        self.freeze_scatter.setZValue(9)
        self.addItem(self.freeze_scatter)

        # Marker shown on the nearest data point when the mouse hovers close to it.
        self.hover_scatter = pg.ScatterPlotItem(
            size=12, symbol="o", brush=pg.mkBrush(255, 255, 0, 160), pen=pg.mkPen("k", width=1)
        )
        self.hover_scatter.setZValue(15)
        self.addItem(self.hover_scatter)
        self._hover_index: int | None = None

        self.addLegend()

        # Coordinate readout, pinned to the top-right corner of the plot.
        self.coord_label = pg.TextItem(anchor=(1, 0), color="k", fill=(255, 255, 255, 180))
        self.coord_label.setZValue(30)
        self.addItem(self.coord_label, ignoreBounds=True)
        self.coord_label.hide()

        self.scene().sigMouseMoved.connect(self._on_mouse_moved)

    # ------------------------------------------------------------------
    def set_theme(self, theme: str) -> None:
        """Switch the plot's own background/foreground; pyqtgraph draws its
        own canvas and ignores the app-wide Qt stylesheet, so this has to be
        set explicitly."""

        if theme == "dark":
            self.setBackground("#1e1e1e")
            axis_color = "#dddddd"
            label_color = "w"
            label_fill = (40, 40, 40, 200)
        else:
            self.setBackground("w")
            axis_color = "k"
            label_color = "k"
            label_fill = (255, 255, 255, 180)

        for axis_name in ("bottom", "left"):
            axis = self.getAxis(axis_name)
            axis.setPen(axis_color)
            axis.setTextPen(axis_color)

        self.coord_label.setColor(label_color)
        self.coord_label.fill = pg.mkBrush(*label_fill)

    # ------------------------------------------------------------------
    def set_data(self, x_epoch: np.ndarray, raw: np.ndarray, corrected: np.ndarray, display_mode: str) -> None:
        show_raw = display_mode in ("raw", "both")
        show_corrected = display_mode in ("corrected", "both")

        if show_raw:
            self.raw_curve.setData(x_epoch, raw, connect="finite")
        self.raw_curve.setVisible(show_raw)

        if show_corrected:
            self.corrected_curve.setData(x_epoch, corrected, connect="finite")
        self.corrected_curve.setVisible(show_corrected)

        self._x = x_epoch
        self._y = corrected if show_corrected else raw
        self._hover_index = None
        self._set_hover_marker([], [])

    def fit_view_to_data(self, x_epoch: np.ndarray, raw: np.ndarray, corrected: np.ndarray, display_mode: str) -> None:
        """Frame the whole variable: X on data extent, Y on the displayed curve(s) extent."""

        if x_epoch.size == 0:
            return

        values = []
        if display_mode in ("raw", "both"):
            values.append(raw)
        if display_mode in ("corrected", "both"):
            values.append(corrected)
        if not values:
            values = [raw]

        stacked = np.concatenate(values)
        finite = stacked[np.isfinite(stacked)]

        self.setXRange(x_epoch[0], x_epoch[-1], padding=0)
        if finite.size:
            self.setYRange(float(finite.min()), float(finite.max()), padding=0.05)

    def set_selection_points(self, x: np.ndarray, y: np.ndarray) -> None:
        if x.size == 0:
            self.selection_scatter.clear()
            return
        if x.size > MAX_SELECTION_POINTS:
            step = x.size // MAX_SELECTION_POINTS + 1
            x = x[::step]
            y = y[::step]
        self.selection_scatter.setData(x, y)

    def set_spike_points(self, x: np.ndarray, y: np.ndarray) -> None:
        if x.size == 0:
            self.spike_scatter.clear()
            return
        self.spike_scatter.setData(x, y)

    def set_freeze_points(self, x: np.ndarray, y: np.ndarray) -> None:
        if x.size == 0:
            self.freeze_scatter.clear()
            return
        self.freeze_scatter.setData(x, y)

    def clear_all(self) -> None:
        self.raw_curve.clear()
        self.corrected_curve.clear()
        self.selection_scatter.clear()
        self.spike_scatter.clear()
        self.freeze_scatter.clear()
        self._set_hover_marker([], [])
        self._x = np.array([])
        self._y = np.array([])
        self._hover_index = None
        self.coord_label.hide()

    # ------------------------------------------------------------------
    # Cursor readout
    # ------------------------------------------------------------------
    def hovered_value(self) -> tuple[float, float] | None:
        """Return (x_epoch, y) of the currently hovered data point, if any."""

        if self._hover_index is None:
            return None
        return float(self._x[self._hover_index]), float(self._y[self._hover_index])

    def _set_hover_marker(self, x: list, y: list) -> None:
        """Update the hover marker, forcing a repaint so old positions don't linger."""

        self.hover_scatter.setData(x, y)
        self.hover_scatter.invalidate()

    def _on_mouse_moved(self, scene_pos) -> None:
        view_box = self.getViewBox()
        if not view_box.sceneBoundingRect().contains(scene_pos):
            self.coord_label.hide()
            if self._hover_index is not None:
                self._hover_index = None
                self._set_hover_marker([], [])
                self.hoverValueChanged.emit(None)
            return

        point = view_box.mapSceneToView(scene_pos)
        x_val, y_val = point.x(), point.y()

        nearest = self._find_nearest_point(scene_pos, x_val)
        if nearest is not None:
            idx, px, py = nearest
            changed = self._hover_index != idx
            self._hover_index = idx
            self._set_hover_marker([px], [py])
            label = f"x={self._format_x(px)}\ny={py:.4g}  (point)"
            if changed:
                self.hoverValueChanged.emit(py)
        else:
            if self._hover_index is not None:
                self._hover_index = None
                self._set_hover_marker([], [])
                self.hoverValueChanged.emit(None)
            label = f"x={self._format_x(x_val)}\ny={y_val:.4g}"

        self.coord_label.setText(label)
        self._position_coord_label()
        self.coord_label.show()

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
        self.coord_label.hide()
        if self._hover_index is not None:
            self._hover_index = None
            self._set_hover_marker([], [])
            self.hoverValueChanged.emit(None)

    def _find_nearest_point(self, scene_pos, x_val: float) -> tuple[int, float, float] | None:
        if self._x.size == 0:
            return None

        idx = int(np.searchsorted(self._x, x_val))
        idx = max(0, min(idx, self._x.size - 1))
        if idx > 0 and abs(self._x[idx - 1] - x_val) < abs(self._x[idx] - x_val):
            idx -= 1

        py = self._y[idx]
        if not np.isfinite(py):
            return None

        view_box = self.getViewBox()
        point_scene = view_box.mapViewToScene(QtCore.QPointF(float(self._x[idx]), float(py)))
        dist = (point_scene - scene_pos).manhattanLength()
        if dist > HOVER_PIXEL_RADIUS:
            return None
        return idx, float(self._x[idx]), float(py)

    def _position_coord_label(self) -> None:
        (x0, x1), (y0, y1) = self.getViewBox().viewRange()
        self.coord_label.setPos(x1, y1)

    @staticmethod
    def _format_x(x_epoch: float) -> str:
        dt = datetime.datetime.utcfromtimestamp(x_epoch)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
