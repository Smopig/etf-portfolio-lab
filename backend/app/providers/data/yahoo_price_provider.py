"""Yahoo Finance daily price provider (CLAUDE.md §7: no fabrication).

Fetches daily OHLCV price data for a symbol from Yahoo Finance's public
"chart" JSON endpoint:

    https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=...&interval=1d

Assumptions about the remote response shape (Yahoo's "v8 chart" API):
- Top-level JSON has ``chart.result[0]`` containing:
  - ``timestamp``: list of UNIX timestamps (UTC seconds, one per trading day)
  - ``indicators.quote[0]``: dict with parallel lists ``open``, ``high``,
    ``low``, ``close``, ``volume``
  - ``indicators.adjclose[0].adjclose``: parallel list of adjusted close
    (only present if ``events=div`` or default chart query includes it)
- ``chart.error`` is non-null on failure (symbol not found, rate limit, etc).

The HTTP call is fully dependency-injected via the ``http_get`` callable so
tests never hit the network. ``http_get(url) -> bytes`` (raw response body).
If no ``http_get`` is supplied, a small stdlib ``urllib``-based default is
used lazily (only imported when actually called).

On any network error, non-2xx-equivalent failure, JSON decode error,
``chart.error`` present, or empty timestamp series: returns an empty
``records`` list with a descriptive ``errors`` entry. Never fabricates
price rows.
"""

from __future__ import annotations

import datetime as dt
import json
from typing import Callable

from app.providers.data.base import BaseDataProvider, ProviderResult

DEFAULT_BASE_URL = "https://query1.finance.yahoo.com/v8/finance/chart"


def _default_http_get(url: str) -> bytes:
    """Default HTTP GET using stdlib urllib (lazy import)."""
    from urllib.request import Request, urlopen

    req = Request(url, headers={"User-Agent": "etf-portfolio-lab/1.0"})
    with urlopen(req, timeout=10) as resp:  # noqa: S310
        return resp.read()


class YahooPriceProvider(BaseDataProvider):
    """Fetches daily OHLCV prices for one symbol from Yahoo Finance."""

    name = "yahoo-finance"
    source_type = "api"

    def __init__(self, http_get: Callable[[str], bytes] | None = None, base_url: str | None = None) -> None:
        self.http_get = http_get or _default_http_get
        self.base_url = base_url or DEFAULT_BASE_URL

    def fetch(self, **params) -> ProviderResult:
        """Fetch daily prices for ``symbol``.

        Params:
            symbol / etf_symbol: ticker symbol to query (required).
            range: Yahoo "range" query param (default "1mo").
            interval: Yahoo "interval" query param (default "1d").

        Returns:
            ProviderResult with one record per trading day:
            ``{etf_symbol, trade_date, open, high, low, close,
            adjusted_close, volume, source_name, source_url}``.
            Empty + errors on any failure.
        """
        symbol = params.get("symbol") or params.get("etf_symbol")
        date_range = params.get("range", "1mo")
        interval = params.get("interval", "1d")

        url = f"{self.base_url}/{symbol}?range={date_range}&interval={interval}"

        result = ProviderResult(
            dataset_type="etf_prices",
            source_name=self.name,
            source_url=url,
            reliability_level="medium",
        )

        if not symbol:
            result.errors.append("YahooPriceProvider.fetch: missing required 'symbol' parameter")
            return result

        try:
            raw = self.http_get(url)
        except Exception as exc:  # noqa: BLE001
            result.errors.append(f"YahooPriceProvider.fetch: HTTP request failed: {exc}")
            return result

        try:
            payload = json.loads(raw)
        except (ValueError, TypeError) as exc:
            result.errors.append(f"YahooPriceProvider.fetch: invalid JSON response: {exc}")
            return result

        chart = payload.get("chart", {})
        if chart.get("error"):
            result.errors.append(f"YahooPriceProvider.fetch: API error: {chart['error']}")
            return result

        chart_results = chart.get("result") or []
        if not chart_results:
            result.errors.append("YahooPriceProvider.fetch: empty 'chart.result' in response")
            return result

        chart_result = chart_results[0]
        timestamps = chart_result.get("timestamp") or []
        if not timestamps:
            result.errors.append("YahooPriceProvider.fetch: no timestamps in response")
            return result

        indicators = chart_result.get("indicators", {})
        quote_list = indicators.get("quote") or [{}]
        quote = quote_list[0]
        adjclose_list = indicators.get("adjclose") or [{}]
        adjclose = adjclose_list[0].get("adjclose") if adjclose_list else None

        opens = quote.get("open") or []
        highs = quote.get("high") or []
        lows = quote.get("low") or []
        closes = quote.get("close") or []
        volumes = quote.get("volume") or []

        records: list[dict] = []
        latest_date: dt.date | None = None
        for i, ts in enumerate(timestamps):
            trade_date = dt.datetime.utcfromtimestamp(ts).date()
            latest_date = trade_date if latest_date is None else max(latest_date, trade_date)

            def _at(lst, idx):
                return lst[idx] if idx < len(lst) else None

            records.append(
                {
                    "etf_symbol": symbol,
                    "trade_date": trade_date,
                    "open": _at(opens, i),
                    "high": _at(highs, i),
                    "low": _at(lows, i),
                    "close": _at(closes, i),
                    "adjusted_close": _at(adjclose, i) if adjclose else _at(closes, i),
                    "volume": _at(volumes, i),
                    "source_name": self.name,
                    "source_url": url,
                }
            )

        if not records:
            result.errors.append("YahooPriceProvider.fetch: no price rows parsed from response")
            return result

        result.records = records
        result.data_date = latest_date
        return result
