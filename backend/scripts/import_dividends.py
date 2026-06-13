"""Import ETF dividend data into etf_dividends.

Usage:
    python -m scripts.import_dividends <path-to-file> [options]

Expected columns (see data/samples/0050_dividends.csv):
    etf_symbol, ex_dividend_date, payment_date, dividend_amount,
    dividend_yield, source_name, source_url

Unique key: (etf_symbol, ex_dividend_date, source_name) (skips rows that already exist).

If `etf_symbol` is not present as a column, pass --etf-symbol.
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

from app.core.database import SessionLocal
from app.models import EtfDividend
from app.utils.data_quality import run_and_report
from app.utils.importers import ImportSummary, _clean, _num, _parse_date, preserve_raw_file, read_table

DATASET_TYPE = "etf_dividends"


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import ETF dividend data.")
    parser.add_argument("file", help="Path to CSV or Excel file")
    parser.add_argument("--etf-symbol", default=None, help="Fallback etf_symbol if column missing")
    parser.add_argument("--source-name", default=None, help="Fallback source_name")
    parser.add_argument("--source-url", default=None, help="Fallback source_url")
    parser.add_argument(
        "--dry-run", action="store_true", help="Parse & validate without writing"
    )
    return parser.parse_args(argv)


def run(args: argparse.Namespace) -> ImportSummary:
    file_path = Path(args.file)
    summary = ImportSummary(
        file_path=str(file_path), dataset_type=DATASET_TYPE, dry_run=args.dry_run
    )

    if not file_path.exists():
        print(f"ERROR: file not found: {file_path}", file=sys.stderr)
        sys.exit(1)

    df = read_table(file_path)
    summary.rows_read = len(df)

    if not args.dry_run:
        preserve_raw_file(file_path, DATASET_TYPE)

    session = SessionLocal()
    try:
        for idx, row in df.iterrows():
            etf_symbol = _clean(row.get("etf_symbol")) or args.etf_symbol
            ex_dividend_date = _parse_date(row.get("ex_dividend_date"))
            source_name = _clean(row.get("source_name")) or args.source_name

            if not etf_symbol or ex_dividend_date is None:
                summary.skipped_invalid += 1
                continue

            exists = (
                session.query(EtfDividend)
                .filter_by(
                    etf_symbol=etf_symbol,
                    ex_dividend_date=ex_dividend_date,
                    source_name=source_name,
                )
                .first()
            )
            if exists:
                summary.skipped_existing += 1
                continue

            if args.dry_run:
                summary.inserted += 1
                continue

            try:
                session.add(
                    EtfDividend(
                        etf_symbol=etf_symbol,
                        ex_dividend_date=ex_dividend_date,
                        payment_date=_parse_date(row.get("payment_date")),
                        dividend_amount=_num(row.get("dividend_amount")),
                        dividend_yield=_num(row.get("dividend_yield")),
                        source_name=source_name,
                        source_url=_clean(row.get("source_url")) or args.source_url,
                        fetched_at=dt.datetime.utcnow(),
                    )
                )
                session.commit()
                summary.inserted += 1
            except Exception as exc:  # noqa: BLE001
                session.rollback()
                summary.errors.append(f"row {idx}: {exc}")
        if not args.dry_run:
            summary.quality_summary = run_and_report(session, DATASET_TYPE)
    finally:
        session.close()

    return summary


def main(argv=None) -> None:
    args = parse_args(argv)
    summary = run(args)
    summary.print_report()
    if getattr(summary, "quality_summary", None):
        print(summary.quality_summary)
    if summary.errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
