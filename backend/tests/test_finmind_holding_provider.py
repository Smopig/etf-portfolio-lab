"""Tests for FinMindHoldingProvider (offline, no network, CLAUDE.md §7).

Covers: happy path, missing token, 402 rate limit (with backoff),
malformed JSON. Asserts the API token never leaks into any output:
records, source_url, errors.
"""

from __future__ import annotations

import json

from app.providers.data.finmind_holding_provider import FinMindHoldingProvider

FAKE_TOKEN = "SECRET_FINMIND_TOKEN_DO_NOT_LEAK"


# Sanitized fixture modeling the documented FinMind shape:
# {"status": 200, "data": [{...}, ...]} with per-row stock_id / stock_name /
# weight / date fields (per FinMind dataset conventions for TaiwanETFHolding).
_HAPPY_PAYLOAD = {
    "status": 200,
    "data": [
        {
            "date": "2026-06-10",
            "stock_id": "2330",
            "stock_name": "台積電",
            "weight": 45.12,
        },
        {
            "date": "2026-06-10",
            "stock_id": "2317",
            "stock_name": "鴻海",
            "weight": 4.87,
        },
    ],
}


def _fake_http_get_factory(payload: dict | bytes):
    captured: dict[str, str] = {}

    def fake_http_get(url: str) -> bytes:
        captured["url"] = url
        if isinstance(payload, bytes):
            return payload
        return json.dumps(payload).encode("utf-8")

    return fake_http_get, captured


def test_happy_path_parses_records_and_redacts_token():
    fake, captured = _fake_http_get_factory(_HAPPY_PAYLOAD)
    provider = FinMindHoldingProvider(http_get=fake, token=FAKE_TOKEN)
    result = provider.fetch(symbol="0050")

    assert result.dataset_type == "etf_holdings"
    assert result.source_name == "FinMind"
    assert result.reliability_level == "medium"
    assert result.errors == []
    assert len(result.records) == 2

    rec = result.records[0]
    assert rec["etf_symbol"] == "0050"
    assert rec["asset_symbol"] == "2330"
    assert rec["asset_name"] == "台積電"
    assert rec["weight"] == 45.12
    assert rec["source_name"] == "FinMind"
    assert rec["confidence_level"] == "MEDIUM"
    assert rec["holding_date"].isoformat() == "2026-06-10"

    # Token MUST appear in the outbound request URL...
    assert FAKE_TOKEN in captured["url"]
    # ...but MUST NOT appear in source_url, records, or errors.
    assert FAKE_TOKEN not in (result.source_url or "")
    for r in result.records:
        for v in r.values():
            assert FAKE_TOKEN not in str(v)
    for err in result.errors:
        assert FAKE_TOKEN not in err


def test_missing_token_returns_empty_with_error(monkeypatch):
    monkeypatch.delenv("FINMIND_API_TOKEN", raising=False)
    fake, captured = _fake_http_get_factory(_HAPPY_PAYLOAD)
    provider = FinMindHoldingProvider(http_get=fake, token=None)
    result = provider.fetch(symbol="0050")

    assert result.records == []
    assert any("FINMIND_API_TOKEN" in e for e in result.errors)
    # Did not call HTTP at all.
    assert captured == {}
    # source_url never embeds a token (none to embed here, but verify shape).
    assert "token=" not in (result.source_url or "")


def test_rate_limit_402_retries_then_returns_rate_limited():
    calls = {"n": 0}

    def fake_http_get(url: str) -> bytes:
        calls["n"] += 1
        return json.dumps({"status": 402, "msg": "quota exceeded"}).encode("utf-8")

    sleeps: list[float] = []

    provider = FinMindHoldingProvider(
        http_get=fake_http_get,
        token=FAKE_TOKEN,
        sleeper=lambda s: sleeps.append(s),
    )
    result = provider.fetch(symbol="0050")

    assert result.records == []
    assert result.errors == ["rate_limited"]
    # Initial attempt + 2 retries == 3 calls; 2 sleeps (1s, 2s).
    assert calls["n"] == 3
    assert sleeps == [1.0, 2.0]
    # Token never in errors or url.
    assert FAKE_TOKEN not in result.errors[0]
    assert FAKE_TOKEN not in (result.source_url or "")


def test_malformed_json_returns_error_no_records():
    fake, _ = _fake_http_get_factory(b"<<not json>>")
    provider = FinMindHoldingProvider(http_get=fake, token=FAKE_TOKEN)
    result = provider.fetch(symbol="0050")

    assert result.records == []
    assert result.errors
    assert "parse JSON" in result.errors[0]
    assert FAKE_TOKEN not in result.errors[0]
    assert FAKE_TOKEN not in (result.source_url or "")


def test_http_exception_does_not_leak_token():
    def boom(url: str) -> bytes:
        # An error message that happens to embed the URL (which contains the
        # token) -- the provider must redact it.
        raise RuntimeError(f"connection refused while fetching {url}")

    provider = FinMindHoldingProvider(http_get=boom, token=FAKE_TOKEN)
    result = provider.fetch(symbol="0050")

    assert result.records == []
    assert result.errors
    for err in result.errors:
        assert FAKE_TOKEN not in err
    assert FAKE_TOKEN not in (result.source_url or "")


def test_empty_data_array_returns_error_no_records():
    fake, _ = _fake_http_get_factory({"status": 200, "data": []})
    provider = FinMindHoldingProvider(http_get=fake, token=FAKE_TOKEN)
    result = provider.fetch(symbol="0050")
    assert result.records == []
    assert result.errors
