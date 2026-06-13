"""Import stock industry classification data into stock_industry.

Usage:
    python -m scripts.import_industry <path-to-file> [options]

Expected columns (see data/samples/stock_industry.csv):
    stock_symbol, stock_name, market, industry_level_1, industry_level_2,
    industry_level_3, custom_sector, custom_theme, source_name, source_url

Unique key: stock_symbol (skips rows whose stock_symbol already exists).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.core.database import SessionLocal
from app.models import StockIndustry
from app.utils.data_quality import run_and_report
from app.utils.importers import ImportSummary, _clean, preserve_raw_file, read_table

DATASET_TYPE = "stock_industry"


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import stock industry classification data.")
    parser.add_argument("file", help="Path to CSV or Excel file")
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
            stock_symbol = _clean(row.get("stock_symbol"))
            if not stock_symbol:
                summary.skipped_invalid += 1
                continue

            exists = (
                session.query(StockIndustry).filter_by(stock_symbol=stock_symbol).first()
            )
            if exists:
                summary.skipped_existing += 1
                continue

            if args.dry_run:
                summary.inserted += 1
                continue

            try:
                session.add(
                    StockIndustry(
                        stock_symbol=stock_symbol,
                        stock_name=_clean(row.get("stock_name")),
                        market=_clean(row.get("market")),
                        industry_level_1=_clean(row.get("industry_level_1")),
                        industry_level_2=_clean(row.get("industry_level_2")),
                        industry_level_3=_clean(row.get("industry_level_3")),
                        custom_sector=_clean(row.get("custom_sector")),
                        custom_theme=_clean(row.get("custom_theme")),
                        source_name=_clean(row.get("source_name")) or args.source_name,
                        source_url=_clean(row.get("source_url")) or args.source_url,
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
