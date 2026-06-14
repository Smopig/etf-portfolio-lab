"""Tests for YahooHoldingProvider (offline, no network, CLAUDE.md §7).

Covers: happy path (10 rows parsed with correct ticker/name/weight and the
holding_date parsed from the data), non-200 HTTP error, a page with no
top10Holdings blob, and malformed input. No token is required for this
provider, and it must NEVER fabricate rows -- failures yield empty records
plus a descriptive error.

The happy-path fixture is a trimmed, real-shaped Yahoo HTML snippet: the
``top10Holdings`` blob exactly as Yahoo emits it, with slashes
unicode-escaped as ``\\u002F`` (verified live against
``tw.stock.yahoo.com/quote/0050.TW/holding`` on 2026-06-14).
"""

from __future__ import annotations

from app.providers.data.yahoo_holding_provider import YahooHoldingProvider

# Real verified 0050 top-10 holdings, with Yahoo's /-escaped slashes.
_HOLDINGS = [
    ("2330.TW", "台積電", "58.28"),
    ("2454.TW", "聯發科", "6.42"),
    ("2308.TW", "台達電", "4.81"),
    ("2317.TW", "鴻海", "3.57"),
    ("3711.TW", "日月光投控", "2.04"),
    ("2303.TW", "聯電", "1.70"),
    ("2383.TW", "台光電", "1.49"),
    ("3037.TW", "欣興", "1.43"),
    ("2345.TW", "智邦", "1.22"),
    ("2327.TW", "國巨*", "1.16"),
]


def _build_yahoo_html() -> bytes:
    detail = ",".join(
        '{"date":"2026\\u002F05\\u002F01","ticker":"%s","name":"%s","weighting":"%s"}'
        % (ticker, name, weight)
        for ticker, name, weight in _HOLDINGS
    )
    blob = (
        '"top10Holdings":{"date":"2026\\u002F05\\u002F01","holdingDetail":['
        + detail
        + "]}"
    )
    # Wrap in a bit of surrounding markup to look like the real page.
    html = (
        "<!DOCTYPE html><html><head></head><body>"
        '<script>window.__data={' + blob + "}</script>"
        "</body></html>"
    )
    return html.encode("utf-8")


def _fake_http_get_factory(payload: bytes, *, raise_exc: Exception | None = None):
    captured: dict[str, str] = {}

    def fake_http_get(url: str) -> bytes:
        captured["url"] = url
        if raise_exc is not None:
            raise raise_exc
        return payload

    return fake_http_get, captured


def test_happy_path_parses_ten_rows():
    fake, captured = _fake_http_get_factory(_build_yahoo_html())
    provider = YahooHoldingProvider(http_get=fake)
    result = provider.fetch(symbol="0050")

    assert result.dataset_type == "etf_holdings"
    assert result.source_name == "Yahoo奇摩股市"
    assert result.reliability_level == "medium"
    assert result.errors == []
    assert len(result.records) == 10

    rec = result.records[0]
    assert rec["etf_symbol"] == "0050"
    assert rec["asset_symbol"] == "2330"  # .TW suffix stripped
    assert rec["asset_name"] == "台積電"
    assert rec["weight"] == 58.28
    assert rec["source_name"] == "Yahoo奇摩股市"
    assert rec["confidence_level"] == "MEDIUM"
    assert rec["source_url"].endswith("/0050.TW/holding")

    # holding_date parsed from the data (2026/05/01), not today.
    assert rec["holding_date"].isoformat() == "2026-05-01"
    assert result.data_date.isoformat() == "2026-05-01"

    # Last row sanity.
    assert result.records[-1]["asset_symbol"] == "2327"
    assert result.records[-1]["weight"] == 1.16

    # URL requested is the .TW holding page.
    assert captured["url"].endswith("/0050.TW/holding")


def test_non_200_returns_empty_with_error():
    err = OSError("HTTP Error 503")
    err.code = 503  # type: ignore[attr-defined]
    fake, _ = _fake_http_get_factory(b"", raise_exc=err)
    provider = YahooHoldingProvider(http_get=fake)
    result = provider.fetch(symbol="0050")

    assert result.records == []
    assert result.errors
    assert "503" in result.errors[0]


def test_no_holdings_blob_returns_empty_with_error():
    html = b"<!DOCTYPE html><html><body>no holdings here</body></html>"
    fake, _ = _fake_http_get_factory(html)
    provider = YahooHoldingProvider(http_get=fake)
    result = provider.fetch(symbol="0050")

    assert result.records == []
    assert any("top10Holdings" in e for e in result.errors)


def test_blob_present_but_no_rows_returns_empty_with_error():
    html = b'<html><body><script>{"top10Holdings":{"holdingDetail":[]}}</script></body></html>'
    fake, _ = _fake_http_get_factory(html)
    provider = YahooHoldingProvider(http_get=fake)
    result = provider.fetch(symbol="0050")

    assert result.records == []
    assert result.errors


def test_http_exception_returns_empty_with_error():
    fake, _ = _fake_http_get_factory(b"", raise_exc=RuntimeError("connection refused"))
    provider = YahooHoldingProvider(http_get=fake)
    result = provider.fetch(symbol="0050")

    assert result.records == []
    assert result.errors
    assert "connection refused" in result.errors[0]


def test_empty_response_returns_empty_with_error():
    fake, _ = _fake_http_get_factory(b"")
    provider = YahooHoldingProvider(http_get=fake)
    result = provider.fetch(symbol="0050")

    assert result.records == []
    assert result.errors


def test_bond_etf_foreign_tickers_preserved():
    # Bond ETFs carry non-Taiwan tickers (no .TW suffix) -- keep them verbatim.
    detail = (
        '{"date":"2026\\u002F05\\u002F01","ticker":"US912810UA42",'
        '"name":"US TREASURY N\\u002FB 4.625% 05\\u002F15\\u002F2054","weighting":"5.00"}'
    )
    html = (
        '<html><body><script>{"top10Holdings":{"holdingDetail":['
        + detail
        + "]}}</script></body></html>"
    ).encode("utf-8")
    fake, _ = _fake_http_get_factory(html)
    provider = YahooHoldingProvider(http_get=fake)
    result = provider.fetch(symbol="00679B")

    assert len(result.records) == 1
    rec = result.records[0]
    assert rec["asset_symbol"] == "US912810UA42"
    assert rec["weight"] == 5.0
    assert "US TREASURY" in rec["asset_name"]
