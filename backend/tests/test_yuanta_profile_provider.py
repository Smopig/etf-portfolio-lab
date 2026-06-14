"""Tests for YuantaProfileProvider (offline, no network, CLAUDE.md §7).

Covers: happy path (tracking_index / index_provider / listing_date / fee %
parsed for 0050), no-fabrication for an empty MANAGEMENT_FEE_TEXT (0056 →
management_fee is None), non-200 HTTP error, malformed JSON, and missing Data.

The fixture is a trimmed, real-shaped Yuanta ETFBackstage payload (verified
live against ``etfapi.yuantaetfs.com`` on 2026-06-14), trimmed to 2 funds.
"""

from __future__ import annotations

import json

from app.providers.data.yuanta_profile_provider import YuantaProfileProvider

# Sanitized real sample (2 of 54 funds), verified live 2026-06-14.
_SAMPLE = {
    "ResultCode": 0,
    "Data": [
        {
            "STK_CD": "0050",
            "INDEX_FUND_NAME": "臺灣50指數",
            "INDEX_PREPARE_COMPANY": "臺灣證券交易所與FTSE合作編製",
            "MANAGEMENT_FEE_TEXT": "約0.0716%  (資料日期：2026/06/12) ",
            "LIST_DATE": "20030630",
            "SETUP_DATE": "20030625",
        },
        {
            "STK_CD": "0056",
            "INDEX_FUND_NAME": "臺灣高股息指數",
            "INDEX_PREPARE_COMPANY": "臺灣證交所與FTSE合作編製",
            "MANAGEMENT_FEE_TEXT": "",
            "LIST_DATE": "20071226",
            "SETUP_DATE": "20071213",
        },
    ],
}


def _fake_http_get_factory(payload: bytes, *, raise_exc: Exception | None = None):
    captured: dict[str, str] = {}

    def fake_http_get(url: str) -> bytes:
        captured["url"] = url
        if raise_exc is not None:
            raise raise_exc
        return payload

    return fake_http_get, captured


def test_happy_path_parses_profile_fields():
    fake, captured = _fake_http_get_factory(json.dumps(_SAMPLE).encode("utf-8"))
    provider = YuantaProfileProvider(http_get=fake)
    result = provider.fetch()

    assert result.dataset_type == "etf_profile"
    assert result.source_name == "元大投信"
    assert result.reliability_level == "high"
    assert result.errors == []
    assert len(result.records) == 2

    by_symbol = {r["symbol"]: r for r in result.records}
    rec = by_symbol["0050"]
    assert rec["tracking_index"] == "臺灣50指數"
    assert rec["index_provider"] == "臺灣證券交易所與FTSE合作編製"
    assert rec["management_fee"] == 0.0716
    assert rec["listing_date"].isoformat() == "2003-06-30"
    assert rec["setup_date"].isoformat() == "2003-06-25"
    assert rec["confidence_level"] == "HIGH"
    assert rec["source_name"] == "元大投信"

    # ETFBackstage endpoint hit with the GetETFInformation FuncId.
    assert "ETFBackstage" in captured["url"]
    assert "GetETFInformation" in captured["url"]


def test_empty_fee_text_yields_null_fee_no_fabrication():
    fake, _ = _fake_http_get_factory(json.dumps(_SAMPLE).encode("utf-8"))
    result = YuantaProfileProvider(http_get=fake).fetch()
    rec = {r["symbol"]: r for r in result.records}["0056"]
    # Empty MANAGEMENT_FEE_TEXT -> NEVER fabricated; fee is None.
    assert rec["management_fee"] is None
    # But other real fields still parse.
    assert rec["tracking_index"] == "臺灣高股息指數"
    assert rec["listing_date"].isoformat() == "2007-12-26"


def test_non_200_returns_empty_with_error():
    err = OSError("HTTP Error 500")
    err.code = 500  # type: ignore[attr-defined]
    fake, _ = _fake_http_get_factory(b"", raise_exc=err)
    result = YuantaProfileProvider(http_get=fake).fetch()
    assert result.records == []
    assert result.errors
    assert "500" in result.errors[0]


def test_malformed_json_returns_empty_with_error():
    fake, _ = _fake_http_get_factory(b"<html>not json</html>")
    result = YuantaProfileProvider(http_get=fake).fetch()
    assert result.records == []
    assert result.errors


def test_missing_data_array_returns_empty_with_error():
    fake, _ = _fake_http_get_factory(json.dumps({"ResultCode": 0}).encode("utf-8"))
    result = YuantaProfileProvider(http_get=fake).fetch()
    assert result.records == []
    assert any("Data" in e for e in result.errors)
