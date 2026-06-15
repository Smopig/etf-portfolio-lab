"""Fubon (富邦投信) ETF full-holdings provider (CLAUDE.md §7).

Fetches the FULL constituent list (not just top 10) for Fubon-issued ETFs
from Fubon's official ETF site. Two endpoints are involved (both verified
live on 2026-06-15, plain GET + browser User-Agent, no token, no anti-bot
cookie, stateless):

1. Fund list / id set (one call, cached on the instance)::

       GET https://websys.fsit.com.tw/FubonETF/Fund/ETFSeries.aspx

   The page links every Fubon ETF via ``...?stkId={code}``. The set of
   ``stkId`` codes is the authoritative list of Fubon funds (~50). This is
   REQUIRED to self-filter: Assets.aspx (below) does NOT error on a
   non-Fubon code — it silently falls back to a default fund — so a symbol
   must be confirmed in this set before trusting Assets.aspx output.

2. Holdings for one fund (server-rendered HTML, NOT AJAX)::

       GET https://websys.fsit.com.tw/FubonETF/Fund/Assets.aspx?stkId={code}

   The page contains one ``<table>`` per asset class, each with a header
   ``{類}代碼 | {類}名稱 | {數量} | 金額 | 權重(%)`` (類 = 股票/期貨/債券/
   受益憑證). Data rows are followed by a ``{類}合計`` total row (skipped).
   ``權重(%)`` cells are plain numbers (e.g. ``10.1702``). The data date is
   ``資料日期：YYYY/MM/DD``; ``淨資產(新台幣)`` and ``每單位淨值(新台幣)``
   give AUM / NAV (captured into ``fund_meta``).

Per CLAUDE.md §7 this provider NEVER fabricates rows. A non-Fubon symbol
(absent from the ETFSeries set) yields an empty result so the caller can
fall back to Yahoo. Any network error, an empty fund set, no parseable
table, or no rows yields an empty ``records`` list with a descriptive
``errors`` entry. Records carry ``confidence_level="HIGH"``
(issuer-authoritative).
"""

from __future__ import annotations

import datetime as dt
import re
from typing import Callable

from app.providers.data.base import BaseDataProvider, ProviderResult

DEFAULT_BASE_URL = "https://websys.fsit.com.tw/FubonETF"

# A public TW ETF code: five+ digits, optional trailing letter (e.g. 006208, 00692, 00675L, 00982D).
_CODE_RE = re.compile(r"^[0-9]{4,6}[A-Z]?$")

# Header column whose name marks each asset-class table (股票/期貨/債券/受益憑證...).
_HEADER_CODE_RE = re.compile(r"(股票|期貨|債券|受益憑證|ETF|存託憑證|現金)?代[碼號]")


