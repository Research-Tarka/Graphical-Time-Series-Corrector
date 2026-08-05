"""Small toolbar to read/set the plot's Y-axis range manually."""

from __future__ import annotations

from PyQt6 import QtCore, QtWidgets


class YRangeControl(QtWidgets.QWidget):
    """Lets the user type a custom Y min/max, or re-fit to the data."""

    rangeApplied = QtCore.pyqtSignal(float, float)
    autoRequested = QtCore.pyqtSignal()
    backRequested = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(QtWidgets.QLabel("Y range:"))

        self.min_spin = QtWidgets.QDoubleSpinBox()
        self.max_spin = QtWidgets.QDoubleSpinBox()
        for spin in (self.min_spin, self.max_spin):
            spin.setRange(-1e12, 1e12)
            spin.setDecimals(4)
            spin.setMinimumWidth(100)
            layout.addWidget(spin)

        self.apply_button = QtWidgets.QPushButton("Apply")
        self.apply_button.clicked.connect(self._on_apply)
        layout.addWidget(self.apply_button)

        self.auto_button = QtWidgets.QPushButton("Auto (data)")
        self.auto_button.clicked.connect(self.autoRequested.emit)
        layout.addWidget(self.auto_button)

        self.back_button = QtWidgets.QPushButton("Previous view")
        self.back_button.setEnabled(False)
        self.back_button.clicked.connect(self.backRequested.emit)
        layout.addWidget(self.back_button)

        layout.addStretch(1)

    def set_back_enabled(self, enabled: bool) -> None:
        self.back_button.setEnabled(enabled)

    def _on_apply(self) -> None:
        ymin, ymax = self.min_spin.value(), self.max_spin.value()
        if ymin >= ymax:
            return
        self.rangeApplied.emit(ymin, ymax)

    def set_range(self, ymin: float, ymax: float) -> None:
        for spin, value in ((self.min_spin, ymin), (self.max_spin, ymax)):
            spin.blockSignals(True)
            spin.setValue(value)
            spin.blockSignals(False)
