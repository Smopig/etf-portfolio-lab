"""Tests for YuantaHoldingProvider (offline, no network, CLAUDE.md §7).

Covers: happy path (full StockWeights parsed with code/name/weight/shares and
holding_date from PCF.trandate, confidence HIGH), non-200 HTTP error, missing
FundWeights, malformed JSON, and a futures ETF whose StockWeights is empty but
FutureWeights is populated (graceful). The provider must NEVER fabricate rows --
failures yield empty records plus a descriptive error.

The fixtures are trimmed, real-shaped Yuanta PCF/Daily JSON (verified live
against ``etfapi.yuantaetfs.com`` on 2026-06-14, trandate 20260612), with
StockWeights trimmed to a few rows while keeping the structure intact.
"""

from __future__ import annotations

import json

from app.providers.data.yuanta_holding_provider import YuantaHoldingProvider


def _build_json(stock_rows, future_rows=None, trandate="20260612") -> bytes:
    payload = {
        "PCF": {
            "fundid": "1066",
            "markcd": "0050",
            "trandate": trandate,
            "nav": 102.14,
            "totalav": 2074315912926,
        },
        "InKind": {"FundComposition": []},
        "FundWeights": {
            "Summary": {"code": "1066", "fundsize": 100000},
            "StockWeights": stock_rows,
            "FutureWeights": future_rows or [],
            "ETFWeights": [],
            "BondWeights": [],
        },
        "Cash": None,
        "Memo": None,
    }
    return json.dumps(payload).encode("utf-8")


_STOCK_ROWS = [
    {"code": "2330", "ym": None, "name": "台積電", "ename": "TSMC", "weights": 57.95, "qty": 522327548.0},
    {"code": "2454", "ym": None, "name": "聯發科", "ename": "MediaTek", "weights": 6.30, "qty": 12345678.0},
    {"code": "2317", "ym": None, "name": "鴻海", "ename": "Hon Hai", "weights": 3.50, "qty": 98765432.0},
]


def _fake_http_get_factory(payload: bytes, *, raise_exc: Exception | None = None):
    captured: dict[str, str] = {}

    def fake_http_get(url: str) -> bytes:
        captured["url"] = url
        if raise_exc is not None:
            raise raise_exc
        return payload

    return fake_http_get, captured


def test_happy_path_parses_full_stock_weights():
    fake, captured = _fake_http_get_factory(_build_json(_STOCK_ROWS))
    provider = YuantaHoldingProvider(http_get=fake)
    result = provider.fetch(symbol="0050")

    assert result.dataset_type == "etf_holdings"
    assert result.source_name == "元大投信"
    assert result.reliability_level == "high"
    assert result.errors == []
    assert len(result.records) == 3

    rec = result.records[0]
    assert rec["etf_symbol"] == "0050"
    assert rec["asset_symbol"] == "2330"
    assert rec["asset_name"] == "台積電"
    assert rec["weight"] == 57.95
    assert rec["shares"] == 522327548.0
    assert rec["confidence_level"] == "HIGH"
    assert rec["source_name"] == "元大投信"

    # holding_date parsed from PCF.trandate (20260612), not today.
    assert rec["holding_date"].isoformat() == "2026-06-12"
    assert result.data_date.isoformat() == "2026-06-12"

    # fund_meta captures AUM (totalav) + NAV from the PCF block (no extra call).
    assert result.fund_meta is not None
    assert result.fund_meta["aum"] == 2074315912926.0
    assert result.fund_meta["nav"] == 102.14
    assert result.fund_meta["nav_date"].isoformat() == "2026-06-12"
    assert result.fund_meta["confidence_level"] == "HIGH"

    # URL is the PCF bridge with %2F-encoded slashes and the ticker present.
    assert "FuncId=PCF%2FDaily" in captured["url"]
    assert "ticker=0050" in captured["url"]
    assert "PageName=%2FtradeInfo%2Fpcf%2F0050" in captured["url"]


def test_non_200_returns_empty_with_error():
    err = OSError("HTTP Error 500")
    err.code = 500  # type: ignore[attr-defined]
    fake, _ = _fake_http_get_factory(b"", raise_exc=err)
    provider = YuantaHoldingProvider(http_get=fake)
    result = provider.fetch(symbol="0050")

    assert result.records == []
    assert result.errors
    assert "500" in result.errors[0]


def test_missing_fund_weights_returns_empty_with_error():
    payload = json.dumps({"PCF": {"trandate": "20260612"}}).encode("utf-8")
    fake, _ = _fake_http_get_factory(payload)
    provider = YuantaHoldingProvider(http_get=fake)
    result = provider.fetch(symbol="0050")

    assert result.records == []
    assert any("FundWeights" in e for e in result.errors)


def test_malformed_json_returns_empty_with_error():
    fake, _ = _fake_http_get_factory(b"<html>not json</html>")
    provider = YuantaHoldingProvider(http_get=fake)
    result = provider.fetch(symbol="0050")

    assert result.records == []
    assert result.errors
    assert "JSON" in result.errors[0]


def test_empty_response_returns_empty_with_error():
    fake, _ = _fake_http_get_factory(b"")
    provider = YuantaHoldingProvider(http_get=fake)
    result = provider.fetch(symbol="0050")

    assert result.records == []
    assert result.errors


def test_futures_etf_empty_stockweights_uses_future_weights():
    future_rows = [
        {"code": "TX", "ym": "202606", "name": "臺股期貨", "ename": "TAIEX FUTURE", "weights": 126.47, "qty": 29000.0},
    ]
    fake, _ = _fake_http_get_factory(_build_json([], future_rows=future_rows))
    provider = YuantaHoldingProvider(http_get=fake)
    result = provider.fetch(symbol="00631L")

    # StockWeights empty but FutureWeights present -> still parsed, no fabrication.
    assert len(result.records) == 1
    rec = result.records[0]
    assert rec["asset_symbol"] == "TX"
    assert rec["asset_name"] == "臺股期貨"
    assert rec["weight"] == 126.47
    assert rec["shares"] == 29000.0
    assert rec["confidence_level"] == "HIGH"


def test_all_weights_empty_returns_empty_with_error():
    fake, _ = _fake_http_get_factory(_build_json([]))
    provider = YuantaHoldingProvider(http_get=fake)
    result = provider.fetch(symbol="0050")

    assert result.records == []
    assert result.errors
