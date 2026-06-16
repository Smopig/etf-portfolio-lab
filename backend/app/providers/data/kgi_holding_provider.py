"""KGI (凱基投信) ETF full-holdings provider (CLAUDE.md §7).

Fetches the FULL constituent list (not just top 10) for KGI-issued *equity*
ETFs from KGI's ``kgifund.com.tw`` fund-detail pages. Two steps (verified live
on 2026-06-16, plain server-side GET + browser User-Agent, no token/cookie):

1. Fund code map (cached on the instance). KGI funds are addressed by an
   internal ``fundID`` like ``J015``; the public ticker (e.g. "00915") is not
   accepted directly. We scan ``J001``..``J030`` once, fetching each detail
   page and reading its own public code from the header text ``(00915 …``::

       GET https://www.kgifund.com.tw/Fund/Detail?fundID=J{nnn}

2. Holdings for one fund are SERVER-RENDERED in that same detail page, in an
   HTML table whose Chinese text is HTML-entity encoded (e.g.
   ``&#x80A1;&#x7968;&#x4EE3;&#x865F;`` = 股票代號). Header columns are
   ``股票代號 | 股票名稱 | 股數 | 權重(%)``; the data date (monthly, e.g.
   ``2026/05/31``) appears just above the table.

KGI *bond* ETFs do not render a holdings table on this page, so they yield an
empty result and fall back to Yahoo (same as the equity-only Cathay provider).
Per CLAUDE.md §7 this provider NEVER fabricates rows: a non-KGI symbol, a bond
ETF, any network error or unparseable page yields an empty ``records`` list
with a descriptive ``errors`` entry. Records carry ``confidence_level="HIGH"``.
"""

from __future__ import annotations

import datetime as dt
import html
import re
from typing import Callable

from app.providers.data.base import BaseDataProvider, ProviderResult

DEFAULT_BASE_URL = "https://www.kgifund.com.tw"

# KGI internal fund ids to scan for the public-code map (covers current range
# J001..~J024 with gaps). Cheap one-off per refresh; cached on the instance.
_SCAN_RANGE = range(1, 31)

_CODE_RE = re.compile(r"^[0-9]{4,6}[A-Z]?$")
# The fund's own public code in the detail header, e.g. "(00915 凱基台灣…".
_OWN_CODE_RE = re.compile(r"\((0[0-9]{4}[A-Z]?)\s")


def _default_http_get(url: str) -> bytes:
    import ssl
    from urllib.request import Request, urlopen

    # kgifund.com.tw serves a TLS cert missing the Subject Key Identifier
    # extension, which OpenSSL 3.x rejects under strict verification (curl and
    # older OpenSSL are lenient). This is a read-only fetch of PUBLIC holdings
    # data with no credentials, so we fall back to an unverified context; the
    # §7 parser still never fabricates and drops unparseable rows.
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

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
    with urlopen(req, timeout=20, context=ctx) as resp:  # noqa: S310
        return resp.read()


