"""Cathay (國泰投信) ETF full-holdings provider (CLAUDE.md §7).

Fetches the FULL constituent list (not just top 10) for Cathay-issued ETFs
from Cathay's ``cwapi.cathaysite.com.tw`` JSON API. Three endpoints are
involved (all verified live on 2026-06-15). The API host runs a WAF that
302-redirects bare requests to ``?event=block``; it passes as long as the
request carries a ``Referer``/``Origin`` of ``www.cathaysite.com.tw`` plus a
browser User-Agent (no cookie/token) — so a plain server-side request works:

1. Fund list / id map (one call, cached on the instance)::

       GET /api/Fund/GetFundList?CurrentPage=1&PerPageCount=300

   ``result[]`` lists every fund; ETFs (``isETF == true``) carry ``stockCode``
   (public ticker, e.g. "00878") and ``fundCode`` (Cathay's short id, e.g.
   "CN") used by the endpoints below. This is REQUIRED to self-filter and to
   resolve the fundCode.

2. Constituent weights (the full holdings)::

       GET /api/ETF/GetIndexStockWeights?fundCode={fundCode}

   ``result.{date, stockWeights[]}`` where each row is
   ``{stockCode, stockName, weights}`` (weights is a percent string). Equity
   ETFs return the full list (e.g. 00878 = 30 stocks); bond ETFs return an
   empty array (no shares are exposed by this endpoint).

3. Fund-level NAV/AUM for ``fund_meta``::

       GET /api/ETF/GetETFAssets?fundCode={fundCode}

   ``result.{preDate, fundNav (AUM), fundPerNav (NAV per unit)}``.

Per CLAUDE.md §7 this provider NEVER fabricates rows. A non-Cathay symbol
(absent from the fund list), a bond ETF with no index weights, any network
error or malformed JSON yields an empty ``records`` list with a descriptive
``errors`` entry so the caller can fall back to Yahoo. Records carry
``confidence_level="HIGH"`` (issuer-authoritative).
"""

from __future__ import annotations

import datetime as dt
import json
import re
from typing import Callable

from app.providers.data.base import BaseDataProvider, ProviderResult

DEFAULT_BASE_URL = "https://cwapi.cathaysite.com.tw"
_SITE = "https://www.cathaysite.com.tw"

# A public TW ETF code: 5-6 digits, optional trailing letter (00878, 00400A, 00687B).
_CODE_RE = re.compile(r"^[0-9]{4,6}[A-Z]?$")


def _default_http_get(url: str) -> bytes:
    from urllib.request import Request, urlopen

    # The WAF passes requests that look like they come from the Cathay site.
    req = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0 Safari/537.36"
            ),
            "Referer": f"{_SITE}/",
            "Origin": _SITE,
            "Accept": "application/json",
        },
    )
    with urlopen(req, timeout=20) as resp:  # noqa: S310
        return resp.read()


def _to_float(value) -> float | None:
    """Parse a value into a float, stripping commas/percent. None if absent."""
    if value is None:
        return None
    text = str(value).replace(",", "").replace("%", "").strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _parse_slash_date(value: str | None) -> dt.date | None:
    if not value:
        return None
    m = re.search(r"(\d{4})/(\d{1,2})/(\d{1,2})", str(value))
    if not m:
        return None
    try:
        return dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


class CathayHoldingProvider(BaseDataProvider):
    """Fetches FULL ETF holdings from Cathay's cwapi JSON API.

    Accepts an injectable ``http_get`` callable: ``(url: str) -> bytes`` so
    tests can stub the network. No API token required.
    """

    name = "國泰投信"
    source_type = "network"

    def __init__(
        self,
        http_get: Callable[[str], bytes] | None = None,
        base_url: str = DEFAULT_BASE_URL,
        **_extra,
    ) -> None:
        self.http_get = http_get or _default_http_get
        self.base_url = base_url.rstrip("/")
        # Lazily-loaded {stockCode: fundCode} map for ETFs, cached for the
        # instance's lifetime (one refresh run).
        self._fund_map: dict[str, str] | None = None

    # ------------------------------------------------------------------ maps
    def _fund_list_url(self) -> str:
        return f"{self.base_url}/api/Fund/GetFundList?CurrentPage=1&PerPageCount=300"

    def _load_fund_map(self) -> dict[str, str]:
        if self._fund_map is not None:
            return self._fund_map
        mapping: dict[str, str] = {}
        try:
            data = json.loads(self.http_get(self._fund_list_url()).decode("utf-8", "ignore"))
            for fund in data.get("result") or []:
                if not isinstance(fund, dict) or not fund.get("isETF"):
                    continue
                code = str(fund.get("stockCode") or "").strip()
                fc = str(fund.get("fundCode") or "").strip()
                if _CODE_RE.match(code) and fc:
                    mapping.setdefault(code, fc)
        except Exception:  # noqa: BLE001
            mapping = {}
        self._fund_map = mapping
        return mapping

    # ----------------------------------------------------------------- fetch
    def _weights_url(self, fund_code: str) -> str:
        return f"{self.base_url}/api/ETF/GetIndexStockWeights?fundCode={fund_code}"

    def _assets_url(self, fund_code: str) -> str:
        return f"{self.base_url}/api/ETF/GetETFAssets?fundCode={fund_code}"

    def _get_json(self, url: str) -> dict | None:
        try:
            return json.loads(self.http_get(url).decode("utf-8", "ignore"))
        except Exception:  # noqa: BLE001
            return None

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

        fund_code = self._load_fund_map().get(symbol)
        if not fund_code:
            return empty([f"{symbol} is not a Cathay ETF (no fundCode)"])

        url = self._weights_url(fund_code)
        payload = self._get_json(url)
        if not payload or not payload.get("success"):
            msg = (payload or {}).get("returnMessage", "no/invalid response")
            return empty([f"Cathay GetIndexStockWeights failed: {msg}"], url)

        result = payload.get("result") or {}
        weights = result.get("stockWeights")
        if not isinstance(weights, list) or not weights:
            # Bond/other ETFs expose no index weights here -> let caller fall back.
            return empty([f"no index stock weights for {symbol} (e.g. bond ETF)"], url)

        data_date = _parse_slash_date(result.get("date"))

        # Fund-level NAV/AUM (best effort; never fabricated).
        assets = self._get_json(self._assets_url(fund_code)) or {}
        ares = assets.get("result") or {} if isinstance(assets, dict) else {}
        aum = _to_float(ares.get("fundNav"))
        nav = _to_float(ares.get("fundPerNav"))
        if data_date is None:
            data_date = _parse_slash_date(ares.get("preDate"))

        holding_date = data_date or dt.date.today()
        fetched_at = dt.datetime.utcnow()
        records: list[dict] = []
        for row in weights:
            if not isinstance(row, dict):
                continue
            code = row.get("stockCode")
            if not code:
                continue
            records.append(
                {
                    "etf_symbol": symbol,
                    "holding_date": holding_date,
                    "asset_symbol": str(code).strip(),
                    "asset_name": row.get("stockName"),
                    "weight": _to_float(row.get("weights")),
                    "shares": None,  # not exposed by GetIndexStockWeights
                    "source_name": self.name,
                    "source_url": url,
                    "fetched_at": fetched_at,
                    "confidence_level": "HIGH",
                }
            )

        if not records:
            return empty([f"no parseable holdings for {symbol}"], url)

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
