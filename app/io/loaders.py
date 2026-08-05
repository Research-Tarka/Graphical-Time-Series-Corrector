"""Load a data table (csv/xlsx/parquet) as a Polars LazyFrame.

Only the timestamp column is materialized at load time; variable columns are
read on demand (see ``DataSession.open_variable``).
"""

from __future__ import annotations

from pathlib import Path

import polars as pl

# Column names checked (case-insensitive) to find the timestamp column,
# in order of preference.
TIMESTAMP_CANDIDATES = [
    "TIMESTAMP_LOCAL",
    "TIMESTAMP",
    "DATETIME",
    "DATE_TIME",
    "DATE",
    "TIME",
]


def load_table_lazy(path: Path) -> tuple[pl.LazyFrame, dict, str]:
    """Return ``(lazy_frame, schema, timestamp_col)`` for ``path``."""

    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".parquet":
        lf = pl.scan_parquet(path)
    elif suffix == ".csv":
        lf = pl.scan_csv(path, try_parse_dates=True)
    elif suffix in (".xlsx", ".xls"):
        lf = pl.read_excel(path, engine="fastexcel").lazy()
    else:
        raise ValueError(f"Unsupported file format: {suffix}")

    schema = lf.collect_schema()
    timestamp_col = _detect_timestamp_col(schema)
    return lf, schema, timestamp_col


def _detect_timestamp_col(schema: pl.Schema) -> str:
    names = list(schema.names())
    lower_map = {n.lower(): n for n in names}

    for candidate in TIMESTAMP_CANDIDATES:
        match = lower_map.get(candidate.lower())
        if match is not None:
            return match

    for name, dtype in schema.items():
        if isinstance(dtype, (pl.Datetime, pl.Date)):
            return name

    return names[0]