def _to_float(value) -> float | None:
    if value is None:
        return None
    text = str(value).replace(",", "").replace("%", "").strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _cell_text(cell_html: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", cell_html)).strip()


class KgiHoldingProvider(BaseDataProvider):
    """Fetches FULL equity-ETF holdings from KGI's server-rendered detail pages.

    Accepts an injectable ``http_get`` callable: ``(url: str) -> bytes`` so
    tests can stub the network. No API token required.
    """

    name = "凱基投信"
    source_type = "network"

    def __init__(
        self,
        http_get: Callable[[str], bytes] | None = None,
        base_url: str = DEFAULT_BASE_URL,
        **_extra,
    ) -> None:
        self.http_get = http_get or _default_http_get
        self.base_url = base_url.rstrip("/")
        self._fund_map: dict[str, str] | None = None

    # ------------------------------------------------------------------ maps
    def _detail_url(self, fund_id: str) -> str:
        return f"{self.base_url}/Fund/Detail?fundID={fund_id}"

    def _load_fund_map(self) -> dict[str, str]:
        if self._fund_map is not None:
            return self._fund_map
        mapping: dict[str, str] = {}
        for n in _SCAN_RANGE:
            fid = f"J{n:03d}"
            try:
                html_text = self.http_get(self._detail_url(fid)).decode("utf-8", "ignore")
            except Exception:  # noqa: BLE001
                continue
            m = _OWN_CODE_RE.search(html_text)
            if m and _CODE_RE.match(m.group(1)):
                mapping.setdefault(m.group(1), fid)
        self._fund_map = mapping
        return mapping

    # ----------------------------------------------------------------- fetch
    def fetch(self, *, symbol: str, **_extra) -> ProviderResult:
        dataset_type = "etf_holdings"
        symbol = str(symbol).strip()

        def empty(errors: list[str], url: str | None = None) -> ProviderResult:
            return ProviderResult(
                records=[],
                dataset_type=dataset_type,
                source_name=self.name,
                source_url=url,
                data_date=None,
                reliability_level=None,
                errors=errors,
            )

        fund_id = self._load_fund_map().get(symbol)
        if not fund_id:
            return empty([f"{symbol} is not a KGI ETF (no fundID)"])

        url = self._detail_url(fund_id)
        try:
            page = self.http_get(url).decode("utf-8", "ignore")
        except Exception as exc:  # noqa: BLE001
            code = getattr(exc, "code", None)
            if code is not None:
                return empty([f"HTTP {code} fetching KGI detail"], url)
            return empty([f"HTTP request failed: {exc}"], url)

        return self._parse(symbol, page, url, dataset_type)

    # ----------------------------------------------------------------- parse
    def _parse(self, symbol: str, page: str, url: str, dataset_type: str) -> ProviderResult:
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

        # Locate the holdings table: header (after entity-decode) names a code
        # column AND a 權重 column, and its rows start with a stock code.
        target = None
        for table in re.findall(r"<table.*?</table>", page, re.S):
            rows = re.findall(r"<tr.*?</tr>", table, re.S)
            if len(rows) < 3:
                continue
            header = [
                _cell_text(c) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", rows[0], re.S)
            ]
            header = [h for h in header if h != ""]
            if not header:
                continue
            if any("代" in h for h in header) and any("權重" in h for h in header):
                target = (header, rows)
                break

        if target is None:
            # Bond / not-yet-disclosed ETFs render no holdings table here.
            return empty([f"no holdings table for {symbol} (e.g. KGI bond ETF)"])

        header, rows = target
        weight_idx = next((j for j, h in enumerate(header) if "權重" in h), None)
        shares_idx = next((j for j, h in enumerate(header) if "股數" in h), None)
        if weight_idx is None:
            return empty([f"no 權重 column for {symbol}"])

        # KGI discloses holdings monthly as of last month-end; the page exposes
        # that date in a hidden ``LastMonthLastDay`` input.
        data_date = None
        dm = re.search(r'name="LastMonthLastDay"[^>]*value="(20\d{2})/(\d{1,2})/(\d{1,2})"', page)
        if dm is None:
            dm = re.search(r'value="(20\d{2})/(\d{1,2})/(\d{1,2})"[^>]*name="LastMonthLastDay"', page)
        if dm:
            try:
                data_date = dt.date(int(dm.group(1)), int(dm.group(2)), int(dm.group(3)))
            except ValueError:
                data_date = None

        holding_date = data_date or dt.date.today()
        fetched_at = dt.datetime.utcnow()
        records: list[dict] = []
        for r in rows[1:]:
            cells = [_cell_text(c) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, re.S)]
            cells = [c for c in cells if c != ""]
            if not cells:
                continue
            code = cells[0]
            if not _CODE_RE.match(code):
                continue
            name = cells[1] if len(cells) > 1 else None
            weight = _to_float(cells[weight_idx]) if weight_idx < len(cells) else None
            shares = (
                _to_float(cells[shares_idx])
                if shares_idx is not None and shares_idx < len(cells)
                else None
            )
            records.append(
                {
                    "etf_symbol": symbol,
                    "holding_date": holding_date,
                    "asset_symbol": code,
                    "asset_name": name,
                    "weight": weight,
                    "shares": shares,
                    "source_name": self.name,
                    "source_url": url,
                    "fetched_at": fetched_at,
                    "confidence_level": "HIGH",
                }
            )

        if not records:
            return empty([f"no parseable holdings for {symbol}"])

        return ProviderResult(
            records=records,
            dataset_type=dataset_type,
            source_name=self.name,
            source_url=url,
            data_date=data_date or holding_date,
            reliability_level="high",
            errors=[],
            fund_meta=None,
        )
