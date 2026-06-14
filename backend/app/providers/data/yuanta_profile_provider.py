"""Yuanta (元大投信) ETF profile provider (CLAUDE.md §7).

Fetches static fund-profile data for ALL Yuanta-issued ETFs in a SINGLE call
to Yuanta's ETFBackstage bridge endpoint::

    https://etfapi.yuantaetfs.com/ectranslation/api/bridge
        ?APIType=ETFBackstage&CompanyName=YUANTAFUNDS&...
        &FuncId=ETFInformation/GetETFInformation

A plain GET with a browser ``User-Agent`` returns JSON (HTTP 200):
``{"ResultCode": 0, "Data": [ {...54 funds...} ]}``. Per-fund keys (verified
live against ``etfapi.yuantaetfs.com`` on 2026-06-14):

- ``STK_CD``               -- ETF code ("0050"), used as the join key.
- ``INDEX_FUND_NAME``      -- 追蹤指數 (tracking index).
- ``INDEX_PREPARE_COMPANY``-- 指數公司 (index provider).
- ``MANAGEMENT_FEE_TEXT``  -- e.g. "約0.0716% (資料日期：2026/06/12)"; the
  numeric % is regex-extracted (None if unparseable — NEVER fabricated).
- ``LIST_DATE``            -- 掛牌日 (YYYYMMDD).
- ``SETUP_DATE``           -- 成立日 (YYYYMMDD).

Per CLAUDE.md §7 this provider NEVER fabricates data. On HTTP error, non-200,
malformed JSON, or unexpected structure it returns an empty ``records`` list
plus a descriptive ``errors`` entry. Records carry ``confidence_level="HIGH"``
(issuer-authoritative).
"""

from __future__ import annotations

import datetime as dt
import json
import re
from typing import Callable
from urllib.parse import quote, urlencode

from app.providers.data.base import BaseDataProvider, ProviderResult

DEFAULT_BASE_URL = "https://etfapi.yuantaetfs.com/ectranslation/api/bridge"

# Matches the first percentage figure in MANAGEMENT_FEE_TEXT, e.g. "0.0716%".
_FEE_RE = re.compile(r"([0-9]+(?:\.[0-9]+)?)\s*%")


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


def _parse_yyyymmdd(value: str | None) -> dt.date | None:
    if not value:
        return None
    try:
        return dt.datetime.strptime(str(value).strip(), "%Y%m%d").date()
    except ValueError:
        return None


def _parse_fee_pct(text: str | None) -> float | None:
    """Extract the numeric % from MANAGEMENT_FEE_TEXT, or None if absent.

    Returns the percentage as a float (e.g. "約0.0716%" -> 0.0716). NEVER
    guesses: any text without a parseable percentage yields None.
    """
    if not text:
        return None
    match = _FEE_RE.search(str(text))
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


class YuantaProfileProvider(BaseDataProvider):
    """Fetches profile data for ALL Yuanta ETFs in one ETFBackstage call.

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

    def _profile_url(self) -> str:
        params = {
            "APIType": "ETFBackstage",
            "CompanyName": "YUANTAFUNDS",
            "DeviceId": "00000000-0000-0000-0000-000000000000",
            "AppName": "ETF",
            "Device": "3",
            "Platform": "ETF",
            "FuncId": "ETFInformation/GetETFInformation",
        }
        return f"{self.base_url}?{urlencode(params, quote_via=quote)}"

    def fetch(self, **_extra) -> ProviderResult:
        dataset_type = "etf_profile"
        url = self._profile_url()

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
                return empty([f"HTTP {code} fetching Yuanta ETFBackstage API"])
            return empty([f"HTTP request failed: {exc}"])

        if not raw:
            return empty(["empty response from Yuanta ETFBackstage"])

        try:
            data = json.loads(raw.decode("utf-8", errors="ignore"))
        except Exception as exc:  # noqa: BLE001
            return empty([f"failed to parse Yuanta ETFBackstage JSON: {exc}"])

        if not isinstance(data, dict):
            return empty(["unexpected Yuanta ETFBackstage response (not an object)"])

        funds = data.get("Data")
        if not isinstance(funds, list):
            return empty(["no Data array in Yuanta ETFBackstage response"])

        fetched_at = dt.datetime.utcnow()
        records: list[dict] = []
        for fund in funds:
            if not isinstance(fund, dict):
                continue
            symbol = fund.get("STK_CD")
            if not symbol:
                continue
            records.append(
                {
                    "symbol": str(symbol).strip(),
                    "tracking_index": (fund.get("INDEX_FUND_NAME") or None),
                    "index_provider": (fund.get("INDEX_PREPARE_COMPANY") or None),
                    "listing_date": _parse_yyyymmdd(fund.get("LIST_DATE")),
                    "setup_date": _parse_yyyymmdd(fund.get("SETUP_DATE")),
                    "management_fee": _parse_fee_pct(fund.get("MANAGEMENT_FEE_TEXT")),
                    "source_name": "元大投信",
                    "source_url": url,
                    "fetched_at": fetched_at,
                    "confidence_level": "HIGH",
                }
            )

        if not records:
            return empty(["no parseable funds in Yuanta ETFBackstage Data"])

        return ProviderResult(
            records=records,
            dataset_type=dataset_type,
            source_name=self.name,
            source_url=url,
            data_date=None,
            reliability_level="high",
            errors=[],
        )
