"""File-based data provider (CSV/Excel), fully offline.

Reads a local file via :func:`app.utils.importers.read_table`, normalizes
each row to a plain dict, preserves the raw file via
:func:`app.utils.importers.preserve_raw_file`, and attaches source metadata.
This is the primary testable path (no network involved).
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

from app.providers.data.base import BaseDataProvider, ProviderResult
from app.utils.importers import _clean, _parse_date, preserve_raw_file, read_table


class CsvFileProvider(BaseDataProvider):
    """Reads a local CSV or Excel file into a :class:`ProviderResult`.

    Despite the name, this provider handles both CSV and Excel files via
    :func:`read_table` (which dispatches on file extension). An alias
    ``ExcelFileProvider`` is exported for callers that want to be explicit
    about the file type — both point at the same implementation.
    """

    name = "local-file"
    source_type = "file"

    def fetch(self, **params) -> ProviderResult:
        """Fetch records from a local file.

        Params:
            path / file_path: path to the .csv/.xlsx/.xls file (required).
            dataset_type: dataset type string (e.g. "etf_prices"), used for
                ``preserve_raw_file`` and attached to the result.
            data_date_column: optional column name to derive ``data_date``
                from (max value across rows, parsed via ``_parse_date``).
                If not provided (or absent), falls back to the file's mtime.
            preserve_raw: if False, skip copying the file into
                ``/data/raw/`` (default True).
            source_url: optional source URL to attach to the result.

        Returns:
            ProviderResult with ``records`` as a list of plain dicts (NaN
            values normalized to ``None`` via ``_clean``). On any error
            (missing file, unreadable format), returns an empty result with
            ``errors`` populated — never fabricates rows.
        """
        path = params.get("path") or params.get("file_path")
        dataset_type = params.get("dataset_type", "")
        source_url = params.get("source_url")
        data_date_column = params.get("data_date_column")
        preserve_raw = params.get("preserve_raw", True)

        result = ProviderResult(
            dataset_type=dataset_type,
            source_name=self.name,
            source_url=source_url,
            reliability_level="high",
        )

        if not path:
            result.errors.append("CsvFileProvider.fetch: missing required 'path' parameter")
            return result

        file_path = Path(path)
        if not file_path.exists():
            result.errors.append(f"CsvFileProvider.fetch: file not found: {file_path}")
            return result

        try:
            df = read_table(file_path)
        except Exception as exc:  # noqa: BLE001
            result.errors.append(f"CsvFileProvider.fetch: failed to read '{file_path}': {exc}")
            return result

        records: list[dict] = []
        for _, row in df.iterrows():
            record = {col: _clean(val) for col, val in row.items()}
            records.append(record)

        result.records = records

        # Determine data_date: from a designated column (max date across
        # rows), else fall back to the file's mtime.
        data_date: dt.date | None = None
        if data_date_column and data_date_column in df.columns:
            dates = [d for d in (_parse_date(v) for v in df[data_date_column]) if d is not None]
            if dates:
                data_date = max(dates)
        if data_date is None:
            mtime = file_path.stat().st_mtime
            data_date = dt.datetime.utcfromtimestamp(mtime).date()
        result.data_date = data_date

        if preserve_raw and dataset_type:
            try:
                preserve_raw_file(file_path, dataset_type)
            except Exception as exc:  # noqa: BLE001
                result.errors.append(f"CsvFileProvider.fetch: failed to preserve raw file: {exc}")

        if not records:
            result.errors.append(f"CsvFileProvider.fetch: file '{file_path}' contained no rows")

        return result


# Alias: same implementation handles .xlsx/.xls via read_table().
ExcelFileProvider = CsvFileProvider
