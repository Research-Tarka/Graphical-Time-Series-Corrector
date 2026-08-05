"""Top bar: open data/events files, pick variable, display mode, save."""

from __future__ import annotations

from PyQt6 import QtCore, QtWidgets


class FilePanel(QtWidgets.QWidget):
    openDataRequested = QtCore.pyqtSignal()
    openEventsRequested = QtCore.pyqtSignal()
    variableChanged = QtCore.pyqtSignal(str)
    displayModeChanged = QtCore.pyqtSignal(str)
    eventsVisibilityChanged = QtCore.pyqtSignal(bool)
    timeAxisChanged = QtCore.pyqtSignal(str)
    saveRequested = QtCore.pyqtSignal(str)  # "diff" | "series" | "full" | "all"
    themeToggled = QtCore.pyqtSignal(str)  # "light" | "dark"

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QtWidgets.QHBoxLayout(self)

        self.open_data_button = QtWidgets.QPushButton("Open a data file...")
        self.open_data_button.clicked.connect(self.openDataRequested.emit)
        layout.addWidget(self.open_data_button)

        self.open_events_button = QtWidgets.QPushButton("Open an events file...")
        self.open_events_button.clicked.connect(self.openEventsRequested.emit)
        layout.addWidget(self.open_events_button)

        layout.addWidget(QtWidgets.QLabel("Time axis:"))
        self.time_axis_combo = QtWidgets.QComboBox()
        self.time_axis_combo.setSizeAdjustPolicy(
            QtWidgets.QComboBox.SizeAdjustPolicy.AdjustToContents
        )
        self.time_axis_combo.currentTextChanged.connect(self._on_time_axis_changed)
        layout.addWidget(self.time_axis_combo)

        layout.addWidget(QtWidgets.QLabel("Variable:"))
        self.variable_combo = QtWidgets.QComboBox()
        self.variable_combo.setEditable(True)
        self.variable_combo.setInsertPolicy(QtWidgets.QComboBox.InsertPolicy.NoInsert)
        self.variable_combo.currentTextChanged.connect(self._on_variable_changed)
        layout.addWidget(self.variable_combo, 1)

        layout.addWidget(QtWidgets.QLabel("Display:"))
        self.display_combo = QtWidgets.QComboBox()
        self.display_combo.addItem("Raw", "raw")
        self.display_combo.addItem("Corrected", "corrected")
        self.display_combo.addItem("Both", "both")
        self.display_combo.setCurrentIndex(2)
        self.display_combo.currentIndexChanged.connect(
            lambda _i: self.displayModeChanged.emit(self.display_combo.currentData())
        )
        layout.addWidget(self.display_combo)

        self.events_checkbox = QtWidgets.QCheckBox("Show events")
        self.events_checkbox.setChecked(True)
        self.events_checkbox.toggled.connect(self.eventsVisibilityChanged.emit)
        layout.addWidget(self.events_checkbox)

        layout.addWidget(QtWidgets.QLabel("Save as:"))
        self.save_format_combo = QtWidgets.QComboBox()
        self.save_format_combo.addItem("Parquet (.parquet)", "parquet")
        self.save_format_combo.addItem("CSV (.csv)", "csv")
        self.save_format_combo.addItem("Excel (.xlsx)", "xlsx")
        layout.addWidget(self.save_format_combo)

        self.save_button = QtWidgets.QToolButton()
        self.save_button.setText("Save all 3")
        self.save_button.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.MenuButtonPopup)
        self.save_button.clicked.connect(lambda: self.saveRequested.emit("all"))

        save_menu = QtWidgets.QMenu(self.save_button)
        save_menu.addAction("Save corrected (diff, for website upload)", lambda: self.saveRequested.emit("diff"))
        save_menu.addAction("Save corrected series (full series, touched columns)", lambda: self.saveRequested.emit("series"))
        save_menu.addAction("Save full table (all columns, all rows)", lambda: self.saveRequested.emit("full"))
        save_menu.addAction("Save all 3", lambda: self.saveRequested.emit("all"))
        self.save_button.setMenu(save_menu)
        layout.addWidget(self.save_button)

        self.theme_button = QtWidgets.QPushButton("Dark mode")
        self.theme_button.setCheckable(True)
        self.theme_button.toggled.connect(self._on_theme_toggled)
        layout.addWidget(self.theme_button)

    def _on_theme_toggled(self, checked: bool) -> None:
        theme = "dark" if checked else "light"
        self.theme_button.setText("Light mode" if checked else "Dark mode")
        self.themeToggled.emit(theme)

    def set_theme_button_state(self, theme: str) -> None:
        self.theme_button.blockSignals(True)
        self.theme_button.setChecked(theme == "dark")
        self.theme_button.setText("Light mode" if theme == "dark" else "Dark mode")
        self.theme_button.blockSignals(False)

    def _on_variable_changed(self, text: str) -> None:
        if text and self.variable_combo.findText(text) >= 0:
            self.variableChanged.emit(text)

    def _on_time_axis_changed(self, text: str) -> None:
        if text:
            self.timeAxisChanged.emit(text)

    def set_variables(self, names: list[str]) -> None:
        self.variable_combo.blockSignals(True)
        self.variable_combo.clear()
        self.variable_combo.addItems(names)
        self.variable_combo.blockSignals(False)

    def set_time_axis_columns(self, names: list[str], current: str) -> None:
        self.time_axis_combo.blockSignals(True)
        self.time_axis_combo.clear()
        self.time_axis_combo.addItems(names)
        idx = self.time_axis_combo.findText(current)
        if idx >= 0:
            self.time_axis_combo.setCurrentIndex(idx)
        self.time_axis_combo.blockSignals(False)

    def set_events_enabled(self, enabled: bool) -> None:
        self.events_checkbox.setEnabled(enabled)

    def current_variable(self) -> str:
        return self.variable_combo.currentText()

    def display_mode(self) -> str:
        return self.display_combo.currentData()

    def save_format(self) -> str:
        return self.save_format_combo.currentData()
