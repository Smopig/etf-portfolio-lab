"""Fuhua (復華投信) ETF full-holdings provider (CLAUDE.md §7).

Fetches the FULL constituent list (not just top 10) for Fuhua-issued ETFs
from Fuhua's authoritative daily PCF (申購買回參考清單) workbook.

Two endpoints are involved (both verified live on 2026-06-15, no token,
no anti-bot block):

1. Fund list / id map (one call, cached on the instance)::

       GET https://www.fhtrust.com.tw/api/fundList   -> JSON

   ``data["result"]`` is a list of funds; each ETF carries ``etf002`` (the
   public stock code, e.g. "00929") and ``fundID`` (Fuhua's internal id,
   e.g. "ETF21") used by the assets endpoint below.

2. Daily PCF workbook for one fund on one trading day::

       GET https://www.fhtrust.com.tw/api/assetsExcel/{fundID}/{YYYYMMDD}

   Returns a binary ``.xlsx``. When no data exists for that day (weekend,
   holiday, or not-yet-published) it returns HTTP 200 with the literal body
   ``查無資料`` — so we walk recent days backwards until a real workbook is
   found. The workbook layout (verified for both equity and bond ETFs):

   - row 2 (0-indexed): ``日期: 2026/06/12`` (data date)
   - ``基金資產淨值`` / ``基金每單位淨值`` label rows precede their value rows
     (AUM / NAV per unit, captured into ``fund_meta``)
   - a header row whose first cell is ``證券代號`` (equity) or ``證券代碼``
     (bond); equity columns are ``證券代號 | 證券名稱 | 股數 | 金額 | 權重(%)``;
     bond columns differ (面額/結算價格/市值 instead of 股數) but the code,
     name and ``權重(%)`` columns are located by header name so both parse.
   - every row below the header until the end is a constituent.

Per CLAUDE.md §7 this provider NEVER fabricates rows. A non-Fuhua symbol
is not in the fund map and yields an empty result (so the caller can fall
back to Yahoo). Any network error, ``查無資料`` for every probed day, a
malformed workbook, or no parseable rows yields an empty ``records`` list
with a descriptive ``errors`` entry. Records carry ``confidence_level="HIGH"``
(issuer-authoritative).
"""

from __future__ import annotations

import datetime as dt
import io
import json
import re
from typing import Callable

from app.providers.data.base import BaseDataProvider, ProviderResult

DEFAULT_BASE_URL = "https://www.fhtrust.com.tw"

# Body returned (HTTP 200) when a fund has no workbook for the requested day.
_NO_DATA_TOKEN = "查無資料".encode("utf-8")

# A public TW ETF code: five digits, optional trailing letter (e.g. 00929, 00768B).
_CODE_RE = re.compile(r"^0[0-9]{4}[A-Z]?$")

# Number of calendar days to walk backwards looking for a published workbook.
# Covers weekends + the issuer's publish lag (observed up to ~2 trading days).
_MAX_DAYS_BACK = 8


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


def _to_float(value) -> float | None:
    """Parse a workbook cell into a float, stripping commas/percent/currency.

    Handles "135,877,000", "13.395%", "(USD)52,000,000" -> 135877000.0 /
    13.395 / 52000000.0. Returns None when no number is present (never guesses).
    """
    if value is None:
        return None
    text = str(value)
    # Drop a leading currency marker like "(USD)" then keep digits/.-.
    text = re.sub(r"\([A-Za-z]+\)", "", text)
    text = text.replace(",", "").replace("%", "").strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _parse_date_label(text: str | None) -> dt.date | None:
    """Parse '日期: 2026/06/12' (or a bare '2026/06/12') into a date."""
    if not text:
        return None
    m = re.search(r"(\d{4})/(\d{1,2})/(\d{1,2})", str(text))
    if not m:
        return None
    try:
        return dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


