"""Shared helpers for CSV/Excel import scripts.

Provides:
- ``_clean`` / ``_parse_date``: value-normalization helpers (used by seed.py too).
- ``read_table``: read a .csv/.xlsx/.xls file into a pandas DataFrame, with
  encoding fallback for CSV files (utf-8, utf-8-sig, cp950/big5).
- ``preserve_raw_file``: copy the source file into /data/raw/<dataset_type>/
  with a timestamped name, returning the destination path.
- ``ImportSummary``: dataclass tracking rows read/inserted/skipped/errors,
  with a ``.print_report()`` helper.
"""

from __future__ import annotations

import datetime as dt
import shutil
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

RAW_DATA_ROOT = Path("/data/raw")

# Encodings to try, in order, when reading a CSV file.
CSV_ENCODINGS = ["utf-8", "utf-8-sig", "cp950", "big5"]


def _parse_date(value):
    """Parse a value into a ``datetime.date``, or ``None`` if empty/NaN."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, str) and not value.strip():
        return None
    if isinstance(value, dt.date):
        return value
    return pd.to_datetime(value).date()


def _clean(value):
    """Convert NaN/empty-string to ``None``, otherwise return as-is."""
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    if isinstance(value, str) and value.strip() == "":
        return None
    return value


def _num(value):
    """Convert a (possibly string) value to a native Python ``float``.

    Returns ``None`` for empty/NaN/None values. Strips surrounding
    whitespace and thousands separators so values read with ``dtype=str``
    can be safely passed to numeric (psycopg2-adaptable) model fields.
    """
    value = _clean(value)
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip().replace(",", "")
        if value == "":
            return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def read_table(path: Path | str) -> pd.DataFrame:
    """Read a CSV or Excel file into a DataFrame.

    For CSV files, tries a sequence of encodings (utf-8, utf-8-sig, cp950,
    big5). If all fail, raises a ``ValueError`` naming the file and the
    encodings that were tried.
    """
    path = Path(path)
    suffix = path.suffix.lower()

    if suffix in (".xlsx", ".xls"):
        return pd.read_excel(path, dtype=str)

    if suffix == ".csv":
        last_error: Exception | None = None
        for encoding in CSV_ENCODINGS:
            try:
                return pd.read_csv(path, encoding=encoding, dtype=str, keep_default_na=False)
            except (UnicodeDecodeError, UnicodeError) as exc:
                last_error = exc
                continue
        raise ValueError(
            f"Could not decode '{path}' using any of the tried encodings: "
            f"{', '.join(CSV_ENCODINGS)}. Last error: {last_error}"
        )

    raise ValueError(
        f"Unsupported file type '{suffix}' for '{path}'. "
        "Expected .csv, .xlsx, or .xls."
    )


def preserve_raw_file(path: Path | str, dataset_type: str) -> Path:
    """Copy ``path`` into ``/data/raw/<dataset_type>/<timestamp>__<name>``.

    Creates the destination directory if needed. Returns the destination path.
    """
    path = Path(path)
    dest_dir = RAW_DATA_ROOT / dataset_type
    dest_dir.mkdir(parents=True, exist_ok=True)

    timestamp = dt.datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    dest_path = dest_dir / f"{timestamp}__{path.name}"
    shutil.copy2(path, dest_path)
    return dest_path


@dataclass
class ImportSummary:
    """Tracks the results of an import run."""

    file_path: str
    dataset_type: str
    rows_read: int = 0
    inserted: int = 0
    skipped_existing: int = 0
    skipped_invalid: int = 0
    errors: list[str] = field(default_factory=list)
    dry_run: bool = False

    def print_report(self) -> None:
        print("=" * 60)
        print(f"Import summary: {self.dataset_type}")
        print(f"  file:             {self.file_path}")
        if self.dry_run:
            print("  mode:             DRY RUN (no writes performed)")
        print(f"  rows read:        {self.rows_read}")
        print(f"  inserted:         {self.inserted}")
        print(f"  skipped (exists): {self.skipped_existing}")
        print(f"  skipped (invalid):{self.skipped_invalid}")
        print(f"  errors:           {len(self.errors)}")
        for err in self.errors:
            print(f"    - {err}")
        print("=" * 60)
