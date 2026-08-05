"""Spike / freeze detection panel.

For each registered detector (see ``app.core.corrections.detection``), shows
a small parameter form, a "Detect" button, a result count, and a button to
turn the detected candidates into the current selection (which then flows
into the normal correction pipeline).
"""

from __future__ import annotations

from PyQt6 import QtCore, QtWidgets

from app.core.corrections import DETECTION_REGISTRY
from app.ui.widgets.param_form import ParamForm


class DetectionPanel(QtWidgets.QWidget):
    # op_id, params
    detectRequested = QtCore.pyqtSignal(str, dict)
    # op_id
    selectRequested = QtCore.pyqtSignal(str)
    clearRequested = QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel("<b>Detection</b>"))

        self._forms: dict[str, ParamForm] = {}
        self._count_labels: dict[str, QtWidgets.QLabel] = {}
        self._select_buttons: dict[str, QtWidgets.QPushButton] = {}

        for op_id, op in DETECTION_REGISTRY.items():
            group = QtWidgets.QGroupBox(op.label)
            group_layout = QtWidgets.QVBoxLayout(group)

            form = ParamForm(op.param_schema)
            self._forms[op_id] = form
            group_layout.addWidget(form)

            row1 = QtWidgets.QHBoxLayout()
            detect_btn = QtWidgets.QPushButton("Detect")
            detect_btn.clicked.connect(lambda _checked, oid=op_id: self._on_detect(oid))
            row1.addWidget(detect_btn)

            clear_btn = QtWidgets.QPushButton("Clear")
            clear_btn.clicked.connect(lambda _checked, oid=op_id: self._on_clear(oid))
            row1.addWidget(clear_btn)
            group_layout.addLayout(row1)

            select_btn = QtWidgets.QPushButton("Select candidates")
            select_btn.setEnabled(False)
            select_btn.clicked.connect(lambda _checked, oid=op_id: self.selectRequested.emit(oid))
            self._select_buttons[op_id] = select_btn
            group_layout.addWidget(select_btn)

            count_label = QtWidgets.QLabel("Candidates: 0")
            self._count_labels[op_id] = count_label
            group_layout.addWidget(count_label)

            layout.addWidget(group)

        layout.addStretch(1)

    def _on_detect(self, op_id: str) -> None:
        self.detectRequested.emit(op_id, self._forms[op_id].values())

    def _on_clear(self, op_id: str) -> None:
        self.set_count(op_id, 0)
        self.clearRequested.emit(op_id)

    def set_count(self, op_id: str, count: int) -> None:
        self._count_labels[op_id].setText(f"Candidates: {count}")
        self._select_buttons[op_id].setEnabled(count > 0)
