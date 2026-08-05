"""Central application state: loaded table, open variables, selection, events."""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import Optional

import numpy as np
import polars as pl

from app.io.loaders import load_table_lazy
from app.io.writer import save_corrected, save_corrected_diff, save_corrected_series
from app.io.events_loader import load_events, filter_events
from .history import UndoEntry, UndoStack
from .selection import SelectionState

EPOCH = np.datetime64("1970-01-01T00:00:00", "ns")


class VariableState:
    """Raw and corrected arrays + undo history for one variable."""

    def __init__(self, name: str, raw: np.ndarray, corrected: np.ndarray):
        self.name = name
        self.raw = raw
        self.corrected = corrected.copy()
        self.history = UndoStack()
        self.is_dirty = False
        # True where the user explicitly deleted this point this session, as
        # opposed to a value that was always missing in raw. UI/history
        # display only -- export correctness never depends on this (a
        # deletion is already detected as a raw-vs-corrected difference).
        self.deleted = np.zeros(raw.shape, dtype=bool)


class DataSession:
    def __init__(self) -> None:
        self.source_path: Optional[Path] = None
        self.lazy_frame: Optional[pl.LazyFrame] = None
        self.schema: Optional[pl.Schema] = None
        self.timestamp_col: Optional[str] = None
        self.table_name: str = ""

        self.timestamps: Optional[np.ndarray] = None  # datetime64[ns]
        self.timestamps_epoch: Optional[np.ndarray] = None  # float64 seconds

        self.variables: dict[str, VariableState] = {}
        self.active_variable: Optional[str] = None

        self.events: Optional[pl.DataFrame] = None
        self.events_for_table: Optional[pl.DataFrame] = None

        self.selection = SelectionState()
        self.display_mode: str = "both"  # "raw" | "corrected" | "both"

        self.corrected_path: Optional[Path] = None

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------
    def load_table(self, path: Path) -> None:
        self.source_path = Path(path)
        self.lazy_frame, self.schema, self.timestamp_col = load_table_lazy(self.source_path)
        self.table_name = self.source_path.stem

        self._load_timestamps(self.timestamp_col)

        self.variables.clear()
        self.active_variable = None
        self.selection.clear()

        self.corrected_path = None

        if self.events is not None:
            self.events_for_table = filter_events(self.events, self.table_name)

    def load_events(self, path: Path) -> None:
        self.events = load_events(Path(path))
        if self.table_name:
            self.events_for_table = filter_events(self.events, self.table_name)

    def set_timestamp_column(self, name: str) -> None:
        """Switch which column is used as the time axis (X axis)."""

        if name == self.timestamp_col:
            return
        self._load_timestamps(name)
        self.timestamp_col = name
        self.variables.clear()
        self.active_variable = None
        self.selection.clear()

    def _load_timestamps(self, name: str) -> None:
        series = self.lazy_frame.select(name).collect().to_series()
        if series.dtype in (pl.Datetime, pl.Date) or isinstance(series.dtype, (pl.Datetime, pl.Date)):
            ts = series.cast(pl.Datetime).to_numpy()
        elif series.dtype == pl.Utf8:
            ts = series.str.to_datetime(strict=False).to_numpy()
        else:
            # Numeric column: interpret as Unix epoch seconds.
            ts = (series.cast(pl.Float64) * 1e9).cast(pl.Int64).to_numpy().astype("datetime64[ns]")

        self.timestamps = ts.astype("datetime64[ns]")
        self.timestamps_epoch = (self.timestamps - EPOCH) / np.timedelta64(1, "s")

    # ------------------------------------------------------------------
    # Variables
    # ------------------------------------------------------------------
    @property
    def column_names(self) -> list[str]:
        if self.schema is None:
            return []
        return list(self.schema.names())

    @property
    def variable_names(self) -> list[str]:
        if self.schema is None:
            return []
        return [c for c in self.schema.names() if c != self.timestamp_col]

    def open_variable(self, name: str) -> VariableState:
        if name in self.variables:
            self.active_variable = name
            return self.variables[name]

        raw = (
            self.lazy_frame.select(name)
            .collect()
            .to_series()
            .cast(pl.Float64, strict=False)
            .to_numpy()
        )

        vs = VariableState(name, raw, raw)
        self.variables[name] = vs
        self.active_variable = name
        return vs

    @property
    def active(self) -> Optional[VariableState]:
        if self.active_variable is None:
            return None
        return self.variables.get(self.active_variable)

    # ------------------------------------------------------------------
    # Corrections / undo
    # ------------------------------------------------------------------
    def apply_correction(self, op_id: str, op_label: str, result) -> None:
        vs = self.active
        if vs is None or result.indices.size == 0:
            return
        old_values = vs.corrected[result.indices].copy()
        new_values = np.asarray(result.new_values)
        vs.history.push(
            UndoEntry(result.indices.copy(), old_values, new_values.copy(), op_id, op_label, datetime.datetime.now())
        )
        vs.corrected[result.indices] = result.new_values
        vs.deleted[result.indices] = op_id == "delete"
        vs.is_dirty = True

    def undo(self) -> Optional[UndoEntry]:
        vs = self.active
        if vs is None:
            return None
        entry = vs.history.pop()
        if entry is None:
            return None
        vs.corrected[entry.indices] = entry.old_values
        vs.is_dirty = True
        return entry

    def _replay_history(self, vs: VariableState) -> None:
        """Recompute `corrected` from `raw` by re-applying all remaining history entries in order."""

        vs.corrected = vs.raw.copy()
        vs.deleted = np.zeros(vs.raw.shape, dtype=bool)
        for entry in vs.history.entries:
            vs.corrected[entry.indices] = entry.new_values
            vs.deleted[entry.indices] = entry.op_id == "delete"

    def delete_history_entry(self, position: int) -> Optional[UndoEntry]:
        vs = self.active
        if vs is None:
            return None
        entry = vs.history.remove_at(position)
        if entry is None:
            return None
        self._replay_history(vs)
        vs.is_dirty = True
        return entry

    def restore_deleted_entry(self) -> Optional[UndoEntry]:
        vs = self.active
        if vs is None:
            return None
        restored = vs.history.restore_last_removed()
        if restored is None:
            return None
        self._replay_history(vs)
        vs.is_dirty = True
        return restored[1]

    def reset_to_raw(self) -> None:
        vs = self.active
        if vs is None:
            return
        vs.corrected = vs.raw.copy()
        vs.deleted = np.zeros(vs.raw.shape, dtype=bool)
        vs.history.clear()
        vs.is_dirty = True

    # ------------------------------------------------------------------
    # Saving
    # ------------------------------------------------------------------
    def dirty_variables(self) -> dict[str, np.ndarray]:
        return {name: vs.corrected for name, vs in self.variables.items() if vs.is_dirty}

    def save(self, mode: str = "full", fmt: str = "parquet") -> Optional[Path]:
        """Save corrections. ``mode``:

        - "diff": ``_corrected.<fmt>`` -- only genuinely-changed rows, only
          touched columns. This is the file meant to be uploaded to the
          website's manual-correction endpoint.
        - "series": ``_corrected_serie.<fmt>`` -- full series (all rows),
          only touched columns.
        - "full": ``_corrected_full.<fmt>`` -- today's original behavior,
          full table (all rows, all columns).
        """

        edited = self.dirty_variables()
        if not edited:
            return None

        if mode == "diff":
            touched = {name: (vs.raw, vs.corrected) for name, vs in self.variables.items() if vs.is_dirty}
            path = save_corrected_diff(self.source_path, touched, self.timestamp_col, self.timestamps, fmt=fmt)
        elif mode == "series":
            path = save_corrected_series(self.source_path, edited, self.timestamp_col, self.timestamps, fmt=fmt)
        elif mode == "full":
            path = save_corrected(self.source_path, edited, self.timestamp_col, len(self.timestamps), fmt=fmt)
        else:
            raise ValueError(f"Unknown save mode: {mode}")

        for vs in self.variables.values():
            vs.is_dirty = False
        self.corrected_path = path
        return path

    def save_all(self, fmt: str = "parquet") -> dict[str, Optional[Path]]:
        """Write all 3 outputs (diff, series, full) from the same dirty
        snapshot, then clear dirty flags once at the end."""

        edited = self.dirty_variables()
        if not edited:
            return {}

        touched = {name: (vs.raw, vs.corrected) for name, vs in self.variables.items() if vs.is_dirty}
        paths = {
            "diff": save_corrected_diff(self.source_path, touched, self.timestamp_col, self.timestamps, fmt=fmt),
            "series": save_corrected_series(self.source_path, edited, self.timestamp_col, self.timestamps, fmt=fmt),
            "full": save_corrected(self.source_path, edited, self.timestamp_col, len(self.timestamps), fmt=fmt),
        }

        for vs in self.variables.values():
            vs.is_dirty = False
        self.corrected_path = paths["full"]
        return paths
