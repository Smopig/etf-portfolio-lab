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

The core fetch logic lives in ``app.services.refresh_service.run_full_fetch``
and is shared with the ``/api/data/refresh`` background-refresh endpoint.
"""

from __future__ import annotations

import argparse

from app.services.refresh_service import run_full_fetch


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


def main(argv=None) -> None:
    args = parse_args(argv)

    def progress(state: dict) -> None:
        print(f"[progress] {state}")

    result = run_full_fetch(
        progress=progress,
        prices=args.prices,
        price_range=args.range,
        limit=args.limit,
        market=args.market,
    )

    print("=" * 60)
    print("Summary:")
    print(f"  list_summary: {result['list_summary']}")
    print(f"  symbols_total: {result['symbols_total']}")
    if result["prices"]:
        print(f"  prices: {result['prices']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
