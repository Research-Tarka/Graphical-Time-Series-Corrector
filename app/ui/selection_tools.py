"""Selection toolbar + controller bridging the plot and SelectionState."""

from __future__ import annotations

from typing import Optional

import numpy as np
import pyqtgraph as pg
from PyQt6 import QtCore, QtWidgets, QtGui

from app.core.selection import SelectionMode, SelectionState


class SelectionToolbar(QtWidgets.QWidget):
    """Radio-style buttons to pick the selection mode + a clear button."""

    modeChanged = QtCore.pyqtSignal(SelectionMode)
    clearClicked = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(QtWidgets.QLabel("Selection:"))

        self._group = QtWidgets.QButtonGroup(self)
        self._group.setExclusive(True)

        self._buttons: dict[SelectionMode, QtWidgets.QToolButton] = {}
        labels = {
            SelectionMode.POINT: "Point",
            SelectionMode.X_RANGE: "X range",
            SelectionMode.Y_RANGE: "Y range",
            SelectionMode.XY_RECT: "X/Y rectangle",
        }
        for mode, text in labels.items():
            btn = QtWidgets.QToolButton()
            btn.setText(text)
            btn.setCheckable(True)
            self._group.addButton(btn)
            self._buttons[mode] = btn
            layout.addWidget(btn)
            btn.clicked.connect(lambda _checked, m=mode: self.modeChanged.emit(m))

        self._buttons[SelectionMode.X_RANGE].setChecked(True)

        layout.addStretch(1)

        clear_btn = QtWidgets.QPushButton("Clear selection")
        clear_btn.clicked.connect(self.clearClicked.emit)
        layout.addWidget(clear_btn)

    def current_mode(self) -> SelectionMode:
        for mode, btn in self._buttons.items():
            if btn.isChecked():
                return mode
        return SelectionMode.X_RANGE


