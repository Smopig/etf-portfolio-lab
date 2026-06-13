"""Fetch the full Taiwan ETF list + recent prices from real public sources.

The ONE command to populate the database with real data (run inside the
backend container, which has internet access):

    docker compose exec backend python -m scripts.fetch_all

Steps:
    1. Fetch the full ETF list (上市 + 上櫃) from the TWSE ISIN listing pages
       and upsert into ``etf_master`` (CLAUDE.md §7: source/date/reliability
       attached to every record; failures recorded via FetchLog, no
       fabrication).
    2. For each ETF symbol now in ``etf_master``, fetch recent daily OHLCV
       prices from Yahoo Finance (trying "<symbol>.TW", then "<symbol>.TWO"
       if the first attempt yields no data) and upsert into ``etf_prices``.

Holdings (成分股) are OUT OF SCOPE for this script.
"""

from __future__ import annotations

import argparse
import time

from app.core.database import SessionLocal
from app.models import EtfMaster
from app.providers.data.factory import get_data_provider
from app.services.data_fetch_service import run_fetch


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch the full Taiwan ETF list + recent prices from TWSE/Yahoo."
    )
    parser.add_argument(
        "--prices",
        dest="prices",
        action="store_true",
        default=True,
        help="(default) also fetch recent prices for each ETF",
    )
    parser.add_argument(
        "--no-prices",
        dest="prices",
        action="store_false",
        help="skip the price-fetch step (ETF list only)",
    )
    parser.add_argument(
        "--range",
        default="1y",
        help="Yahoo Finance 'range' query param for price history (default: 1y)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Only fetch prices for the first N ETFs (useful for testing)",
    )
    parser.add_argument(
        "--market",
        choices=["listed", "otc", "both"],
        default="both",
        help="Which TWSE ISIN market section(s) to fetch (default: both)",
    )
    return parser.parse_args(argv)


def fetch_etf_list(session, market: str) -> list[str]:
    print("=" * 60)
    print("Step 1: fetching ETF master list from TWSE ISIN listing pages...")
    provider = get_data_provider("twse-etf-list")
    summary = run_fetch(session, provider, "etf_master", persist=True, market=market)

    print(f"  status:        {summary['status']}")
    print(f"  rows fetched:  {summary['rows_fetched']}")
    print(f"  rows inserted: {summary['rows_inserted']}")
    print(f"  source_url:    {summary['source_url']}")
    print(f"  data_date:     {summary['data_date']}")
    if summary["errors"]:
        print(f"  errors:        {summary['errors']}")

    symbols = [s for (s,) in session.query(EtfMaster.symbol).order_by(EtfMaster.symbol).all()]
    print(f"  etf_master now has {len(symbols)} ETF symbol(s) total")
    print("=" * 60)
    return symbols


def fetch_prices_for_symbols(session, symbols: list[str], date_range: str, limit: int | None) -> None:
    if limit is not None:
        symbols = symbols[:limit]

    print("Step 2: fetching recent daily prices from Yahoo Finance...")
    print(f"  symbols to process: {len(symbols)}  (range={date_range})")

    n_total = len(symbols)
    n_with_prices = 0
    n_failures = 0

    for i, symbol in enumerate(symbols, start=1):
        provider = get_data_provider("yahoo-finance")
        ok = False
        try:
            for suffix in (".TW", ".TWO"):
                yahoo_symbol = f"{symbol}{suffix}"
                summary = run_fetch(
                    session,
                    provider,
                    "etf_prices",
                    persist=True,
                    symbol=yahoo_symbol,
                    range=date_range,
                )
                if summary["status"] == "success" and summary["rows_fetched"] > 0:
                    ok = True
                    print(
                        f"  [{i}/{n_total}] {symbol}: OK via {yahoo_symbol} "
                        f"({summary['rows_fetched']} rows, {summary['rows_inserted']} new)"
                    )
                    break
            if not ok:
                n_failures += 1
                print(f"  [{i}/{n_total}] {symbol}: FAILED (no data from .TW or .TWO)")
        except Exception as exc:  # noqa: BLE001
            n_failures += 1
            print(f"  [{i}/{n_total}] {symbol}: FAILED (exception: {exc})")

        if ok:
            n_with_prices += 1

        time.sleep(0.4)

    print("=" * 60)
    print("Price fetch summary:")
    print(f"  symbols processed: {n_total}")
    print(f"  with prices:       {n_with_prices}")
    print(f"  failures:          {n_failures}")
    print("=" * 60)


def main(argv=None) -> None:
    args = parse_args(argv)

    session = SessionLocal()
    try:
        symbols = fetch_etf_list(session, args.market)

        if args.prices:
            fetch_prices_for_symbols(session, symbols, args.range, args.limit)
        else:
            print("Skipping price fetch (--no-prices).")
    finally:
        session.close()


if __name__ == "__main__":
    main()
