"""Yahoo Taiwan ETF dividend provider (CLAUDE.md §7).

Fetches an ETF's per-distribution dividend history from Yahoo奇摩股市's
public dividend page::

    https://tw.stock.yahoo.com/quote/{CODE}.TW/dividend

A plain GET with a browser ``User-Agent`` returns the HTML page; the dividend
history is embedded as JSON under a ``"dividends":[`` blob. Records carry a
``recordType``:

- ``"SUB"``  = per-distribution rows. USE THESE.
- ``"YEAR"`` = annual summary rows. SKIPPED.

Verified SUB shape (00929)::

    {"exDate":"2026-06-17T00:00:00+08:00","year":"2026","period":"M5",
     "symbol":"00929","totalDividend":"0.26","isUpcoming":false,
     "exDividend":{"cash":"0.26","cashPayDate":"2026-07-13T00:00:00+08:00"},
     "recordType":"SUB"}

Slashes inside the JSON may be unicode-escaped as ``\\u002F`` in the raw HTML;
the parser unescapes those before extracting rows.

Per CLAUDE.md §7: this provider NEVER fabricates rows. On HTTP error, non-200,
a missing ``dividends`` blob, or no parseable rows it returns an empty
``records`` list with a descriptive ``errors`` entry. ``isUpcoming`` rows are
preserved (flagged) so downstream TTM logic can exclude unpaid distributions.

No API token is required.
"""

from __future__ import annotations

import datetime as dt
import json
from typing import Callable

from app.providers.data.base import BaseDataProvider, ProviderResult

DEFAULT_BASE_URL = "https://tw.stock.yahoo.com/quote"


def _default_http_get(url: str) -> bytes:
    from urllib.request import Request, urlopen

    req = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0 Safari/537.36"
            )
        },
    )
    with urlopen(req, timeout=20) as resp:  # noqa: S310
        return resp.read()


def _parse_iso_date(value: str | None) -> dt.date | None:
    """Parse the date part of an ISO string like ``2026-06-17T00:00:00+08:00``."""
    if not value or not isinstance(value, str):
        return None
    head = value.strip()[:10]
    try:
        return dt.datetime.strptime(head, "%Y-%m-%d").date()
    except ValueError:
        return None


def _parse_float(value) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _extract_dividends_array(html: str) -> list | None:
    """Locate the ``"dividends":[ ... ]`` JSON array and parse it.

    Uses bracket-depth balancing (respecting string literals) so the exact
    array bounds are found regardless of surrounding page content.
    """
    marker = '"dividends":['
    start = html.find(marker)
    if start < 0:
        return None
    arr_start = start + len(marker) - 1  # index of the opening '['

    depth = 0
    in_str = False
    escaped = False
    for i in range(arr_start, len(html)):
        ch = html[i]
        if in_str:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                blob = html[arr_start : i + 1]
                try:
                    return json.loads(blob)
                except (ValueError, json.JSONDecodeError):
                    return None
    return None


class YahooDividendProvider(BaseDataProvider):
    """Fetches an ETF's dividend history from Yahoo奇摩股市's dividend page.

    Accepts an injectable ``http_get`` callable ``(url: str) -> bytes`` so
    tests can stub the network. No token required.
    """

    name = "Yahoo奇摩股市"
    source_type = "network"

    def __init__(
        self,
        http_get: Callable[[str], bytes] | None = None,
        base_url: str = DEFAULT_BASE_URL,
        **_extra,
    ) -> None:
        self.http_get = http_get or _default_http_get
        self.base_url = base_url.rstrip("/")

    def _dividend_url(self, symbol: str) -> str:
        return f"{self.base_url}/{symbol}.TW/dividend"

    def fetch(self, *, symbol: str, **_extra) -> ProviderResult:
        dataset_type = "etf_dividends"
        url = self._dividend_url(symbol)

        def empty(errors: list[str]) -> ProviderResult:
            return ProviderResult(
                records=[],
                dataset_type=dataset_type,
                source_name=self.name,
                source_url=url,
                data_date=None,
                reliability_level=None,
                errors=errors,
            )

        try:
            raw = self.http_get(url)
        except Exception as exc:  # noqa: BLE001
            code = getattr(exc, "code", None)
            if code is not None:
                return empty([f"HTTP {code} fetching Yahoo dividend page"])
            return empty([f"HTTP request failed: {exc}"])

        if not raw:
            return empty(["empty response from Yahoo"])

        try:
            html = raw.decode("utf-8", errors="ignore")
        except Exception as exc:  # noqa: BLE001
            return empty([f"failed to decode response: {exc}"])

        # Unescape JSON-encoded slashes (Yahoo emits "/" for "/").
        html = html.replace("\\u002F", "/").replace("\\/", "/")

        dividends = _extract_dividends_array(html)
        if dividends is None:
            return empty(["no dividends blob found in Yahoo page"])

        fetched_at = dt.datetime.utcnow()
        records: list[dict] = []
        max_ex_date: dt.date | None = None

        for row in dividends:
            if not isinstance(row, dict):
                continue
            if row.get("recordType") != "SUB":
                continue

            ex_date = _parse_iso_date(row.get("exDate"))
            if ex_date is None:
                continue

            ex_dividend = row.get("exDividend") or {}
            pay_date = _parse_iso_date(
                ex_dividend.get("cashPayDate") if isinstance(ex_dividend, dict) else None
            )

            amount = _parse_float(row.get("totalDividend"))
            if amount is None and isinstance(ex_dividend, dict):
                amount = _parse_float(ex_dividend.get("cash"))

            is_upcoming = bool(row.get("isUpcoming"))
            period = row.get("period") or ""

            if max_ex_date is None or ex_date > max_ex_date:
                max_ex_date = ex_date

            records.append(
                {
                    "etf_symbol": symbol,
                    "ex_dividend_date": ex_date,
                    "payment_date": pay_date,
                    "dividend_amount": amount,
                    "is_upcoming": is_upcoming,
                    "period": str(period),
                    "source_name": self.name,
                    "source_url": url,
                    "fetched_at": fetched_at,
                    "confidence_level": "MEDIUM",
                }
            )

        if not records:
            return empty(["no parseable SUB dividend rows in Yahoo page"])

        return ProviderResult(
            records=records,
            dataset_type=dataset_type,
            source_name=self.name,
            source_url=url,
            data_date=max_ex_date,
            reliability_level="medium",
            errors=[],
        )
