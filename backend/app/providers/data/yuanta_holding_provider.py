"""Yuanta (元大投信) ETF full-holdings provider (CLAUDE.md §7).

Fetches the FULL constituent list (not just top 10) for Yuanta-issued ETFs
from Yuanta's authoritative PCF/Daily JSON bridge API::

    https://etfapi.yuantaetfs.com/ectranslation/api/bridge?...&FuncId=PCF/Daily&ticker={CODE}

A plain GET with a browser ``User-Agent`` returns JSON (HTTP 200). The
constituents live under ``FundWeights``:

- ``StockWeights[]`` -- equity constituents (primary), each row carries
  ``code`` / ``name`` / ``weights`` (%) / ``qty`` (shares).
- ``FutureWeights[]`` / ``ETFWeights[]`` / ``BondWeights[]`` -- same shape;
  populated for futures / leveraged / fund-of-fund / bond ETFs where
  ``StockWeights`` may be empty.

Data date = ``PCF.trandate`` parsed as ``YYYYMMDD``.

Per CLAUDE.md §7 this provider NEVER fabricates rows. On HTTP error,
non-200, malformed JSON, missing ``FundWeights``, or no parseable rows it
returns an empty ``records`` list with a descriptive ``errors`` entry. A
non-Yuanta ETF will typically yield an error/empty response and is handled
gracefully (empty + error), never a crash.

This is the issuer's own authoritative data, so records carry
``confidence_level="HIGH"`` (above Yahoo's MEDIUM). No API token required.
"""

from __future__ import annotations

import datetime as dt
import json
from typing import Callable
from urllib.parse import quote, urlencode

from app.providers.data.base import BaseDataProvider, ProviderResult

DEFAULT_BASE_URL = "https://etfapi.yuantaetfs.com/ectranslation/api/bridge"

# Weight buckets to harvest from FundWeights, in priority order. StockWeights
# is the primary set; the rest cover futures / leveraged / FoF / bond ETFs.
_WEIGHT_KEYS = ("StockWeights", "FutureWeights", "ETFWeights", "BondWeights")


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


def _parse_trandate(value: str | None) -> dt.date | None:
    if not value:
        return None
    value = str(value).strip()
    try:
        return dt.datetime.strptime(value, "%Y%m%d").date()
    except ValueError:
        return None


def _to_float(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class YuantaHoldingProvider(BaseDataProvider):
    """Fetches FULL ETF holdings from Yuanta's PCF/Daily JSON API.

    Accepts an injectable ``http_get`` callable: ``(url: str) -> bytes``
    (so tests can stub the network). No token required.
    """

    name = "元大投信"
    source_type = "network"

    def __init__(
        self,
        http_get: Callable[[str], bytes] | None = None,
        base_url: str = DEFAULT_BASE_URL,
        **_extra,
    ) -> None:
        self.http_get = http_get or _default_http_get
        self.base_url = base_url

    # ------------------------------------------------------------------
    # URL helper
    # ------------------------------------------------------------------
    def _holding_url(self, symbol: str) -> str:
        params = {
            "APIType": "ETFAPI",
            "CompanyName": "YUANTAFUNDS",
            "PageName": f"/tradeInfo/pcf/{symbol}",
            "DeviceId": "00000000-0000-0000-0000-000000000000",
            "FuncId": "PCF/Daily",
            "AppName": "ETF",
            "Device": "3",
            "Platform": "ETF",
            "ticker": symbol,
            "ndate": "",
        }
        # quote_via=quote so slashes in PageName / FuncId are encoded as %2F.
        return f"{self.base_url}?{urlencode(params, quote_via=quote)}"

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
                return empty([f"HTTP {code} fetching Yuanta PCF API"])
            return empty([f"HTTP request failed: {exc}"])

        if not raw:
            return empty(["empty response from Yuanta"])

        try:
            data = json.loads(raw.decode("utf-8", errors="ignore"))
        except Exception as exc:  # noqa: BLE001
            return empty([f"failed to parse Yuanta JSON: {exc}"])

        if not isinstance(data, dict):
            return empty(["unexpected Yuanta response (not an object)"])

        fund_weights = data.get("FundWeights")
        if not isinstance(fund_weights, dict):
            return empty(["no FundWeights in Yuanta response"])

        pcf = data.get("PCF") if isinstance(data.get("PCF"), dict) else {}
        data_date = _parse_trandate(pcf.get("trandate"))
        holding_date = data_date or dt.date.today()
        fetched_at = dt.datetime.utcnow()

        # Fund-level meta from the PCF block: AUM (totalav) + NAV per unit.
        # Only populated when the issuer reports a real value (never fabricated).
        fund_meta = {
            "aum": _to_float(pcf.get("totalav")),
            "nav": _to_float(pcf.get("nav")),
            "nav_date": data_date,
            "source_name": self.name,
            "source_url": url,
            "fetched_at": fetched_at,
            "confidence_level": "HIGH",
        }

        records: list[dict] = []
        for key in _WEIGHT_KEYS:
            rows = fund_weights.get(key)
            if not isinstance(rows, list):
                continue
            for row in rows:
                if not isinstance(row, dict):
                    continue
                code = row.get("code")
                if code is None:
                    continue
                records.append(
                    {
                        "etf_symbol": symbol,
                        "holding_date": holding_date,
                        "asset_symbol": str(code),
                        "asset_name": row.get("name"),
                        "weight": _to_float(row.get("weights")),
                        "shares": _to_float(row.get("qty")),
                        "source_name": self.name,
                        "source_url": url,
                        "fetched_at": fetched_at,
                        "confidence_level": "HIGH",
                    }
                )

        if not records:
            return empty(["no parseable holdings in Yuanta FundWeights"])

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
