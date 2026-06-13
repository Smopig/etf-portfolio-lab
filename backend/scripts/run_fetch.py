"""Run a data provider fetch via the orchestrator.

Usage:
    python -m scripts.run_fetch --provider local-file --dataset etf_prices \
        --file data/samples/0050_prices.csv [--persist]

    python -m scripts.run_fetch --provider yahoo-finance --dataset etf_prices \
        --symbol 0050.TW [--persist]
"""

from __future__ import annotations

import argparse
import sys

from app.core.database import SessionLocal
from app.providers.data.factory import get_data_provider
from app.services.data_fetch_service import run_fetch


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a data provider fetch.")
    parser.add_argument("--provider", required=True, help="Provider key (see factory.py)")
    parser.add_argument("--dataset", required=True, help="Dataset type, e.g. etf_prices")
    parser.add_argument("--file", default=None, help="Local file path (for file providers)")
    parser.add_argument("--symbol", default=None, help="Symbol (for network providers)")
    parser.add_argument(
        "--persist",
        action="store_true",
        help="Write results to the database (otherwise dry-run, no writes)",
    )
    return parser.parse_args(argv)


def main(argv=None) -> None:
    args = parse_args(argv)
    provider = get_data_provider(args.provider)

    params: dict = {}
    if args.file:
        params["file_path"] = args.file
        params["dataset_type"] = args.dataset
    if args.symbol:
        params["symbol"] = args.symbol

    session = SessionLocal()
    try:
        summary = run_fetch(session, provider, args.dataset, persist=args.persist, **params)
    finally:
        session.close()

    print("=" * 60)
    print(f"Fetch summary: {args.provider} / {args.dataset}")
    print(f"  status:        {summary['status']}")
    print(f"  rows fetched:  {summary['rows_fetched']}")
    print(f"  rows inserted: {summary['rows_inserted']}")
    print(f"  source_url:    {summary['source_url']}")
    print(f"  data_date:     {summary['data_date']}")
    if summary["errors"]:
        print(f"  errors:        {summary['errors']}")
    if summary.get("quality_summary"):
        print(f"  {summary['quality_summary']}")
    print("=" * 60)

    if summary["status"] == "error":
        sys.exit(1)


if __name__ == "__main__":
    main()
