"""Sidebar panel: one button + auto-generated form per correction operation.

Adding a new correction = add a module to ``app/core/corrections`` that
registers a ``CorrectionOperation`` with ``@register_correction``. This
panel picks it up automatically (button + form), no UI change needed.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
from PyQt6 import QtCore, QtWidgets

from app.core.corrections import REGISTRY
from app.core.corrections.base import CorrectionOperation
from app.ui.widgets.param_form import ParamForm


class CorrectionPanel(QtWidgets.QWidget):
    """Lets the user arm a correction and apply it to the current selection."""

    # op_id, params
    applyRequested = QtCore.pyqtSignal(str, dict)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._forms: dict[str, ParamForm] = {}
        self._buttons: dict[str, QtWidgets.QPushButton] = {}
        self._armed_op: Optional[str] = None
        self._selection_mask: Optional[np.ndarray] = None

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel("<b>Corrections</b>"))

        self.auto_apply_checkbox = QtWidgets.QCheckBox("Apply automatically to selection")
        self.auto_apply_checkbox.setChecked(False)
        layout.addWidget(self.auto_apply_checkbox)

        buttons_widget = QtWidgets.QWidget()
        buttons_layout = QtWidgets.QGridLayout(buttons_widget)
        buttons_layout.setContentsMargins(0, 0, 0, 0)

        self._stack = QtWidgets.QStackedWidget()
        empty = QtWidgets.QWidget()
        self._stack.addWidget(empty)
        self._empty_index = 0

        for row, (op_id, op) in enumerate(REGISTRY.items()):
            btn = QtWidgets.QPushButton(op.label)
            btn.setCheckable(True)
            btn.clicked.connect(lambda _checked, oid=op_id: self._on_operation_clicked(oid))
            buttons_layout.addWidget(btn, row, 0)
            self._buttons[op_id] = btn

            form = ParamForm(op.param_schema)
            form.changed.connect(self._maybe_auto_apply)
            self._forms[op_id] = form
            self._stack.addWidget(form)

        layout.addWidget(buttons_widget)
        layout.addWidget(self._stack)

        self.apply_button = QtWidgets.QPushButton("Apply")
        self.apply_button.setEnabled(False)
        self.apply_button.clicked.connect(self._on_apply_clicked)
        layout.addWidget(self.apply_button)

        self.status_label = QtWidgets.QLabel("")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        layout.addStretch(1)

    # ------------------------------------------------------------------
    def armed_operation(self) -> Optional[CorrectionOperation]:
        if self._armed_op is None:
            return None
        return REGISTRY[self._armed_op]

    def current_params(self) -> dict:
        if self._armed_op is None:
            return {}
        return self._forms[self._armed_op].values()

    def set_selection_mask(self, mask: Optional[np.ndarray]) -> None:
        self._selection_mask = mask
        self._update_apply_enabled()
        self._maybe_auto_apply()

    def set_hover_value(self, value: Optional[float]) -> None:
        for form in self._forms.values():
            form.set_hover_value(value)

    # ------------------------------------------------------------------
    def _on_operation_clicked(self, op_id: str) -> None:
        btn = self._buttons[op_id]
        if not btn.isChecked():
            # user unarmed it
            if self._armed_op == op_id:
                self._armed_op = None
                self._stack.setCurrentIndex(self._empty_index)
            self._update_apply_enabled()
            return

        for other_id, other_btn in self._buttons.items():
            if other_id != op_id:
                other_btn.setChecked(False)

        self._armed_op = op_id
        self._stack.setCurrentWidget(self._forms[op_id])
        self._update_apply_enabled()
        self._maybe_auto_apply()

    def _update_apply_enabled(self) -> None:
        op = self.armed_operation()
        if op is None:
            self.apply_button.setEnabled(False)
            return
        if op.needs_selection:
            count = 0 if self._selection_mask is None else int(np.count_nonzero(self._selection_mask))
            self.apply_button.setEnabled(count > 0)
        else:
            self.apply_button.setEnabled(True)

    def _maybe_auto_apply(self) -> None:
        op = self.armed_operation()
        if op is None or not op.needs_selection:
            return
        if not self.auto_apply_checkbox.isChecked():
            return
        if self._selection_mask is None or not np.any(self._selection_mask):
            return
        self._emit_apply()

    def _on_apply_clicked(self) -> None:
        self._emit_apply()

    def _emit_apply(self) -> None:
        op = self.armed_operation()
        if op is None:
            return
        if op.needs_selection and (self._selection_mask is None or not np.any(self._selection_mask)):
            return
        self.applyRequested.emit(self._armed_op, self.current_params())

    def show_status(self, text: str) -> None:
        self.status_label.setText(text)
