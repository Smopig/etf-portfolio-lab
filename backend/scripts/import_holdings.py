"""Import ETF holdings data into etf_holdings, plus snapshot tables.

Usage:
    python -m scripts.import_holdings <path-to-file> [options]

Expected columns (see data/samples/0050_holdings.csv):
    etf_symbol, holding_date, asset_symbol, asset_name, asset_type, weight,
    shares, market_value, source_name, source_url, confidence_level

Unique key for etf_holdings: (etf_symbol, holding_date, asset_symbol).

In addition to upserting etf_holdings rows, this script creates (or reuses)
one EtfHoldingSnapshot row per (etf_symbol, holding_date, source_name) found
in the file, recording raw_file_path + parser_version, and inserts an
EtfHoldingSnapshotItem for each row belonging to a newly created snapshot
(immutable copy). Re-importing the same file reuses the existing snapshot
and does not duplicate its items.

If `etf_symbol` is not present as a column, pass --etf-symbol.
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

from app.core.database import SessionLocal
from app.models import EtfHolding, EtfHoldingSnapshot, EtfHoldingSnapshotItem
from app.utils.data_quality import run_and_report
from app.utils.importers import ImportSummary, _clean, _parse_date, preserve_raw_file, read_table

DATASET_TYPE = "etf_holdings"
PARSER_VERSION = "import_holdings.v1"


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import ETF holdings data.")
    parser.add_argument("file", help="Path to CSV or Excel file")
    parser.add_argument("--etf-symbol", default=None, help="Fallback etf_symbol if column missing")
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

    raw_file_path = None
    if not args.dry_run:
        raw_file_path = str(preserve_raw_file(file_path, DATASET_TYPE))

    session = SessionLocal()
    try:
        # snapshot cache: (etf_symbol, holding_date, source_name) -> snapshot id (or None for dry-run)
        snapshots: dict[tuple, int | None] = {}
        snapshots_created: dict[tuple, bool] = {}

        for idx, row in df.iterrows():
            etf_symbol = _clean(row.get("etf_symbol")) or args.etf_symbol
            holding_date = _parse_date(row.get("holding_date"))
            asset_symbol = _clean(row.get("asset_symbol"))
            source_name = _clean(row.get("source_name")) or args.source_name
            source_url = _clean(row.get("source_url")) or args.source_url
            confidence_level = _clean(row.get("confidence_level")) or args.confidence

            if not etf_symbol or holding_date is None:
                summary.skipped_invalid += 1
                continue

            # --- snapshot (one per etf_symbol/holding_date/source_name) ---
            snapshot_key = (etf_symbol, holding_date, source_name)
            snapshot_id = None
            if not args.dry_run:
                if snapshot_key not in snapshots:
                    existing_snapshot = (
                        session.query(EtfHoldingSnapshot)
                        .filter_by(
                            etf_symbol=etf_symbol,
                            snapshot_date=holding_date,
                            source_name=source_name,
                        )
                        .first()
                    )
                    if existing_snapshot:
                        snapshot_id = existing_snapshot.id
                        snapshots_created[snapshot_key] = False
                    else:
                        new_snapshot = EtfHoldingSnapshot(
                            etf_symbol=etf_symbol,
                            snapshot_date=holding_date,
                            source_name=source_name,
                            source_url=source_url,
                            raw_file_path=raw_file_path,
                            parser_version=PARSER_VERSION,
                            fetched_at=dt.datetime.utcnow(),
                        )
                        session.add(new_snapshot)
                        session.commit()
                        snapshot_id = new_snapshot.id
                        snapshots_created[snapshot_key] = True
                    snapshots[snapshot_key] = snapshot_id
                else:
                    snapshot_id = snapshots[snapshot_key]

                # Only append a snapshot item if this snapshot was newly
                # created in this run (avoid duplicating items on re-import)
                if snapshots_created.get(snapshot_key):
                    try:
                        session.add(
                            EtfHoldingSnapshotItem(
                                snapshot_id=snapshot_id,
                                asset_symbol=asset_symbol,
                                asset_name=_clean(row.get("asset_name")),
                                asset_type=_clean(row.get("asset_type")),
                                weight=_clean(row.get("weight")),
                                shares=_clean(row.get("shares")),
                                market_value=_clean(row.get("market_value")),
                            )
                        )
                        session.commit()
                    except Exception as exc:  # noqa: BLE001
                        session.rollback()
                        summary.errors.append(f"row {idx} (snapshot item): {exc}")

            # --- current holdings table (idempotent upsert by skip) ---
            exists = (
                session.query(EtfHolding)
                .filter_by(
                    etf_symbol=etf_symbol,
                    holding_date=holding_date,
                    asset_symbol=asset_symbol,
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
                    EtfHolding(
                        etf_symbol=etf_symbol,
                        holding_date=holding_date,
                        asset_symbol=asset_symbol,
                        asset_name=_clean(row.get("asset_name")),
                        asset_type=_clean(row.get("asset_type")),
                        weight=_clean(row.get("weight")),
                        shares=_clean(row.get("shares")),
                        market_value=_clean(row.get("market_value")),
                        source_name=source_name,
                        source_url=source_url,
                        fetched_at=dt.datetime.utcnow(),
                        confidence_level=confidence_level,
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
