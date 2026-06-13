"""TWSE/TPEx ISIN listing provider for ETF master list (CLAUDE.md §7).

Fetches the long-standing TWSE ISIN listing pages (HTML tables) for listed
(上市) and OTC (上櫃) instruments, filters to rows whose section header is
exactly "ETF" (excluding ETN / 受益證券 / 認購售權證 etc.), and normalizes
each row into an ``etf_master`` record.

Source pages:
    listed (上市): https://isin.twse.com.tw/isin/C_public.jsp?strMode=2
    OTC (上櫃):    https://isin.twse.com.tw/isin/C_public.jsp?strMode=4

The page is served as Big5/CP950-encoded HTML. ``http_get`` returns raw
bytes; this provider decodes with cp950 (fallback big5, then
errors="replace").

Per CLAUDE.md §7: never fabricates rows. On HTTP failure or parse failure
(no ETF rows found), returns empty ``records`` with ``errors`` populated.
"""

from __future__ import annotations

import datetime as dt
import re
from html.parser import HTMLParser
from typing import Callable

from app.providers.data.base import BaseDataProvider, ProviderResult

LISTED_URL = "https://isin.twse.com.tw/isin/C_public.jsp?strMode=2"
OTC_URL = "https://isin.twse.com.tw/isin/C_public.jsp?strMode=4"

_WS_RE = re.compile(r"[\s　]+")


def _default_http_get(url: str) -> bytes:
    from urllib.request import Request, urlopen

    req = Request(url, headers={"User-Agent": "etf-portfolio-lab/1.0"})
    with urlopen(req, timeout=15) as resp:  # noqa: S310
        return resp.read()


class _IsinTableParser(HTMLParser):
    """Parses the TWSE ISIN listing HTML table into rows of cell text.

    Tracks <tr> boundaries and collects the text of each <td>/<th> cell.
    Rows are emitted as lists of stripped cell strings via ``self.rows``.
    """

    def __init__(self) -> None:
        super().__init__()
        self.rows: list[list[str]] = []
        self._current_row: list[str] | None = None
        self._current_cell: list[str] | None = None
        self._in_cell = False

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self._current_row = []
        elif tag in ("td", "th"):
            self._current_cell = []
            self._in_cell = True

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._current_row is not None:
            text = "".join(self._current_cell or []).strip()
            self._current_row.append(text)
            self._current_cell = None
            self._in_cell = False
        elif tag == "tr" and self._current_row is not None:
            self.rows.append(self._current_row)
            self._current_row = None

    def handle_data(self, data):
        if self._in_cell and self._current_cell is not None:
            self._current_cell.append(data)


def _decode(raw: bytes) -> str:
    for enc in ("cp950", "big5"):
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("cp950", errors="replace")


def _normalize_date(value: str) -> str | None:
    value = (value or "").strip()
    if not value:
        return None
    value = value.replace("/", "-")
    return value


def _parse_rows(html: str) -> list[dict]:
    """Parse the ISIN table HTML, returning only rows in the "ETF" section."""
    parser = _IsinTableParser()
    parser.feed(html)

    records: list[dict] = []
    current_section: str | None = None

    for row in parser.rows:
        cells = [c for c in row]
        if not cells:
            continue

        # Section header rows: a single non-empty cell (others empty/missing),
        # e.g. "ETF", "股票", "ETN", "受益證券".
        non_empty = [c for c in cells if c.strip()]
        if len(non_empty) == 1 and "　" not in non_empty[0] and not _WS_RE.search(non_empty[0]):
            current_section = non_empty[0].strip()
            continue

        if current_section != "ETF":
            continue

        first_cell = cells[0]
        parts = _WS_RE.split(first_cell, maxsplit=1)
        if len(parts) != 2:
            continue
        symbol, name = parts[0].strip(), parts[1].strip()
        if not symbol or not name:
            continue

        isin = cells[1].strip() if len(cells) > 1 else None
        listing_date = _normalize_date(cells[2]) if len(cells) > 2 else None
        market = cells[3].strip() if len(cells) > 3 else None

        records.append(
            {
                "symbol": symbol,
                "name": name,
                "isin": isin or None,
                "listing_date": listing_date,
                "market": market or None,
            }
        )

    return records


class TwseEtfListProvider(BaseDataProvider):
    """Fetches the full list of Taiwan-listed ETFs (master info only)."""

    name = "twse-isin"
    source_type = "network"

    def __init__(self, http_get: Callable[[str], bytes] | None = None) -> None:
        self.http_get = http_get or _default_http_get

    def fetch(self, **params) -> ProviderResult:
        """Fetch the ETF list for ``market`` ("listed"|"otc"|"both", default "both")."""
        market = params.get("market", "both")

        urls: list[tuple[str, str]] = []
        if market in ("listed", "both"):
            urls.append(("listed", LISTED_URL))
        if market in ("otc", "both"):
            urls.append(("otc", OTC_URL))

        if not urls:
            return ProviderResult(
                dataset_type="etf_master",
                source_name="TWSE ISIN",
                source_url=None,
                reliability_level="high",
                errors=[f"TwseEtfListProvider.fetch: unknown market '{market}'"],
            )

        all_records: list[dict] = []
        errors: list[str] = []
        source_urls: list[str] = []

        for _label, url in urls:
            source_urls.append(url)
            try:
                raw = self.http_get(url)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"TwseEtfListProvider.fetch: HTTP request failed for {url}: {exc}")
                continue

            try:
                html = _decode(raw)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"TwseEtfListProvider.fetch: decode failed for {url}: {exc}")
                continue

            try:
                rows = _parse_rows(html)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"TwseEtfListProvider.fetch: parse failed for {url}: {exc}")
                continue

            if not rows:
                errors.append(f"TwseEtfListProvider.fetch: no ETF rows parsed from {url}")
                continue

            for rec in rows:
                rec["source_name"] = self.name
                rec["source_url"] = url
            all_records.extend(rows)

        result = ProviderResult(
            dataset_type="etf_master",
            source_name=self.name,
            source_url="; ".join(source_urls),
            reliability_level="high",
            errors=errors,
        )

        if not all_records:
            return result

        result.records = all_records
        result.data_date = dt.date.today()
        return result
