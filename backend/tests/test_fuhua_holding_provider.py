"""Tests for FuhuaHoldingProvider (offline, no network, CLAUDE.md §7).

Covers: happy path (equity workbook fully parsed with code/name/weight/shares,
data date + AUM/NAV from the header block, confidence HIGH), the bond workbook
schema (證券代碼 header, no 股數 column -> shares None), a non-Fuhua symbol
(absent from the fund map -> empty + error, so the caller falls back to Yahoo),
查無資料 on every probed day (-> empty + error), and the date walk-back (first
day 查無資料, an earlier day has the workbook). The provider must NEVER
fabricate rows.

Fixtures are built with openpyxl in the real workbook layout verified live
against ``www.fhtrust.com.tw`` on 2026-06-15 (equity 00929/ETF21, bond
00768B/ETF14).
"""

from __future__ import annotations

import datetime as dt
import io
import json

import openpyxl

from app.providers.data.fuhua_holding_provider import FuhuaHoldingProvider

_FUND_LIST = json.dumps(
    {
        "result": [
            {"etf002": "00929", "fundID": "ETF21", "twNameFull": "復華台灣科技優息ETF基金"},
            {"etf002": "00768B", "fundID": "ETF14", "twNameFull": "復華美國20年期以上公債ETF基金"},
            # A non-ETF row (no etf002) must be ignored, not crash.
            {"twName": "某貨幣基金", "fundID": "MMF1"},
        ]
    }
).encode("utf-8")


def _equity_workbook(date_label: str = "日期: 2026/06/12") -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["復華台灣科技優息ETF基金（證劵代碼：00929）"])
    ws.append([])
    ws.append([date_label])
    ws.append(["基金資產淨值"])
    ws.append(["135,423,578,706"])
    ws.append(["基金在外流通單位數"])
    ws.append(["4,580,639,000"])
    ws.append(["基金每單位淨值"])
    ws.append(["29.56"])
    ws.append([])
    ws.append(["證券代號", "證券名稱", "股數", "金額", "權重(%)"])
    ws.append(["2303", "聯華電子", "135,877,000", "18,139,579,500", "13.395%"])
    ws.append(["2454", "聯發科技", "3,249,000", "13,580,820,000", "10.028%"])
    ws.append(["2357", "華碩電腦", "11,044,000", "8,669,540,000", "6.402%"])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _bond_workbook() -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["復華美國20年期以上公債ETF基金（證劵代碼：00768B）"])
    ws.append([])
    ws.append(["日期: 2026/06/12"])
    ws.append(["基金資產淨值"])
    ws.append(["38,308,897,144"])
    ws.append(["基金每單位淨值"])
    ws.append(["50.1688"])
    ws.append([])
    ws.append(
        ["證券代碼", "證券名稱", "面額", "債券結算價格", "債券應收利息(NTD)", "債券市值 (NTD)", "權重(%)"]
    )
    ws.append(["US912810UM89", "T 4 3/4 08/15/55", "(USD)52,000,000", "96.4688", "25,471,345", "1,586,980,395", "4.209%"])
    ws.append(["US912810UK24", "T 4 3/4 05/15/55", "(USD)52,000,000", "96.4375", "6,157,846", "1,586,466,310", "4.157%"])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _http_get_factory(assets_by_date: dict[str, bytes], *, fund_list: bytes = _FUND_LIST):
    """Build a fake http_get dispatching on URL.

    ``assets_by_date`` maps a ``YYYYMMDD`` string to the workbook bytes for that
    day. A requested day not present returns the 查無資料 token (HTTP 200 body).
    """
    calls: list[str] = []

    def fake_http_get(url: str) -> bytes:
        calls.append(url)
        if url.endswith("/api/fundList"):
            return fund_list
        if "/api/assetsExcel/" in url:
            day = url.rsplit("/", 1)[-1]
            return assets_by_date.get(day, "查無資料".encode("utf-8"))
        raise AssertionError(f"unexpected url {url}")

    return fake_http_get, calls


def test_happy_path_equity_workbook():
    today = dt.date.today()
    day = today.strftime("%Y%m%d")
    fake, calls = _http_get_factory({day: _equity_workbook()})
    provider = FuhuaHoldingProvider(http_get=fake)
    result = provider.fetch(symbol="00929")

    assert result.dataset_type == "etf_holdings"
    assert result.source_name == "復華投信"
    assert result.reliability_level == "high"
    assert result.errors == []
    assert len(result.records) == 3

    rec = result.records[0]
    assert rec["etf_symbol"] == "00929"
    assert rec["asset_symbol"] == "2303"
    assert rec["asset_name"] == "聯華電子"
    assert rec["weight"] == 13.395
    assert rec["shares"] == 135877000.0
    assert rec["confidence_level"] == "HIGH"
    assert rec["holding_date"].isoformat() == "2026-06-12"
    assert result.data_date.isoformat() == "2026-06-12"

    # fund_meta from the header block (AUM + NAV per unit), never fabricated.
    assert result.fund_meta["aum"] == 135423578706.0
    assert result.fund_meta["nav"] == 29.56
    assert result.fund_meta["nav_date"].isoformat() == "2026-06-12"

    # The fund list resolved 00929 -> ETF21 in the assets URL.
    assert any("/api/assetsExcel/ETF21/" in u for u in calls)


def test_bond_workbook_schema_no_shares():
    today = dt.date.today().strftime("%Y%m%d")
    fake, _ = _http_get_factory({today: _bond_workbook()})
    provider = FuhuaHoldingProvider(http_get=fake)
    result = provider.fetch(symbol="00768B")

    assert len(result.records) == 2
    rec = result.records[0]
    assert rec["asset_symbol"] == "US912810UM89"
    assert rec["asset_name"] == "T 4 3/4 08/15/55"
    assert rec["weight"] == 4.209
    # Bond schema has 面額, not 股數 -> shares is None (never invented).
    assert rec["shares"] is None
    assert rec["confidence_level"] == "HIGH"


def test_non_fuhua_symbol_returns_empty_with_error():
    today = dt.date.today().strftime("%Y%m%d")
    fake, calls = _http_get_factory({today: _equity_workbook()})
    provider = FuhuaHoldingProvider(http_get=fake)
    result = provider.fetch(symbol="0050")

    assert result.records == []
    assert result.errors
    # Resolved via the fund map; no assetsExcel call wasted for a non-Fuhua fund.
    assert not any("/api/assetsExcel/" in u for u in calls)


def test_no_data_for_every_day_returns_empty_with_error():
    fake, _ = _http_get_factory({})  # every day -> 查無資料
    provider = FuhuaHoldingProvider(http_get=fake)
    result = provider.fetch(symbol="00929")

    assert result.records == []
    assert result.errors


def test_date_walk_back_to_earlier_published_day():
    today = dt.date.today()
    earlier = (today - dt.timedelta(days=2)).strftime("%Y%m%d")
    # Only an earlier day has a workbook; today/yesterday return 查無資料.
    fake, _ = _http_get_factory({earlier: _equity_workbook("日期: 2026/06/10")})
    provider = FuhuaHoldingProvider(http_get=fake)
    result = provider.fetch(symbol="00929")

    assert len(result.records) == 3
    assert result.data_date.isoformat() == "2026-06-10"
