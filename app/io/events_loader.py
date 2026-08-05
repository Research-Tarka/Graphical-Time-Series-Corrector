"""Load and filter an "events" table (punctual or period annotations)."""

from __future__ import annotations

from pathlib import Path

import polars as pl

REQUIRED_COLUMNS = ["start"]


def load_events(path: Path) -> pl.DataFrame:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".parquet":
        df = pl.read_parquet(path)
    elif suffix == ".csv":
        df = pl.read_csv(path)
    elif suffix in (".xlsx", ".xls"):
        df = pl.read_excel(path, engine="fastexcel")
    else:
        raise ValueError(f"Unsupported file format: {suffix}")

    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            raise ValueError(f"The events file must contain a '{col}' column")

    df = df.with_columns(_to_datetime_expr(df, "start").alias("_start_dt"))
    if "end" in df.columns:
        df = df.with_columns(_to_datetime_expr(df, "end").alias("_end_dt"))
    else:
        df = df.with_columns(pl.lit(None, dtype=pl.Datetime).alias("_end_dt"))

    df = df.with_columns(
        (pl.col("_end_dt").is_null() | (pl.col("_end_dt") == pl.col("_start_dt"))).alias("_is_punctual")
    )
    return df


def _to_datetime_expr(df: pl.DataFrame, col: str) -> pl.Expr:
    dtype = df.schema[col]
    if isinstance(dtype, (pl.Datetime, pl.Date)):
        return pl.col(col).cast(pl.Datetime)
    return pl.col(col).cast(pl.Utf8).str.to_datetime(strict=False)


def filter_events(df: pl.DataFrame, table_name: str) -> pl.DataFrame:
    """Keep events that apply to ``table_name`` (or to every table, "*")."""

    if "table" not in df.columns:
        return df
    return df.filter((pl.col("table") == "*") | (pl.col("table") == table_name))
