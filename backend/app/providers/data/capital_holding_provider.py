"""Capital (群益投信) ETF full-holdings provider (CLAUDE.md §7).

Fetches the FULL constituent list (not just top 10) for Capital-issued ETFs
from Capital's ``capitalfund.com.tw`` ``/CFWeb/api`` JSON API. Two endpoints
are involved, both **POST** (a GET returns HTTP 405); verified live on
2026-06-15 with a plain server-side request (UA + Referer/Origin of the
Capital site, no token/cookie):

1. Fund list / id map (one call, cached on the instance)::

       POST /CFWeb/api/etf/items   body {}

   Returns a list of ``{fundNo, stockNo, shortName}`` (28 ETFs). ``stockNo``
   is the public ticker (e.g. "00919"); ``fundNo`` (e.g. "195") is the id the
   buyback endpoint expects. REQUIRED to self-filter and resolve fundNo.

2. The daily PCF (申購買回) basket = full holdings::

       POST /CFWeb/api/etf/buyback   body {"fundId": <int fundNo>}

   Returns ``{stocks[], bonds[], futures[], pcf{...}, assets[]}``:
   - ``stocks[]``  : ``{stocNo, stocName, weight, share}``
   - ``bonds[]``   : ``{bondNo, bondName, weight, faceValue}``
   - ``futures[]`` : ``{txEname, txDesc, weight, lot}``
   - ``pcf``       : ``{nav (total AUM), pUnit (NAV/unit), date1}`` -> fund_meta
   - ``assets[]``  : cash/margin (NOT constituents, skipped)

Per CLAUDE.md §7 this provider NEVER fabricates rows. A non-Capital symbol
(absent from ``items``), any network error, or an empty basket yields an empty
``records`` list with a descriptive ``errors`` entry so the caller can fall
back to Yahoo. Records carry ``confidence_level="HIGH"`` (issuer-authoritative).
"""

from __future__ import annotations

import datetime as dt
import json
import re
from typing import Callable

from app.providers.data.base import BaseDataProvider, ProviderResult

DEFAULT_BASE_URL = "https://www.capitalfund.com.tw/CFWeb/api/etf"
_SITE = "https://www.capitalfund.com.tw"

_CODE_RE = re.compile(r"^[0-9]{4,6}[A-Z]?$")


def _default_http_post(url: str, body: dict) -> bytes:
    from urllib.request import Request, urlopen

    data = json.dumps(body).encode("utf-8")
    req = Request(
        url,
        data=data,
        method="POST",
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0 Safari/537.36"
            ),
            "Referer": f"{_SITE}/etf",
            "Origin": _SITE,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    with urlopen(req, timeout=20) as resp:  # noqa: S310
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


def _parse_date(value: str | None) -> dt.date | None:
    if not value:
        return None
    m = re.search(r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})", str(value))
    if not m:
        return None
    try:
        return dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


class CapitalHoldingProvider(BaseDataProvider):
    """Fetches FULL ETF holdings from Capital's /CFWeb/api PCF (buyback) API.

    Accepts an injectable ``http_post`` callable: ``(url, body_dict) -> bytes``
    so tests can stub the network. No API token required.
    """

    name = "群益投信"
    source_type = "network"

    def __init__(
        self,
        http_post: Callable[[str, dict], bytes] | None = None,
        base_url: str = DEFAULT_BASE_URL,
        **_extra,
    ) -> None:
        self.http_post = http_post or _default_http_post
        self.base_url = base_url.rstrip("/")
        # Lazily-loaded {stockNo: fundNo} map, cached for the instance lifetime.
        self._fund_map: dict[str, str] | None = None

    # ------------------------------------------------------------------ maps
    def _load_fund_map(self) -> dict[str, str]:
        if self._fund_map is not None:
            return self._fund_map
        mapping: dict[str, str] = {}
        try:
            raw = self.http_post(f"{self.base_url}/items", {})
            data = json.loads(raw.decode("utf-8", "ignore"))
            items = data.get("data") if isinstance(data, dict) and "data" in data else data
            for it in items or []:
                if not isinstance(it, dict):
                    continue
                code = str(it.get("stockNo") or "").strip()
                fund_no = str(it.get("fundNo") or "").strip()
                if _CODE_RE.match(code) and fund_no:
                    mapping.setdefault(code, fund_no)
        except Exception:  # noqa: BLE001
            mapping = {}
        self._fund_map = mapping
        return mapping

    # ----------------------------------------------------------------- fetch
    def fetch(self, *, symbol: str, **_extra) -> ProviderResult:
        dataset_type = "etf_holdings"
        symbol = str(symbol).strip()
        url = f"{self.base_url}/buyback"

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

        fund_no = self._load_fund_map().get(symbol)
        if not fund_no:
            return empty([f"{symbol} is not a Capital ETF (no fundNo)"])

        try:
            raw = self.http_post(url, {"fundId": int(fund_no)})
            payload = json.loads(raw.decode("utf-8", "ignore"))
        except Exception as exc:  # noqa: BLE001
            return empty([f"Capital buyback request/parse failed: {exc}"])

        data = payload.get("data") if isinstance(payload, dict) and "data" in payload else payload
        if not isinstance(data, dict):
            return empty(["unexpected Capital buyback response"])

        pcf = data.get("pcf") if isinstance(data.get("pcf"), dict) else {}
        data_date = _parse_date(pcf.get("date1")) or _parse_date(pcf.get("date2"))
        holding_date = data_date or dt.date.today()
        fetched_at = dt.datetime.utcnow()

        records: list[dict] = []

        def add(code, name, weight, shares):
            if not code:
                return
            records.append(
                {
                    "etf_symbol": symbol,
                    "holding_date": holding_date,
                    "asset_symbol": str(code).strip(),
                    "asset_name": (str(name).strip() if name is not None else None),
                    "weight": _to_float(weight),
                    "shares": _to_float(shares),
                    "source_name": self.name,
                    "source_url": url,
                    "fetched_at": fetched_at,
                    "confidence_level": "HIGH",
                }
            )

        for s in data.get("stocks") or []:
            if isinstance(s, dict):
                add(s.get("stocNo"), s.get("stocName"), s.get("weight"), s.get("share"))
        for b in data.get("bonds") or []:
            if isinstance(b, dict):
                add(b.get("bondNo"), b.get("bondName"), b.get("weight"), b.get("faceValue"))
        for f in data.get("futures") or []:
            if isinstance(f, dict):
                add(
                    f.get("txEname") or f.get("txDesc"),
                    f.get("txDesc"),
                    f.get("weight"),
                    f.get("lot"),
                )

        if not records:
            return empty([f"no parseable holdings for {symbol}"])

        fund_meta = {
            "aum": _to_float(pcf.get("nav")),
            "nav": _to_float(pcf.get("pUnit")),
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
