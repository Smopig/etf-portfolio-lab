"""Yahoo Taiwan ETF holdings provider (CLAUDE.md §7).

Fetches ETF top-10 constituent / holdings rows from Yahoo奇摩股市's public
ETF holding page::

    https://tw.stock.yahoo.com/quote/{CODE}.TW/holding

A plain GET with a browser ``User-Agent`` returns the HTML page (~310KB).
The holdings are embedded as JSON inside the HTML under a ``top10Holdings``
blob, with the form::

    "top10Holdings":{"date":"2026/05/01","holdingDetail":[
        {"date":"2026/05/01","ticker":"2330.TW","name":"台積電","weighting":"58.28"},
        ...up to 10 rows...
    ]}

Slashes inside the JSON are unicode-escaped as ``\\u002F`` in the raw HTML;
the parser unescapes those before extracting rows.

Per CLAUDE.md §7: this provider NEVER fabricates rows. On HTTP error,
non-200, a missing ``top10Holdings`` blob, or no parseable rows it returns
an empty ``records`` list with a descriptive ``errors`` entry. Some ETFs
(e.g. bond / futures ETFs) may legitimately have non-Taiwan tickers; those
are preserved verbatim (only the ``.TW`` / ``.TWO`` suffix is stripped).

No API token is required.
"""

from __future__ import annotations

import datetime as dt
import re
from typing import Callable

from app.providers.data.base import BaseDataProvider, ProviderResult

DEFAULT_BASE_URL = "https://tw.stock.yahoo.com/quote"

# Each holdingDetail object inside the top10Holdings blob.
_ROW_RE = re.compile(
    r'"date":"(?P<date>[0-9/]+)","ticker":"(?P<ticker>[0-9A-Za-z.]+)",'
    r'"name":"(?P<name>[^"]+)","weighting":"(?P<weight>[0-9.]+)"'
)
# Fallback: holdingDetail objects without a leading date field.
_ROW_RE_NODATE = re.compile(
    r'"ticker":"(?P<ticker>[0-9A-Za-z.]+)",'
    r'"name":"(?P<name>[^"]+)","weighting":"(?P<weight>[0-9.]+)"'
)

_MAX_ROWS = 10


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


def _strip_suffix(ticker: str) -> str:
    """Strip a Taiwan exchange suffix (``.TW`` / ``.TWO``) from a ticker.

    Foreign / bond tickers (e.g. ``US912810UA42``) carry no such suffix and
    are returned unchanged.
    """
    for suffix in (".TWO", ".TW"):
        if ticker.endswith(suffix):
            return ticker[: -len(suffix)]
    return ticker


def _parse_holding_date(value: str | None) -> dt.date | None:
    if not value:
        return None
    value = value.strip()
    for fmt in ("%Y/%m/%d", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


class YahooHoldingProvider(BaseDataProvider):
    """Fetches ETF top-10 holdings from Yahoo奇摩股市's holding page.

    Accepts an injectable ``http_get`` callable: ``(url: str) -> bytes``
    (so tests can stub the network). No token required.
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

    # ------------------------------------------------------------------
    # URL helper
    # ------------------------------------------------------------------
    def _holding_url(self, symbol: str) -> str:
        return f"{self.base_url}/{symbol}.TW/holding"

    # ------------------------------------------------------------------
    # Fetch
    # ------------------------------------------------------------------
    def fetch(self, *, symbol: str, **_extra) -> ProviderResult:
        dataset_type = "etf_holdings"
        url = self._holding_url(symbol)

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
                return empty([f"HTTP {code} fetching Yahoo holding page"])
            return empty([f"HTTP request failed: {exc}"])

        if not raw:
            return empty(["empty response from Yahoo"])

        try:
            html = raw.decode("utf-8", errors="ignore")
        except Exception as exc:  # noqa: BLE001
            return empty([f"failed to decode response: {exc}"])

        # Unescape JSON-encoded slashes (Yahoo emits "/" for "/").
        html = html.replace("\\u002F", "/").replace("\\/", "/")

        blob_start = html.find("top10Holdings")
        if blob_start < 0:
            return empty(["no top10Holdings blob found in Yahoo page"])

        # Limit matching to a window after the blob marker so unrelated
        # objects elsewhere in the page cannot leak in.
        window = html[blob_start : blob_start + 8000]

        matches = list(_ROW_RE.finditer(window))
        used_nodate = False
        if not matches:
            matches = list(_ROW_RE_NODATE.finditer(window))
            used_nodate = True

        if not matches:
            return empty(["no parseable holdings in Yahoo top10Holdings blob"])

        fetched_at = dt.datetime.utcnow()
        fallback_date = dt.date.today()
        records: list[dict] = []
        max_row_date: dt.date | None = None

        for m in matches[:_MAX_ROWS]:
            ticker = m.group("ticker")
            row_date = (
                None if used_nodate else _parse_holding_date(m.group("date"))
            )
            effective_date = row_date or fallback_date
            if row_date is not None and (
                max_row_date is None or row_date > max_row_date
            ):
                max_row_date = row_date

            try:
                weight = float(m.group("weight"))
            except (TypeError, ValueError):
                weight = None

            records.append(
                {
                    "etf_symbol": symbol,
                    "holding_date": effective_date,
                    "asset_symbol": _strip_suffix(ticker),
                    "asset_name": m.group("name"),
                    "weight": weight,
                    "source_name": self.name,
                    "source_url": url,
                    "fetched_at": fetched_at,
                    "confidence_level": "MEDIUM",
                }
            )

        if not records:
            return empty(["no usable holdings parsed from Yahoo page"])

        return ProviderResult(
            records=records,
            dataset_type=dataset_type,
            source_name=self.name,
            source_url=url,
            data_date=max_row_date or fallback_date,
            reliability_level="medium",
            errors=[],
        )