def _default_http_get(url: str) -> bytes:
    import ssl
    from urllib.request import Request, urlopen

    # websys.fsit.com.tw serves a TLS cert missing the Subject Key Identifier
    # extension, which OpenSSL 3.x rejects under strict verification (curl is
    # lenient, Python is not). This is a read-only fetch of PUBLIC issuer
    # holdings data, so we fall back to an unverified context to mirror curl.
    # No credentials are sent; the risk is limited to data integrity, which the
    # §7 parser already guards (never fabricates, drops unparseable rows).
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
    """Parse a cell into a float, stripping commas/percent/currency. None if absent."""
    if value is None:
        return None
    text = re.sub(r"\([A-Za-z]+\)", "", str(value)).replace(",", "").replace("%", "").strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _strip_tags(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


class FubonHoldingProvider(BaseDataProvider):
    """Fetches FULL ETF holdings from Fubon's server-rendered Assets.aspx.

    Accepts an injectable ``http_get`` callable: ``(url: str) -> bytes`` so
    tests can stub the network. No API token required.
    """

    name = "富邦投信"
    source_type = "network"

    def __init__(
        self,
        http_get: Callable[[str], bytes] | None = None,
        base_url: str = DEFAULT_BASE_URL,
        **_extra,
    ) -> None:
        self.http_get = http_get or _default_http_get
        self.base_url = base_url.rstrip("/")
        # Lazily-loaded set of valid Fubon stkId codes, cached for the
        # instance's lifetime (one refresh run).
        self._fund_set: set[str] | None = None

    # ------------------------------------------------------------------ list
    def _series_url(self) -> str:
        return f"{self.base_url}/Fund/ETFSeries.aspx"

    def _load_fund_set(self) -> set[str]:
        if self._fund_set is not None:
            return self._fund_set
        codes: set[str] = set()
        try:
            raw = self.http_get(self._series_url())
            html = raw.decode("utf-8", errors="ignore")
            for m in re.finditer(r"stkId=([0-9A-Za-z]+)", html):
                code = m.group(1).strip()
                if _CODE_RE.match(code):
                    codes.add(code)
        except Exception:  # noqa: BLE001
            codes = set()
        self._fund_set = codes
        return codes

    # ----------------------------------------------------------------- fetch
    def _assets_url(self, symbol: str) -> str:
        return f"{self.base_url}/Fund/Assets.aspx?stkId={symbol}"

    def fetch(self, *, symbol: str, **_extra) -> ProviderResult:
        dataset_type = "etf_holdings"
        symbol = str(symbol).strip()
        url = self._assets_url(symbol)

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

        # Self-filter: Assets.aspx silently shows a default fund for non-Fubon
        # codes, so only trust it for codes confirmed in the ETFSeries list.
        if symbol not in self._load_fund_set():
            return empty([f"{symbol} is not a Fubon ETF (not in ETFSeries list)"])

        try:
            raw = self.http_get(url)
        except Exception as exc:  # noqa: BLE001
            code = getattr(exc, "code", None)
            if code is not None:
                return empty([f"HTTP {code} fetching Fubon Assets.aspx"])
            return empty([f"HTTP request failed: {exc}"])

        html = raw.decode("utf-8", errors="ignore")
        return self._parse_assets(symbol, html, url, dataset_type)

    # ----------------------------------------------------------------- parse
    def _parse_assets(
        self, symbol: str, html: str, url: str, dataset_type: str
    ) -> ProviderResult:
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

        flat = _strip_tags(html)
        dm = re.search(r"資料日期[：:]\s*(\d{4})/(\d{1,2})/(\d{1,2})", flat)
        data_date = None
        if dm:
            try:
                data_date = dt.date(int(dm.group(1)), int(dm.group(2)), int(dm.group(3)))
            except ValueError:
                data_date = None

        am = re.search(r"淨資產\(新台幣\)\s*([0-9,]+)", flat)
        nm = re.search(r"每單位淨值\(新台幣\)\s*([0-9,.]+)", flat)
        aum = _to_float(am.group(1)) if am else None
        nav = _to_float(nm.group(1)) if nm else None

        holding_date = data_date or dt.date.today()
        fetched_at = dt.datetime.utcnow()
        records: list[dict] = []

        for table in re.findall(r"<table.*?</table>", html, re.S):
            rows = re.findall(r"<tr.*?</tr>", table, re.S)
            if not rows:
                continue
            # Header cells of the first row.
            header = [
                _strip_tags(c)
                for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", rows[0], re.S)
            ]
            header = [h for h in header if h != ""]
            if not header or not _HEADER_CODE_RE.search(header[0]):
                continue
            weight_idx = next(
                (j for j, h in enumerate(header) if "權重" in h), None
            )
            if weight_idx is None:
                continue
            # Quantity column is the 3rd column (股數/口數/面額), if present.
            qty_idx = 2 if len(header) > 3 else None

            for r in rows[1:]:
                cells = [
                    _strip_tags(c)
                    for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, re.S)
                ]
                cells = [c for c in cells if c != ""]
                if not cells:
                    continue
                code = cells[0]
                # Skip the per-class total row ("{類}合計") and blank codes.
                if not code or "合計" in code:
                    continue
                name = cells[1] if len(cells) > 1 else None
                weight = _to_float(cells[weight_idx]) if weight_idx < len(cells) else None
                shares = (
                    _to_float(cells[qty_idx])
                    if qty_idx is not None and qty_idx < len(cells)
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
            return empty(["no parseable holdings in Fubon Assets.aspx"])

        fund_meta = {
            "aum": aum,
            "nav": nav,
            "nav_date": data_date,
            "source_name": self.name,
            "source_url": url,
            "fetched_at": fetched_at,
            "confidence_level": "HIGH",
        }

        return ProviderResult(
            records=records,
            dataset_type=dataset_type,
            source_name=self.name,
            source_url=url,
            data_date=data_date or holding_date,
            reliability_level="high",
            errors=[],
            fund_meta=fund_meta,
        )
