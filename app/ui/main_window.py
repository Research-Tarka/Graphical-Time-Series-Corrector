"""Main application window: assembles all panels and wires them together."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PyQt6 import QtCore, QtWidgets

from app.core.session import DataSession
from app.core.corrections import REGISTRY, DETECTION_REGISTRY, CorrectionContext
from app.core.selection import SelectionMode
from app.utils import settings as app_settings
from app.utils.config import APP_DIR

from .plot_widget import TimeSeriesPlot
from .selection_tools import SelectionToolbar, SelectionController
from .event_overlay import EventOverlayManager
from .correction_panel import CorrectionPanel
from .detection_panel import DetectionPanel
from .history_panel import HistoryPanel
from .file_panel import FilePanel
from .view_controls import YRangeControl

DATA_FILTER = "Data (*.parquet *.csv *.xlsx *.xls);;All files (*)"
EVENTS_FILTER = "Events (*.parquet *.csv *.xlsx *.xls);;All files (*)"


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Time Series Correction")
        self.resize(1500, 950)

        self.session = DataSession()
        self._detection_results: dict[str, object] = {}
        self._view_history: list[tuple[tuple[float, float], tuple[float, float]]] = []

        # Debounce selection-point redraws while dragging a selection region:
        # redrawing thousands of scatter points on every drag frame is slow.
        self._selection_points_timer = QtCore.QTimer(self)
        self._selection_points_timer.setSingleShot(True)
        self._selection_points_timer.setInterval(40)
        self._selection_points_timer.timeout.connect(self.refresh_selection_points)

        # --- widgets -------------------------------------------------
        self.file_panel = FilePanel()
        self.plot = TimeSeriesPlot()
        self.selection_toolbar = SelectionToolbar()
        self.y_range_control = YRangeControl()
        self.selection_controller = SelectionController(self.plot)
        self.event_overlay = EventOverlayManager(self.plot)
        self.correction_panel = CorrectionPanel()
        self.detection_panel = DetectionPanel()
        self.history_panel = HistoryPanel()

        # --- layout ----------------------------------------------------
        central = QtWidgets.QWidget()
        main_layout = QtWidgets.QVBoxLayout(central)
        self.file_panel.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Fixed
        )
        main_layout.addWidget(self.file_panel, 0)

        plot_container = QtWidgets.QWidget()
        plot_layout = QtWidgets.QVBoxLayout(plot_container)
        plot_layout.setContentsMargins(0, 0, 0, 0)

        toolbar_row = QtWidgets.QWidget()
        toolbar_layout = QtWidgets.QHBoxLayout(toolbar_row)
        toolbar_layout.setContentsMargins(0, 0, 0, 0)
        toolbar_layout.addWidget(self.selection_toolbar)
        toolbar_layout.addWidget(self._vline())
        toolbar_layout.addWidget(self.y_range_control)
        plot_layout.addWidget(toolbar_row)
        plot_layout.addWidget(self.plot)

        side_panel = QtWidgets.QWidget()
        side_layout = QtWidgets.QVBoxLayout(side_panel)
        side_layout.addWidget(self.correction_panel)
        side_layout.addWidget(self.detection_panel)
        side_layout.addWidget(self.history_panel)

        side_scroll = QtWidgets.QScrollArea()
        side_scroll.setWidget(side_panel)
        side_scroll.setWidgetResizable(True)
        side_scroll.setMinimumWidth(360)
        side_scroll.setMaximumWidth(480)

        splitter = QtWidgets.QSplitter()
        splitter.addWidget(plot_container)
        splitter.addWidget(side_scroll)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        main_layout.addWidget(splitter, 1)

        self.setCentralWidget(central)
        self.status_bar = self.statusBar()

        self.file_panel.set_events_enabled(False)

        # --- connections -------------------------------------------------
        self.file_panel.openDataRequested.connect(self.open_data_file)
        self.file_panel.openEventsRequested.connect(self.open_events_file)
        self.file_panel.variableChanged.connect(self.on_variable_changed)
        self.file_panel.timeAxisChanged.connect(self.on_time_axis_changed)
        self.file_panel.displayModeChanged.connect(self.on_display_mode_changed)
        self.file_panel.eventsVisibilityChanged.connect(self.event_overlay.set_visible)
        self.file_panel.saveRequested.connect(self.on_save)
        self.file_panel.themeToggled.connect(self.on_theme_toggled)

        self.selection_toolbar.modeChanged.connect(self.selection_controller.set_mode)
        self.selection_toolbar.clearClicked.connect(self.selection_controller.clear_selection)
        self.selection_controller.selectionChanged.connect(self.on_selection_changed)

        self.y_range_control.rangeApplied.connect(self.on_y_range_applied)
        self.y_range_control.autoRequested.connect(self.on_y_range_auto)
        self.y_range_control.backRequested.connect(self.on_view_back)

        self.correction_panel.applyRequested.connect(self.on_apply_correction)
        self.plot.hoverValueChanged.connect(self.correction_panel.set_hover_value)

        self.detection_panel.detectRequested.connect(self.on_detect)
        self.detection_panel.selectRequested.connect(self.on_select_detected)
        self.detection_panel.clearRequested.connect(self.on_clear_detected)

        self.history_panel.undoRequested.connect(self.on_undo)
        self.history_panel.resetRequested.connect(self.on_reset)
        self.history_panel.deleteRequested.connect(self.on_delete_history_entry)
        self.history_panel.restoreDeletedRequested.connect(self.on_restore_deleted_entry)

        self._apply_theme(app_settings.get_theme(), sync_button=True)

    # ------------------------------------------------------------------
    # Theme
    # ------------------------------------------------------------------
    def on_theme_toggled(self, theme: str) -> None:
        app_settings.set_theme(theme)
        self._apply_theme(theme, sync_button=False)

    def _apply_theme(self, theme: str, sync_button: bool) -> None:
        qss_name = "theme_dark.qss" if theme == "dark" else "theme_light.qss"
        qss_path = APP_DIR / "resources" / qss_name
        stylesheet = qss_path.read_text(encoding="utf-8") if qss_path.exists() else ""
        app = QtWidgets.QApplication.instance()
        if app is not None:
            app.setStyleSheet(stylesheet)
        self.plot.set_theme(theme)
        if sync_button:
            self.file_panel.set_theme_button_state(theme)

    @staticmethod
    def _vline() -> QtWidgets.QFrame:
        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.Shape.VLine)
        line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        return line

    # ------------------------------------------------------------------
    # File loading
    # ------------------------------------------------------------------
    def open_data_file(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Open a data file", "", DATA_FILTER
        )
        if not path:
            return
        try:
            self.session.load_table(Path(path))
        except Exception as exc:  # noqa: BLE001
            QtWidgets.QMessageBox.critical(self, "Loading error", str(exc))
            return

        self.setWindowTitle(f"Time Series Correction - {self.session.source_path.name}")
        self.file_panel.set_time_axis_columns(self.session.column_names, self.session.timestamp_col)
        self.file_panel.set_variables(self.session.variable_names)
        self.file_panel.set_events_enabled(self.session.events is not None)
        self.plot.clear_all()
        self._clear_detection_ui()
        self.event_overlay.set_events(self.session.events_for_table)
        self.status_bar.showMessage(
            f"{self.session.source_path.name} - {len(self.session.timestamps):,} rows, "
            f"{len(self.session.variable_names)} variables".replace(",", " ")
        )

        if self.session.variable_names:
            self.file_panel.variable_combo.setCurrentIndex(0)
            self.on_variable_changed(self.session.variable_names[0])

    def on_time_axis_changed(self, name: str) -> None:
        if not name or name not in self.session.column_names or name == self.session.timestamp_col:
            return
        try:
            self.session.set_timestamp_column(name)
        except Exception as exc:  # noqa: BLE001
            QtWidgets.QMessageBox.critical(self, "Invalid time axis", str(exc))
            self.file_panel.set_time_axis_columns(self.session.column_names, self.session.timestamp_col)
            return

        self.file_panel.set_variables(self.session.variable_names)
        self.plot.clear_all()
        self._clear_detection_ui()
        self.event_overlay.set_events(self.session.events_for_table)

        if self.session.variable_names:
            self.file_panel.variable_combo.setCurrentIndex(0)
            self.on_variable_changed(self.session.variable_names[0])

    def open_events_file(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Open an events file", "", EVENTS_FILTER
        )
        if not path:
            return
        try:
            self.session.load_events(Path(path))
        except Exception as exc:  # noqa: BLE001
            QtWidgets.QMessageBox.critical(self, "Loading error", str(exc))
            return
        self.file_panel.set_events_enabled(True)
        self.event_overlay.set_events(self.session.events_for_table)

    # ------------------------------------------------------------------
    # Variable / display
    # ------------------------------------------------------------------
    def on_variable_changed(self, name: str) -> None:
        if not name or name not in self.session.variable_names:
            return
        vs = self.session.open_variable(name)
        self._clear_detection_ui()
        self.selection_controller.set_data(self.session.timestamps_epoch, vs.corrected)
        self.refresh_plot()
        self.plot.fit_view_to_data(
            self.session.timestamps_epoch, vs.raw, vs.corrected, self.session.display_mode
        )
        self._sync_y_range_control()
        self.selection_controller.set_mode(self.selection_toolbar.current_mode())
        self.history_panel.refresh(vs.history)

    def _sync_y_range_control(self) -> None:
        (_, _), (ymin, ymax) = self.plot.getViewBox().viewRange()
        self.y_range_control.set_range(ymin, ymax)

    def _push_view_history(self) -> None:
        xr, yr = self.plot.getViewBox().viewRange()
        self._view_history.append((tuple(xr), tuple(yr)))
        self.y_range_control.set_back_enabled(True)

    def on_y_range_applied(self, ymin: float, ymax: float) -> None:
        self._push_view_history()
        self.plot.setYRange(ymin, ymax, padding=0)

    def on_y_range_auto(self) -> None:
        vs = self.session.active
        if vs is None:
            return
        self._push_view_history()
        self.plot.fit_view_to_data(
            self.session.timestamps_epoch, vs.raw, vs.corrected, self.session.display_mode
        )
        self._sync_y_range_control()

    def on_view_back(self) -> None:
        if not self._view_history:
            return
        xr, yr = self._view_history.pop()
        self.plot.setXRange(*xr, padding=0)
        self.plot.setYRange(*yr, padding=0)
        self._sync_y_range_control()
        if not self._view_history:
            self.y_range_control.set_back_enabled(False)

    def on_display_mode_changed(self, mode: str) -> None:
        self.session.display_mode = mode
        self.refresh_plot()

    def refresh_plot(self) -> None:
        vs = self.session.active
        if vs is None:
            return
        self.plot.set_data(
            self.session.timestamps_epoch, vs.raw, vs.corrected, self.session.display_mode
        )
        self.refresh_selection_points()

    # ------------------------------------------------------------------
    # Selection
    # ------------------------------------------------------------------
    def on_selection_changed(self) -> None:
        self.correction_panel.set_selection_mask(self.selection_controller.state.mask)
        self._selection_points_timer.start()

    def refresh_selection_points(self) -> None:
        vs = self.session.active
        mask = self.selection_controller.state.mask
        if vs is None or mask is None or not np.any(mask):
            self.plot.set_selection_points(np.array([]), np.array([]))
            return
        idx = np.where(mask)[0]
        y_source = vs.raw if self.session.display_mode == "raw" else vs.corrected
        self.plot.set_selection_points(self.session.timestamps_epoch[idx], y_source[idx])

    # ------------------------------------------------------------------
    # Corrections
    # ------------------------------------------------------------------
    def on_apply_correction(self, op_id: str, params: dict) -> None:
        vs = self.session.active
        if vs is None:
            return
        op = REGISTRY[op_id]
        ctx = CorrectionContext(
            values=vs.corrected,
            timestamps=self.session.timestamps,
            selection_mask=self.selection_controller.state.mask,
            params=params,
        )
        try:
            result = op.apply(ctx)
        except Exception as exc:  # noqa: BLE001
            QtWidgets.QMessageBox.warning(self, "Correction failed", str(exc))
            return

        if result.indices.size == 0:
            self.correction_panel.show_status(f"{op.label}: no points affected.")
            return

        self.session.apply_correction(op_id, op.label, result)
        self.selection_controller.update_y(vs.corrected)
        self.refresh_plot()
        self.history_panel.refresh(vs.history)
        self.correction_panel.show_status(f"{op.label} applied to {result.indices.size} point(s).")

    def on_undo(self) -> None:
        vs = self.session.active
        entry = self.session.undo()
        if entry is None or vs is None:
            return
        self.selection_controller.update_y(vs.corrected)
        self.refresh_plot()
        self.history_panel.refresh(vs.history)

    def on_delete_history_entry(self, position: int) -> None:
        vs = self.session.active
        entry = self.session.delete_history_entry(position)
        if entry is None or vs is None:
            return
        self.selection_controller.update_y(vs.corrected)
        self.refresh_plot()
        self.history_panel.refresh(vs.history)

    def on_restore_deleted_entry(self) -> None:
        vs = self.session.active
        entry = self.session.restore_deleted_entry()
        if entry is None or vs is None:
            return
        self.selection_controller.update_y(vs.corrected)
        self.refresh_plot()
        self.history_panel.refresh(vs.history)

    def on_reset(self) -> None:
        vs = self.session.active
        if vs is None:
            return
        answer = QtWidgets.QMessageBox.question(
            self,
            "Confirm",
            "Revert to raw data for this variable?\n"
            "(The correction history for this variable will be cleared.)",
        )
        if answer != QtWidgets.QMessageBox.StandardButton.Yes:
            return
        self.session.reset_to_raw()
        self.selection_controller.update_y(vs.corrected)
        self.refresh_plot()
        self.history_panel.refresh(vs.history)

    # ------------------------------------------------------------------
    # Detection
    # ------------------------------------------------------------------
    def on_detect(self, op_id: str, params: dict) -> None:
        vs = self.session.active
        if vs is None:
            return
        op = DETECTION_REGISTRY[op_id]
        ctx = CorrectionContext(
            values=vs.corrected,
            timestamps=self.session.timestamps,
            selection_mask=None,
            params=params,
        )
        result = op.apply(ctx)
        self._detection_results[op_id] = result
        self.detection_panel.set_count(op_id, int(result.indices.size))

        x = self.session.timestamps_epoch[result.indices]
        y = vs.corrected[result.indices]
        if op_id == "spike":
            self.plot.set_spike_points(x, y)
        elif op_id == "freeze":
            self.plot.set_freeze_points(x, y)

    def on_select_detected(self, op_id: str) -> None:
        result = self._detection_results.get(op_id)
        vs = self.session.active
        if result is None or vs is None:
            return
        mask = np.zeros(vs.corrected.shape, dtype=bool)
        mask[result.indices] = True
        self.selection_controller.set_external_mask(mask)

    def on_clear_detected(self, op_id: str) -> None:
        self._detection_results.pop(op_id, None)
        if op_id == "spike":
            self.plot.set_spike_points(np.array([]), np.array([]))
        elif op_id == "freeze":
            self.plot.set_freeze_points(np.array([]), np.array([]))
        self.detection_panel.set_count(op_id, 0)

    def _clear_detection_ui(self) -> None:
        for op_id in list(DETECTION_REGISTRY):
            self.on_clear_detected(op_id)

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------
    def on_save(self, mode: str) -> None:
        if not self.session.dirty_variables():
            QtWidgets.QMessageBox.information(self, "Save", "No corrections to save.")
            return
        try:
            if mode == "all":
                paths = self.session.save_all(fmt=self.file_panel.save_format())
                path_list = "\n".join(str(p) for p in paths.values())
            else:
                path = self.session.save(mode=mode, fmt=self.file_panel.save_format())
                path_list = str(path)
        except Exception as exc:  # noqa: BLE001
            QtWidgets.QMessageBox.critical(self, "Save error", str(exc))
            return
        QtWidgets.QMessageBox.information(self, "Saved", f"File(s) saved:\n{path_list}")
        self.status_bar.showMessage(f"Saved: {path_list}")
