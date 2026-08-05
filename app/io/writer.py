"""Write corrected variables back to ``<basename>_corrected.parquet``."""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import polars as pl


def corrected_path_for(original_path: Path, suffix: str = "_corrected", fmt: str = "parquet") -> Path:
    original_path = Path(original_path)
    return original_path.with_name(original_path.stem + suffix + "." + fmt)


def _write_dataframe(result: pl.DataFrame, corrected_path: Path, fmt: str) -> None:
    if fmt == "parquet":
        tmp_path = corrected_path.with_suffix(".parquet.tmp")
        result.write_parquet(tmp_path)
        os.replace(tmp_path, corrected_path)
    elif fmt == "csv":
        tmp_path = corrected_path.with_suffix(".csv.tmp")
        result.write_csv(tmp_path)
        os.replace(tmp_path, corrected_path)
    elif fmt == "xlsx":
        result.write_excel(corrected_path)
    else:
        raise ValueError(f"Unsupported output format: {fmt}")


def save_corrected(
    original_path: Path,
    edited: dict[str, np.ndarray],
    timestamp_col: str,
    n_rows: int,
    fmt: str = "parquet",
) -> Path:
    """Merge ``edited`` columns into ``<basename>_corrected_full.<fmt>``.

    Full-table mode: rewrites every column and every row every time (today's
    original/only behavior, kept as save mode "full"). If the output file
    already exists, it is used as the source (so previously corrected
    columns are preserved); otherwise the original file is the source. Only
    the columns in ``edited`` are replaced. The result is written in ``fmt``
    (``parquet``, ``csv`` or ``xlsx``), atomically for parquet/csv (write to
    a temp file then replace).
    """

    original_path = Path(original_path)
    corrected_path = corrected_path_for(original_path, "_corrected_full", fmt)

    source_path = corrected_path if corrected_path.exists() else original_path
    lf = _scan_any(source_path)

    height = lf.select(pl.len()).collect().item()
    if height != n_rows:
        raise ValueError(
            f"The number of rows in the source file ({height}) does not match "
            f"the loaded data ({n_rows}). Aborting save."
        )

    new_columns = [pl.Series(name, values) for name, values in edited.items()]
    result = lf.with_columns(new_columns).collect()

    _write_dataframe(result, corrected_path, fmt)
    return corrected_path


def save_corrected_diff(
    original_path: Path,
    touched: dict[str, tuple[np.ndarray, np.ndarray]],
    timestamp_col: str,
    timestamps: np.ndarray,
    fmt: str = "parquet",
) -> Path:
    """Write ``<basename>_corrected.<fmt>``: this is the file meant to be
    uploaded to the website's manual-correction endpoint.

    Contains only the rows where at least one touched variable's corrected
    value actually differs from its raw value (NaN-vs-NaN at the same cell is
    NOT a change). Columns are the timestamp column plus the touched variable
    names; a variable that didn't change at an included row is written as NaN
    at that row (the website's own noop filter drops any cell that equals its
    raw value or is NaN-over-raw-NaN, so leaving it NaN there is safe and
    never mis-tags an unrelated column as corrected).

    ``touched`` maps variable name -> (raw, corrected) arrays, both full
    length (same length as ``timestamps``).
    """

    original_path = Path(original_path)
    corrected_path = corrected_path_for(original_path, "_corrected", fmt)

    if not touched:
        raise ValueError("No touched variables to save.")

    changed_by_var: dict[str, np.ndarray] = {}
    union_changed = np.zeros(timestamps.shape, dtype=bool)
    for name, (raw, corrected) in touched.items():
        changed = ~np.isclose(raw, corrected, atol=1e-9, rtol=1e-6, equal_nan=True)
        changed_by_var[name] = changed
        union_changed |= changed

    columns: dict[str, np.ndarray] = {timestamp_col: timestamps[union_changed]}
    for name, (_, corrected) in touched.items():
        col_values = corrected[union_changed].copy()
        # Rows where THIS variable didn't change (but another touched
        # variable did) are written as NaN, not the unchanged raw value.
        col_values[~changed_by_var[name][union_changed]] = np.nan
        columns[name] = col_values

    result = pl.DataFrame(columns)
    _write_dataframe(result, corrected_path, fmt)
    return corrected_path


def save_corrected_series(
    original_path: Path,
    touched: dict[str, np.ndarray],
    timestamp_col: str,
    timestamps: np.ndarray,
    fmt: str = "parquet",
) -> Path:
    """Write ``<basename>_corrected_serie.<fmt>``: the full series (every
    row) for only the touched variable(s), meant for working on the series
    directly. Every value (changed or not) is written as a plain
    replacement -- the website's own raw-comparison filter (not this
    function) is what keeps cells equal to raw from being auto-tagged as
    corrected, so no special marker is needed here.
    """

    original_path = Path(original_path)
    corrected_path = corrected_path_for(original_path, "_corrected_serie", fmt)

    if not touched:
        raise ValueError("No touched variables to save.")

    columns: dict[str, np.ndarray] = {timestamp_col: timestamps}
    columns.update(touched)
    result = pl.DataFrame(columns)
    _write_dataframe(result, corrected_path, fmt)
    return corrected_path


def _scan_any(path: Path) -> pl.LazyFrame:
    suffix = path.suffix.lower()
    if suffix == ".parquet":
        return pl.scan_parquet(path)
    if suffix == ".csv":
        return pl.scan_csv(path, try_parse_dates=True)
    if suffix in (".xlsx", ".xls"):
        return pl.read_excel(path, engine="fastexcel").lazy()
    raise ValueError(f"Unsupported file format: {suffix}")
