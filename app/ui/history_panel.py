"""Undo history for the active variable."""

from __future__ import annotations

from PyQt6 import QtCore, QtWidgets

from app.core.history import UndoStack


class HistoryPanel(QtWidgets.QWidget):
    undoRequested = QtCore.pyqtSignal()
    resetRequested = QtCore.pyqtSignal()
    deleteRequested = QtCore.pyqtSignal(int)
    restoreDeletedRequested = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel("<b>History</b>"))

        self.list_widget = QtWidgets.QListWidget()
        self.list_widget.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.list_widget)

        row = QtWidgets.QHBoxLayout()
        self.undo_button = QtWidgets.QPushButton("Undo last correction")
        self.undo_button.clicked.connect(self.undoRequested.emit)
        row.addWidget(self.undo_button)
        layout.addLayout(row)

        row2 = QtWidgets.QHBoxLayout()
        self.delete_button = QtWidgets.QPushButton("Delete selected correction")
        self.delete_button.setEnabled(False)
        self.delete_button.clicked.connect(self._on_delete_clicked)
        row2.addWidget(self.delete_button)

        self.restore_deleted_button = QtWidgets.QPushButton("Restore deleted correction")
        self.restore_deleted_button.setEnabled(False)
        self.restore_deleted_button.clicked.connect(self.restoreDeletedRequested.emit)
        row2.addWidget(self.restore_deleted_button)
        layout.addLayout(row2)

        self.reset_button = QtWidgets.QPushButton("Revert to raw data")
        self.reset_button.clicked.connect(self.resetRequested.emit)
        layout.addWidget(self.reset_button)

    def refresh(self, history: UndoStack | None) -> None:
        self.list_widget.clear()
        if history is None:
            self.undo_button.setEnabled(False)
            self.delete_button.setEnabled(False)
            self.restore_deleted_button.setEnabled(False)
            return
        for entry in history.entries:
            text = f"{entry.when:%H:%M:%S} - {entry.op_label} ({entry.indices.size} pts)"
            self.list_widget.addItem(text)
        self.list_widget.scrollToBottom()
        self.undo_button.setEnabled(bool(history))
        self.delete_button.setEnabled(False)
        self.restore_deleted_button.setEnabled(history.can_restore)

    def _on_selection_changed(self) -> None:
        self.delete_button.setEnabled(bool(self.list_widget.selectedItems()))

    def _on_delete_clicked(self) -> None:
        row = self.list_widget.currentRow()
        if row < 0:
            return
        self.deleteRequested.emit(row)
