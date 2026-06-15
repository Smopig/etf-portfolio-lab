"""Tests for CapitalHoldingProvider (offline, no network, CLAUDE.md §7).

Covers: happy path (buyback PCF parsed across stocks + futures with
code/name/weight/shares, AUM/NAV/date from pcf, confidence HIGH), the bond
schema (bonds[] with bondNo/faceValue), a non-Capital symbol (absent from
items -> empty + error, no buyback call), and an empty basket (-> empty +
error). The provider must NEVER fabricate rows.

Fixtures reproduce the real /CFWeb/api JSON shapes verified live on 2026-06-15
(00919=fundNo 195 equity, 00937B=378 bond).
"""

from __future__ import annotations

import json

from app.providers.data.capital_holding_provider import CapitalHoldingProvider

_ITEMS = json.dumps(
    {
        "data": [
            {"fundNo": "195", "stockNo": "00919", "shortName": "群益台灣精選高息"},
            {"fundNo": "378", "stockNo": "00937B", "shortName": "群益ESG投等債"},
        ]
    }
).encode("utf-8")

_BUYBACK_EQUITY = json.dumps(
    {
        "data": {
            "pcf": {"nav": 550762418982.0, "pUnit": 30.61, "date1": "2026-06-16", "date2": "2026-06-15"},
            "stocks": [
                {"stocNo": "2881", "stocName": "富邦金", "weight": 13.4418, "share": 580650000},
                {"stocNo": "2882", "stocName": "國泰金", "weight": 12.3016, "share": 651470000},
            ],
            "bonds": [],
            "futures": [
                {"txEname": "TX202606", "txDesc": "台指期202606", "weight": 0.404, "lot": 244},
            ],
            "assets": [{"asDesc": "現金", "asMoney": "TWD 14,835,187,267.00"}],
        }
    }
).encode("utf-8")

_BUYBACK_BOND = json.dumps(
    {
        "data": {
            "pcf": {"nav": 259449193408.0, "pUnit": 15.0181, "date1": "2026-06-16"},
            "stocks": [],
            "bonds": [
                {"bondNo": "XS2638076187", "bondName": "ISPIM 7.778 06/20/54", "weight": 2.6356, "faceValue": 177900000},
            ],
            "futures": [],
        }
    }
).encode("utf-8")


def _http_post_factory(buyback: bytes = _BUYBACK_EQUITY, *, items: bytes = _ITEMS):
    calls: list[tuple[str, dict]] = []

    def fake_http_post(url: str, body: dict) -> bytes:
        calls.append((url, body))
        if url.endswith("/items"):
            return items
        if url.endswith("/buyback"):
            return buyback
        raise AssertionError(f"unexpected url {url}")

    return fake_http_post, calls


def test_happy_path_parses_stocks_and_futures():
    fake, calls = _http_post_factory()
    provider = CapitalHoldingProvider(http_post=fake)
    result = provider.fetch(symbol="00919")

    assert result.source_name == "群益投信"
    assert result.reliability_level == "high"
    assert result.errors == []
    # 2 stocks + 1 future = 3 rows.
    assert len(result.records) == 3
    assert [r["asset_symbol"] for r in result.records] == ["2881", "2882", "TX202606"]

    stock = result.records[0]
    assert stock["asset_name"] == "富邦金"
    assert stock["weight"] == 13.4418
    assert stock["shares"] == 580650000.0
    assert stock["confidence_level"] == "HIGH"
    assert stock["holding_date"].isoformat() == "2026-06-16"

    fut = result.records[2]
    assert fut["asset_name"] == "台指期202606"
    assert fut["shares"] == 244.0

    assert result.fund_meta["aum"] == 550762418982.0
    assert result.fund_meta["nav"] == 30.61
    assert result.fund_meta["nav_date"].isoformat() == "2026-06-16"
    # buyback called with the resolved integer fundId.
    assert ("https://www.capitalfund.com.tw/CFWeb/api/etf/buyback", {"fundId": 195}) in calls


def test_bond_schema_parsed():
    fake, _ = _http_post_factory(buyback=_BUYBACK_BOND)
    provider = CapitalHoldingProvider(http_post=fake)
    result = provider.fetch(symbol="00937B")

    assert len(result.records) == 1
    rec = result.records[0]
    assert rec["asset_symbol"] == "XS2638076187"
    assert rec["asset_name"] == "ISPIM 7.778 06/20/54"
    assert rec["weight"] == 2.6356
    assert rec["shares"] == 177900000.0  # faceValue


def test_non_capital_symbol_returns_empty_without_buyback():
    fake, calls = _http_post_factory()
    provider = CapitalHoldingProvider(http_post=fake)
    result = provider.fetch(symbol="0050")

    assert result.records == []
    assert result.errors
    assert not any(url.endswith("/buyback") for url, _ in calls)


def test_empty_basket_returns_empty_with_error():
    empty_basket = json.dumps({"data": {"pcf": {}, "stocks": [], "bonds": [], "futures": []}}).encode("utf-8")
    fake, _ = _http_post_factory(buyback=empty_basket)
    provider = CapitalHoldingProvider(http_post=fake)
    result = provider.fetch(symbol="00919")

    assert result.records == []
    assert result.errors
