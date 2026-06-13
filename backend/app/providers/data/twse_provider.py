"""TWSE (Taiwan Stock Exchange) ETF holdings/constituents provider.

Per CLAUDE.md §7: never fabricates holdings. On HTTP failure or unparseable
payload, returns empty ``records`` with ``errors`` populated.

Remote format assumption
-------------------------
TWSE's OpenAPI publishes ETF constituent data as a JSON array of objects,
similar to::

    [
      {"Code": "2330", "Name": "台積電", "Weight": "12.34", ...},
      ...
    ]

This provider expects ``http_get`` to return raw JSON bytes representing
such an array, where each object has at least a stock code field
(``"Code"``/``"code"``/``"stock_code"``) and a weight field
(``"Weight"``/``"weight"``/``"Percent"``). Field names are matched
case-insensitively against this set of aliases. If TWSE's actual schema
differs, this parser will yield zero usable records and surface an error
rather than guessing field meanings.
"""

from __future__ import annotations

import datetime as dt
import json
from typing import Callable

from app.providers.data.base import BaseDataProvider, ProviderResult

DEFAULT_BASE_URL = "https://openapi.twse.com.tw/v1/exchangeReport/ETF"

_CODE_KEYS = {"code", "stock_code", "asset_symbol", "stockno", "symbol"}
_NAME_KEYS = {"name", "stock_name", "asset_name"}
_WEIGHT_KEYS = {"weight", "percent", "percentage", "ratio"}


def _default_http_get(url: str) -> bytes:
    from urllib.request import Request, urlopen

    req = Request(url, headers={"User-Agent": "etf-portfolio-lab/1.0"})
    with urlopen(req, timeout=10) as resp:  # noqa: S310
        return resp.read()


def _find_key(obj: dict, candidates: set[str]) -> str | None:
    for key in obj:
        if key.lower() in candidates:
            return key
    return None


class TwseProvider(BaseDataProvider):
    """Fetches ETF constituent/holdings data from a TWSE-style JSON endpoint.

    Accepts an injectable ``http_get`` callable: ``(url: str) -> bytes``.
    """

    name = "twse"
    source_type = "network"

    def __init__(
        self,
        http_get: Callable[[str], bytes] | None = None,
        base_url: str = DEFAULT_BASE_URL,
    ) -> None:
        self.http_get = http_get or _default_http_get
        self.base_url = base_url

    def fetch(
        self,
        *,
        symbol: str,
        holding_date: dt.date | None = None,
        **_extra,
    ) -> ProviderResult:
        dataset_type = "etf_holdings"
        source_url = f"{self.base_url}?symbol={symbol}"

        try:
            raw = self.http_get(source_url)
        except Exception as exc:  # noqa: BLE001
            return ProviderResult(
                records=[],
                dataset_type=dataset_type,
                source_name=self.name,
                source_url=source_url,
                data_date=None,
                reliability_level=None,
                errors=[f"HTTP request failed: {exc}"],
            )

        if not raw:
            return ProviderResult(
                records=[],
                dataset_type=dataset_type,
                source_name=self.name,
                source_url=source_url,
                data_date=None,
                reliability_level=None,
                errors=["empty response body"],
            )

        try:
            payload = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            return ProviderResult(
                records=[],
                dataset_type=dataset_type,
                source_name=self.name,
                source_url=source_url,
                data_date=None,
                reliability_level=None,
                errors=[f"failed to parse JSON response: {exc}"],
            )

        if not isinstance(payload, list) or not payload:
            return ProviderResult(
                records=[],
                dataset_type=dataset_type,
                source_name=self.name,
                source_url=source_url,
                data_date=None,
                reliability_level=None,
                errors=["expected a non-empty JSON array of constituent rows"],
            )

        effective_date = holding_date or dt.date.today()
        records: list[dict] = []
        errors: list[str] = []

        for i, item in enumerate(payload):
            if not isinstance(item, dict):
                errors.append(f"row {i}: not an object, skipped")
                continue
            code_key = _find_key(item, _CODE_KEYS)
            if code_key is None:
                errors.append(f"row {i}: no recognizable stock-code field, skipped")
                continue
            name_key = _find_key(item, _NAME_KEYS)
            weight_key = _find_key(item, _WEIGHT_KEYS)

            weight = None
            if weight_key is not None:
                try:
                    weight = float(item[weight_key])
                except (TypeError, ValueError):
                    weight = None

            records.append(
                {
                    "etf_symbol": symbol,
                    "holding_date": effective_date,
                    "asset_symbol": str(item[code_key]),
                    "asset_name": item.get(name_key) if name_key else None,
                    "weight": weight,
                    "source_name": self.name,
                    "source_url": source_url,
                }
            )

        if not records:
            errors.append("no usable rows parsed from response")

        return ProviderResult(
            records=records,
            dataset_type=dataset_type,
            source_name=self.name,
            source_url=source_url,
            data_date=effective_date if records else None,
            reliability_level="medium" if records else None,
            errors=errors,
        )


# Alias for clarity in factory registration.
FundCompanyProvider = TwseProvider
