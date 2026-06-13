"""Import ETF master data from a CSV/Excel file into etf_master.

Usage:
    python -m scripts.import_etf_master <path-to-file> [options]

Expected columns (see data/samples/etf_master.csv):
    symbol, name, issuer, listing_date, management_type, asset_class,
    investment_style, strategy_type, tracking_index, index_provider,
    selection_method, weighting_method, rebalance_frequency,
    replication_method, expense_ratio, management_fee, custody_fee,
    dividend_frequency, source_name, source_url, data_date, confidence_level

Unique key: symbol (skips rows whose symbol already exists).
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

from app.core.database import SessionLocal
from app.models import EtfMaster
from app.utils.data_quality import run_and_report
from app.utils.importers import ImportSummary, _clean, _parse_date, preserve_raw_file, read_table

DATASET_TYPE = "etf_master"


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import ETF master data.")
    parser.add_argument("file", help="Path to CSV or Excel file")
    parser.add_argument("--source-name", default=None, help="Fallback source_name")
    parser.add_argument("--source-url", default=None, help="Fallback source_url")
    parser.add_argument("--confidence", default=None, help="Fallback confidence_level")
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
            symbol = _clean(row.get("symbol"))
            if not symbol:
                summary.skipped_invalid += 1
                continue

            exists = session.query(EtfMaster).filter_by(symbol=symbol).first()
            if exists:
                summary.skipped_existing += 1
                continue

            if args.dry_run:
                summary.inserted += 1
                continue

            try:
                session.add(
                    EtfMaster(
                        symbol=symbol,
                        name=_clean(row.get("name")) or symbol,
                        issuer=_clean(row.get("issuer")),
                        listing_date=_parse_date(row.get("listing_date")),
                        management_type=_clean(row.get("management_type")),
                        asset_class=_clean(row.get("asset_class")),
                        investment_style=_clean(row.get("investment_style")),
                        strategy_type=_clean(row.get("strategy_type")),
                        tracking_index=_clean(row.get("tracking_index")),
                        index_provider=_clean(row.get("index_provider")),
                        selection_method=_clean(row.get("selection_method")),
                        weighting_method=_clean(row.get("weighting_method")),
                        rebalance_frequency=_clean(row.get("rebalance_frequency")),
                        replication_method=_clean(row.get("replication_method")),
                        expense_ratio=_clean(row.get("expense_ratio")),
                        management_fee=_clean(row.get("management_fee")),
                        custody_fee=_clean(row.get("custody_fee")),
                        dividend_frequency=_clean(row.get("dividend_frequency")),
                        source_name=_clean(row.get("source_name")) or args.source_name,
                        source_url=_clean(row.get("source_url")) or args.source_url,
                        data_date=_parse_date(row.get("data_date")),
                        fetched_at=dt.datetime.utcnow(),
                        confidence_level=_clean(row.get("confidence_level")) or args.confidence,
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
