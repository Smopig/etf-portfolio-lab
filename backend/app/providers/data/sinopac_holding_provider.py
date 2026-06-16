"""SinoPac (永豐投信) ETF full-holdings provider (CLAUDE.md §7).

Fetches the FULL constituent list (not just top 10) for SinoPac-issued ETFs
(equity AND bond) from SinoPac's ETF site PCF (申購買回) page. Verified live on
2026-06-16 with plain server-side requests (browser User-Agent, no token):

1. Fund list (one GET, cached on the instance). The PCF page embeds a
   ``<select name="fundId">`` whose options are the public tickers + names::

       GET https://sitc.sinopac.com/SinopacEtfs/Etfs/Pcf

   e.g. 00930/00907/00901/00888/00858/006204/00958B/00857B/...

2. Holdings for one fund are server-rendered after POSTing the ticker (a bare
   GET shows a default fund, so the POST is required to select)::

       POST https://sitc.sinopac.com/SinopacEtfs/Etfs/Pcf   form: fundId={code}

   The table header is ``證券代碼 | 證券名稱 | 股數 | 佔基金淨資產之權重(%)``
   (bond funds list ISIN codes in 證券代碼). The data date appears as
   ``資料日期：YYYY/MM/DD``.

Per CLAUDE.md §7 this provider NEVER fabricates rows: a non-SinoPac symbol
(absent from the fundId list), any network error, or an unparseable page yields
an empty ``records`` list with a descriptive ``errors`` entry so the caller can
fall back to Yahoo. Records carry ``confidence_level="HIGH"``.
"""

from __future__ import annotations

import datetime as dt
import re
from typing import Callable
from urllib.parse import urlencode

from app.providers.data.base import BaseDataProvider, ProviderResult

DEFAULT_PCF_URL = "https://sitc.sinopac.com/SinopacEtfs/Etfs/Pcf"

_CODE_RE = re.compile(r"^[0-9]{4,6}[A-Z]?$")


def _default_http_request(url: str, data: dict | None = None) -> bytes:
    from urllib.request import Request, urlopen

    body = urlencode(data).encode("utf-8") if data is not None else None
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0 Safari/537.36"
        ),
        "Referer": DEFAULT_PCF_URL,
    }
    if data is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    req = Request(url, data=body, headers=headers, method="POST" if data is not None else "GET")
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


def _cell(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html)).strip()


class SinopacHoldingProvider(BaseDataProvider):
    """Fetches FULL ETF holdings from SinoPac's PCF page (GET list + POST fund).

    Accepts an injectable ``http_request`` callable: ``(url, data|None) -> bytes``
    (data is None for GET, a dict for a form POST) so tests can stub the network.
    No API token required.
    """

    name = "永豐投信"
    source_type = "network"

    def __init__(
        self,
        http_request: Callable[[str, dict | None], bytes] | None = None,
        pcf_url: str = DEFAULT_PCF_URL,
        **_extra,
    ) -> None:
        self.http_request = http_request or _default_http_request
        self.pcf_url = pcf_url
        self._fund_set: set[str] | None = None

    # ------------------------------------------------------------------ list
    def _load_fund_set(self) -> set[str]:
        if self._fund_set is not None:
            return self._fund_set
        codes: set[str] = set()
        try:
            html = self.http_request(self.pcf_url, None).decode("utf-8", "ignore")
            m = re.search(r'<select[^>]*name="fundId"[^>]*>(.*?)</select>', html, re.S)
            if m:
                for value in re.findall(r'<option[^>]*value="([^"]+)"', m.group(1)):
                    code = value.strip()
                    if _CODE_RE.match(code):
                        codes.add(code)
        except Exception:  # noqa: BLE001
            codes = set()
        self._fund_set = codes
        return codes

    # ----------------------------------------------------------------- fetch
    def fetch(self, *, symbol: str, **_extra) -> ProviderResult:
        dataset_type = "etf_holdings"
        symbol = str(symbol).strip()

        def empty(errors: list[str]) -> ProviderResult:
            return ProviderResult(
                records=[],
                dataset_type=dataset_type,
                source_name=self.name,
                source_url=self.pcf_url,
                data_date=None,
                reliability_level=None,
                errors=errors,
            )

        if symbol not in self._load_fund_set():
            return empty([f"{symbol} is not a SinoPac ETF (not in fundId list)"])

        try:
            html = self.http_request(self.pcf_url, {"fundId": symbol}).decode("utf-8", "ignore")
        except Exception as exc:  # noqa: BLE001
            code = getattr(exc, "code", None)
            if code is not None:
                return empty([f"HTTP {code} fetching SinoPac PCF"])
            return empty([f"HTTP request failed: {exc}"])

        return self._parse(symbol, html, dataset_type)

    # ----------------------------------------------------------------- parse
    def _parse(self, symbol: str, html: str, dataset_type: str) -> ProviderResult:
        def empty(errors: list[str]) -> ProviderResult:
            return ProviderResult(
                records=[],
                dataset_type=dataset_type,
                source_name=self.name,
                source_url=self.pcf_url,
                data_date=None,
                reliability_level=None,
                errors=errors,
            )

        dm = re.search(r"資料日期[：:]\s*(\d{4})/(\d{1,2})/(\d{1,2})", html)
        data_date = None
        if dm:
            try:
                data_date = dt.date(int(dm.group(1)), int(dm.group(2)), int(dm.group(3)))
            except ValueError:
                data_date = None

        # Locate the holdings table: header names a 證券代 column AND a 權重 column.
        target = None
        for table in re.findall(r"<table.*?</table>", html, re.S):
            rows = re.findall(r"<tr.*?</tr>", table, re.S)
            if len(rows) < 2:
                continue
            header = [_cell(c) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", rows[0], re.S)]
            header = [h for h in header if h != ""]
            if any("證券代" in h or "代碼" in h for h in header) and any("權重" in h for h in header):
                target = (header, rows)
                break

        if target is None:
            return empty([f"no holdings table for {symbol}"])

        header, rows = target
        weight_idx = next((j for j, h in enumerate(header) if "權重" in h), None)
        shares_idx = next((j for j, h in enumerate(header) if "股數" in h), None)
        if weight_idx is None:
            return empty([f"no 權重 column for {symbol}"])

        holding_date = data_date or dt.date.today()
        fetched_at = dt.datetime.utcnow()
        records: list[dict] = []
        for r in rows[1:]:
            # Keep cells positionally (do NOT drop empties) so the header column
            # indices stay aligned — bond rows have a blank 股數 cell.
            cells = [_cell(c) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, re.S)]
            if not any(cells):
                continue
            code = cells[0] if cells else ""
            # Skip total/summary rows; accept stock codes and bond ISINs.
            if not code or "合計" in code or "總" in code:
                continue
            name = cells[1] if len(cells) > 1 else None
            weight = _to_float(cells[weight_idx]) if weight_idx < len(cells) else None
            shares = (
                _to_float(cells[shares_idx])
                if shares_idx is not None and shares_idx < len(cells)
                else None
            )
            if weight is None and shares is None:
                continue
            records.append(
                {
                    "etf_symbol": symbol,
                    "holding_date": holding_date,
                    "asset_symbol": code,
                    "asset_name": name,
                    "weight": weight,
                    "shares": shares,
                    "source_name": self.name,
                    "source_url": self.pcf_url,
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
            source_url=self.pcf_url,
            data_date=data_date or holding_date,
            reliability_level="high",
            errors=[],
            fund_meta=None,
        )
