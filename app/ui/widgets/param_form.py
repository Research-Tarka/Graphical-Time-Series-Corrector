"""Auto-generate a small form from a list of ParamSpec.

Used by the correction and detection panels so that adding a new operation
with a new ``param_schema`` does not require any new UI code.
"""

from __future__ import annotations

from typing import Any

from PyQt6 import QtCore, QtWidgets

from app.core.corrections.base import ParamSpec


class OptionalFloatField(QtWidgets.QWidget):
    """Checkbox + spin box: unchecked == None."""

    valueChanged = QtCore.pyqtSignal()

    def __init__(self, default: float | None = None, parent=None):
        super().__init__(parent)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.checkbox = QtWidgets.QCheckBox()
        self.spin = QtWidgets.QDoubleSpinBox()
        self.spin.setRange(-1e12, 1e12)
        self.spin.setDecimals(6)

        if default is None:
            self.checkbox.setChecked(False)
            self.spin.setEnabled(False)
        else:
            self.checkbox.setChecked(True)
            self.spin.setValue(default)

        self.checkbox.toggled.connect(self.spin.setEnabled)
        self.checkbox.toggled.connect(self.valueChanged.emit)
        self.spin.valueChanged.connect(self.valueChanged.emit)

        layout.addWidget(self.checkbox)
        layout.addWidget(self.spin)

    def value(self) -> float | None:
        if not self.checkbox.isChecked():
            return None
        return self.spin.value()


class ExprField(QtWidgets.QWidget):
    """A QLineEdit for a math expression + a button to insert a value from the plot."""

    changed = QtCore.pyqtSignal()

    def __init__(self, default: str = "", parent=None):
        super().__init__(parent)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.line_edit = QtWidgets.QLineEdit()
        self.line_edit.setText(default)
        self.line_edit.setPlaceholderText(
            "ex: x + 1, x**2, np.exp(x), np.log10(x), (x - 3) / 2"
        )
        self.line_edit.textChanged.connect(self.changed.emit)
        layout.addWidget(self.line_edit)

        self.insert_button = QtWidgets.QPushButton("Insert hovered value from the plot")
        self.insert_button.setEnabled(False)
        self.insert_button.clicked.connect(self._on_insert_clicked)
        layout.addWidget(self.insert_button)

        self._hover_value: float | None = None

    def set_hover_value(self, value: float | None) -> None:
        self._hover_value = value
        self.insert_button.setEnabled(value is not None)

    def _on_insert_clicked(self) -> None:
        if self._hover_value is None:
            return
        text = f"{self._hover_value:.6g}"
        self.line_edit.insert(text)

    def text(self) -> str:
        return self.line_edit.text()


class ParamForm(QtWidgets.QWidget):
    """A QFormLayout built from a list of ParamSpec, with conditional rows."""

    changed = QtCore.pyqtSignal()

    def __init__(self, param_schema: list[ParamSpec], parent=None):
        super().__init__(parent)
        self._schema = param_schema
        self._widgets: dict[str, QtWidgets.QWidget] = {}
        self._rows: dict[str, tuple[QtWidgets.QLabel, QtWidgets.QWidget]] = {}

        layout = QtWidgets.QFormLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        for spec in param_schema:
            widget = self._build_widget(spec)
            self._widgets[spec.name] = widget
            label = QtWidgets.QLabel(spec.label)
            layout.addRow(label, widget)
            self._rows[spec.name] = (label, widget)
            self._connect_changed(spec, widget)

        self._update_visibility()

    # ------------------------------------------------------------------
    def _build_widget(self, spec: ParamSpec) -> QtWidgets.QWidget:
        if spec.type == "float":
            w = QtWidgets.QDoubleSpinBox()
            w.setRange(-1e12, 1e12)
            w.setDecimals(6)
            w.setValue(float(spec.default) if spec.default is not None else 0.0)
            return w
        if spec.type == "int":
            w = QtWidgets.QSpinBox()
            w.setRange(-10**9, 10**9)
            w.setValue(int(spec.default) if spec.default is not None else 0)
            return w
        if spec.type == "optional_float":
            return OptionalFloatField(spec.default)
        if spec.type == "expr":
            return ExprField(str(spec.default) if spec.default is not None else "")
        if spec.type == "enum":
            w = QtWidgets.QComboBox()
            for value, label in spec.choices or []:
                w.addItem(label, value)
            if spec.default is not None:
                idx = w.findData(spec.default)
                if idx >= 0:
                    w.setCurrentIndex(idx)
            return w
        # "str" / "expr"
        w = QtWidgets.QLineEdit()
        w.setText(str(spec.default) if spec.default is not None else "")
        return w

    def _connect_changed(self, spec: ParamSpec, widget: QtWidgets.QWidget) -> None:
        if isinstance(widget, QtWidgets.QDoubleSpinBox):
            widget.valueChanged.connect(self.changed.emit)
        elif isinstance(widget, QtWidgets.QSpinBox):
            widget.valueChanged.connect(self.changed.emit)
        elif isinstance(widget, QtWidgets.QComboBox):
            widget.currentIndexChanged.connect(self._on_combo_changed)
        elif isinstance(widget, QtWidgets.QLineEdit):
            widget.textChanged.connect(self.changed.emit)
        elif isinstance(widget, OptionalFloatField):
            widget.valueChanged.connect(self.changed.emit)
        elif isinstance(widget, ExprField):
            widget.changed.connect(self.changed.emit)

    def _on_combo_changed(self, _index: int) -> None:
        self._update_visibility()
        self.changed.emit()

    def _update_visibility(self) -> None:
        for spec in self._schema:
            if spec.depends_on is None:
                continue
            other_name, allowed_values = spec.depends_on
            other_widget = self._widgets.get(other_name)
            current = self._value_of(other_widget) if other_widget is not None else None
            visible = current in allowed_values
            label, widget = self._rows[spec.name]
            label.setVisible(visible)
            widget.setVisible(visible)

    @staticmethod
    def _value_of(widget: QtWidgets.QWidget) -> Any:
        if isinstance(widget, QtWidgets.QComboBox):
            return widget.currentData()
        if isinstance(widget, (QtWidgets.QDoubleSpinBox, QtWidgets.QSpinBox)):
            return widget.value()
        if isinstance(widget, QtWidgets.QLineEdit):
            return widget.text()
        if isinstance(widget, OptionalFloatField):
            return widget.value()
        if isinstance(widget, ExprField):
            return widget.text()
        return None

    # ------------------------------------------------------------------
    def values(self) -> dict[str, Any]:
        return {name: self._value_of(widget) for name, widget in self._widgets.items()}

    def set_hover_value(self, value: float | None) -> None:
        """Forward the currently hovered plot value to any ExprField in this form."""

        for widget in self._widgets.values():
            if isinstance(widget, ExprField):
                widget.set_hover_value(value)
