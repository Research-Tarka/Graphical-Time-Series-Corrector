"""Per-variable undo stack for corrections."""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Optional

import numpy as np


@dataclass
class UndoEntry:
    indices: np.ndarray
    old_values: np.ndarray
    new_values: np.ndarray
    op_id: str
    op_label: str
    when: datetime.datetime


class UndoStack:
    def __init__(self) -> None:
        self.entries: list[UndoEntry] = []
        # (position, entry) pairs removed via `remove_at`, restorable via `restore_last_removed`.
        self._removed: list[tuple[int, UndoEntry]] = []

    def push(self, entry: UndoEntry) -> None:
        self.entries.append(entry)

    def pop(self) -> Optional[UndoEntry]:
        if not self.entries:
            return None
        return self.entries.pop()

    def remove_at(self, position: int) -> Optional[UndoEntry]:
        if not 0 <= position < len(self.entries):
            return None
        entry = self.entries.pop(position)
        self._removed.append((position, entry))
        return entry

    def restore_last_removed(self) -> Optional[tuple[int, UndoEntry]]:
        if not self._removed:
            return None
        position, entry = self._removed.pop()
        position = min(position, len(self.entries))
        self.entries.insert(position, entry)
        return position, entry

    @property
    def can_restore(self) -> bool:
        return bool(self._removed)

    def clear(self) -> None:
        self.entries.clear()
        self._removed.clear()

    def __len__(self) -> int:
        return len(self.entries)

    def __bool__(self) -> bool:
        return bool(self.entries)