class FuhuaHoldingProvider(BaseDataProvider):
    """Fetches FULL ETF holdings from Fuhua's daily PCF workbook API.

    Accepts an injectable ``http_get`` callable: ``(url: str) -> bytes`` so
    tests can stub the network. No API token required.
    """

    name = "復華投信"
    source_type = "network"

    def __init__(
        self,
        http_get: Callable[[str], bytes] | None = None,
        base_url: str = DEFAULT_BASE_URL,
        **_extra,
    ) -> None:
        self.http_get = http_get or _default_http_get
        self.base_url = base_url.rstrip("/")
        # Lazily-loaded {public_code: fundID} map, cached for the instance's
        # lifetime (one refresh run) so we hit /api/fundList only once.
        self._fund_map: dict[str, str] | None = None

    # ------------------------------------------------------------------ maps
    def _fund_list_url(self) -> str:
        return f"{self.base_url}/api/fundList"

    def _load_fund_map(self) -> dict[str, str]:
        if self._fund_map is not None:
            return self._fund_map
        mapping: dict[str, str] = {}
        try:
            raw = self.http_get(self._fund_list_url())
            data = json.loads(raw.decode("utf-8", errors="ignore"))
            funds = data.get("result") if isinstance(data, dict) else None
            if isinstance(funds, list):
                for fund in funds:
                    if not isinstance(fund, dict):
                        continue
                    code = str(fund.get("etf002") or "").strip()
                    fund_id = str(fund.get("fundID") or "").strip()
                    if _CODE_RE.match(code) and fund_id.startswith("ETF"):
                        mapping.setdefault(code, fund_id)
        except Exception:  # noqa: BLE001
            mapping = {}
        self._fund_map = mapping
        return mapping

    # ----------------------------------------------------------------- fetch
    def _assets_url(self, fund_id: str, day: dt.date) -> str:
        return f"{self.base_url}/api/assetsExcel/{fund_id}/{day:%Y%m%d}"

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
            # Not a Fuhua fund (or the fund list was unavailable). Empty result
            # lets the caller fall back to another provider.
            return empty([f"{symbol} is not a Fuhua ETF (no fundID)"])

        # Walk recent days backwards until a published workbook is found.
        today = dt.date.today()
        last_url = None
        raw = None
        for delta in range(_MAX_DAYS_BACK):
            day = today - dt.timedelta(days=delta)
            last_url = self._assets_url(fund_id, day)
            try:
                candidate = self.http_get(last_url)
            except Exception as exc:  # noqa: BLE001
                code = getattr(exc, "code", None)
                if code is not None:
                    return empty([f"HTTP {code} fetching Fuhua assetsExcel"], last_url)
                continue
            if not candidate or candidate[:12].startswith(_NO_DATA_TOKEN):
                continue
            if candidate[:2] != b"PK":  # not an xlsx (zip) payload
                continue
            raw = candidate
            break

        if raw is None:
            return empty(
                [f"no Fuhua workbook found for {symbol} in last {_MAX_DAYS_BACK} days"],
                last_url,
            )

        return self._parse_workbook(symbol, raw, last_url, dataset_type)

    # ----------------------------------------------------------------- parse
    def _parse_workbook(
        self, symbol: str, raw: bytes, url: str | None, dataset_type: str
    ) -> ProviderResult:
        import openpyxl  # imported lazily; only needed when a workbook arrives

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
            wb = openpyxl.load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
            ws = wb.active
            rows = [list(r) for r in ws.iter_rows(values_only=True)]
        except Exception as exc:  # noqa: BLE001
            return empty([f"failed to parse Fuhua workbook: {exc}"])

        # Locate the data date and AUM/NAV labels, and the constituent header.
        data_date: dt.date | None = None
        aum: float | None = None
        nav: float | None = None
        header_idx: int | None = None

        for i, row in enumerate(rows):
            first = next((c for c in row if c is not None), None)
            text = str(first).strip() if first is not None else ""
            if text.startswith("日期") and data_date is None:
                data_date = _parse_date_label(text)
            elif text == "基金資產淨值" and i + 1 < len(rows):
                aum = _to_float(next((c for c in rows[i + 1] if c is not None), None))
            elif text == "基金每單位淨值" and i + 1 < len(rows):
                nav = _to_float(next((c for c in rows[i + 1] if c is not None), None))
            elif text in ("證券代號", "證券代碼") and header_idx is None:
                header_idx = i

        if header_idx is None:
            return empty(["no constituent header row in Fuhua workbook"])

        header = [str(c).strip() if c is not None else "" for c in rows[header_idx]]
        name_idx = 1 if len(header) > 1 else None
        weight_idx = next(
            (j for j, h in enumerate(header) if "權重" in h), None
        )
        shares_idx = next((j for j, h in enumerate(header) if h == "股數"), None)
        if weight_idx is None:
            return empty(["no 權重 column in Fuhua workbook header"])

        holding_date = data_date or dt.date.today()
        fetched_at = dt.datetime.utcnow()
        records: list[dict] = []
        for row in rows[header_idx + 1 :]:
            if not row:
                continue
            code = row[0]
            if code is None or str(code).strip() == "":
                continue
            name = row[name_idx] if name_idx is not None and name_idx < len(row) else None
            weight = _to_float(row[weight_idx]) if weight_idx < len(row) else None
            shares = (
                _to_float(row[shares_idx])
                if shares_idx is not None and shares_idx < len(row)
                else None
            )
            records.append(
                {
                    "etf_symbol": symbol,
                    "holding_date": holding_date,
                    "asset_symbol": str(code).strip(),
                    "asset_name": str(name).strip() if name is not None else None,
                    "weight": weight,
                    "shares": shares,
                    "source_name": self.name,
                    "source_url": url,
                    "fetched_at": fetched_at,
                    "confidence_level": "HIGH",
                }
            )

        if not records:
            return empty(["no parseable holdings in Fuhua workbook"])

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