class SelectionController(QtCore.QObject):
    """Owns the selection tools overlaid on the plot and the resulting mask."""

    selectionChanged = QtCore.pyqtSignal()

    def __init__(self, plot_widget: pg.PlotWidget, parent=None):
        super().__init__(parent)
        self.plot = plot_widget
        self.state = SelectionState()

        self._region_item: Optional[pg.LinearRegionItem] = None
        self._roi_item: Optional[pg.RectROI] = None
        self._rect_first_point: Optional[tuple[float, float]] = None

        self._x: Optional[np.ndarray] = None
        self._y: Optional[np.ndarray] = None

        self.plot.scene().sigMouseClicked.connect(self._on_mouse_clicked)

    # ------------------------------------------------------------------
    def set_data(self, x_epoch: np.ndarray, y: np.ndarray) -> None:
        self._x = x_epoch
        self._y = y
        self.clear_selection()

    def update_y(self, y: np.ndarray) -> None:
        """Update the Y array (e.g. after a correction) without clearing the selection."""

        self._y = y

    def set_mode(self, mode: SelectionMode) -> None:
        self.state.mode = mode
        self._remove_tools()
        self.state.clear()

        if mode == SelectionMode.X_RANGE:
            self._region_item = pg.LinearRegionItem(orientation="vertical")
            self._region_item.setZValue(20)
            self._region_item.sigRegionChanged.connect(self._on_region_changed)
            self.plot.addItem(self._region_item)
            self._init_region()
        elif mode == SelectionMode.Y_RANGE:
            self._region_item = pg.LinearRegionItem(orientation="horizontal")
            self._region_item.setZValue(20)
            self._region_item.sigRegionChanged.connect(self._on_y_region_changed)
            self.plot.addItem(self._region_item)
            self._init_y_region()
        elif mode == SelectionMode.XY_RECT:
            self._rect_first_point = None

        self.selectionChanged.emit()

    def clear_selection(self) -> None:
        self._rect_first_point = None
        if self._roi_item is not None:
            self.plot.removeItem(self._roi_item)
            self._roi_item = None
        self.state.clear()
        self.selectionChanged.emit()

    # ------------------------------------------------------------------
    def _remove_tools(self) -> None:
        if self._region_item is not None:
            self.plot.removeItem(self._region_item)
            self._region_item = None
        if self._roi_item is not None:
            self.plot.removeItem(self._roi_item)
            self._roi_item = None

    def _init_region(self) -> None:
        if self._region_item is None:
            return
        view_range = self.plot.getViewBox().viewRange()
        x0, x1 = view_range[0]
        center = (x0 + x1) / 2
        width = (x1 - x0) * 0.1
        self._region_item.setRegion((center - width / 2, center + width / 2))
        self._on_region_changed()

    def _init_y_region(self) -> None:
        if self._region_item is None:
            return
        view_range = self.plot.getViewBox().viewRange()
        y0, y1 = view_range[1]
        center = (y0 + y1) / 2
        height = (y1 - y0) * 0.1
        self._region_item.setRegion((center - height / 2, center + height / 2))
        self._on_y_region_changed()

    def _show_rect(self, x0: float, y0: float, x1: float, y1: float) -> None:
        if self._roi_item is not None:
            self.plot.removeItem(self._roi_item)
            self._roi_item = None

        x0, x1 = sorted((x0, x1))
        y0, y1 = sorted((y0, y1))

        self._roi_item = pg.RectROI(
            (x0, y0), (x1 - x0, y1 - y0), pen=pg.mkPen("y", width=2), movable=False
        )
        # Display-only: drop the default resize handle.
        for handle in list(self._roi_item.handles):
            self._roi_item.removeHandle(handle["item"])
        self._roi_item.setZValue(20)
        self.plot.addItem(self._roi_item)

        mask = (self._x >= x0) & (self._x <= x1) & (self._y >= y0) & (self._y <= y1)
        self.state.set_mask(mask)
        self.state.x_range = (x0, x1)
        self.state.y_range = (y0, y1)

    # ------------------------------------------------------------------
    def _on_region_changed(self) -> None:
        if self._x is None or self._region_item is None:
            return
        x0, x1 = self._region_item.getRegion()
        mask = (self._x >= x0) & (self._x <= x1)
        self.state.set_mask(mask)
        self.state.x_range = (x0, x1)
        self.state.y_range = None
        self.selectionChanged.emit()

    def _on_y_region_changed(self) -> None:
        if self._y is None or self._region_item is None:
            return
        y0, y1 = self._region_item.getRegion()
        mask = (self._y >= y0) & (self._y <= y1)
        self.state.set_mask(mask)
        self.state.x_range = None
        self.state.y_range = (y0, y1)
        self.selectionChanged.emit()

    def _on_mouse_clicked(self, event) -> None:
        if self._x is None or self._x.size == 0:
            return
        view_box = self.plot.getViewBox()
        if not view_box.sceneBoundingRect().contains(event.scenePos()):
            return
        point = view_box.mapSceneToView(event.scenePos())

        if self.state.mode == SelectionMode.POINT:
            self._handle_point_click(point)
        elif self.state.mode == SelectionMode.XY_RECT:
            self._handle_rect_click(point)

    def _handle_point_click(self, point) -> None:
        idx = int(np.searchsorted(self._x, point.x()))
        idx = max(0, min(idx, self._x.size - 1))
        if idx > 0 and abs(self._x[idx - 1] - point.x()) < abs(self._x[idx] - point.x()):
            idx -= 1

        mask = np.zeros(self._x.shape, dtype=bool)
        mask[idx] = True
        self.state.set_mask(mask)
        self.state.point_index = idx
        self.state.x_range = None
        self.state.y_range = None
        self.selectionChanged.emit()

    def _handle_rect_click(self, point) -> None:
        if self._rect_first_point is None:
            # First corner: clear any previous rectangle and wait for the second click.
            if self._roi_item is not None:
                self.plot.removeItem(self._roi_item)
                self._roi_item = None
            self.state.clear()
            self._rect_first_point = (point.x(), point.y())
            self.selectionChanged.emit()
        else:
            x0, y0 = self._rect_first_point
            self._show_rect(x0, y0, point.x(), point.y())
            self._rect_first_point = None
            self.selectionChanged.emit()

    # ------------------------------------------------------------------
    def set_external_mask(self, mask: np.ndarray) -> None:
        """Used by the detection panel to turn candidates into a selection."""

        self._remove_tools()
        self.state.mode = SelectionMode.POINT  # informational only
        self.state.set_mask(mask)
        self.state.x_range = None
        self.state.y_range = None
        self.state.point_index = None
        self.selectionChanged.emit()
