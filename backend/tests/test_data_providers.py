"""Tests for app.providers.data.* (offline, no network)."""

from __future__ import annotations

import datetime as dt
import json

from app.providers.data.csv_file_provider import CsvFileProvider
from app.providers.data.factory import get_data_provider
from app.providers.data.twse_provider import TwseProvider
from app.providers.data.yahoo_price_provider import YahooPriceProvider


def test_csv_file_provider_reads_records(tmp_path):
    csv_path = tmp_path / "prices.csv"
    csv_path.write_text(
        "etf_symbol,trade_date,close,source_name\n"
        "ETF0050,2026-06-01,150.5,test-source\n"
        "ETF0050,2026-06-02,151.0,test-source\n"
    )

    provider = CsvFileProvider()
    result = provider.fetch(
        file_path=csv_path,
        dataset_type="etf_prices",
        source_url="file://local",
        data_date_column="trade_date",
        preserve_raw=False,
    )

    assert result.dataset_type == "etf_prices"
    assert result.source_name == "local-file"
    assert result.source_url == "file://local"
    assert result.reliability_level == "high"
    assert result.errors == []
    assert len(result.records) == 2
    assert result.records[0]["etf_symbol"] == "ETF0050"
    assert result.data_date == dt.date(2026, 6, 2)


def test_csv_file_provider_missing_file_returns_error(tmp_path):
    provider = CsvFileProvider()
    result = provider.fetch(
        file_path=tmp_path / "missing.csv",
        dataset_type="etf_prices",
        preserve_raw=False,
    )
    assert result.records == []
    assert result.errors
    assert "not found" in result.errors[0]


def test_yahoo_price_provider_success_with_fake_http():
    payload = {
        "chart": {
            "result": [
                {
                    "timestamp": [1748736000, 1748822400],
                    "indicators": {
                        "quote": [
                            {
                                "open": [100.0, 101.0],
                                "high": [102.0, 103.0],
                                "low": [99.0, 100.0],
                                "close": [101.0, 102.0],
                                "volume": [1000, 2000],
                            }
                        ],
                        "adjclose": [{"adjclose": [101.0, 102.0]}],
                    },
                }
            ],
            "error": None,
        }
    }

    def fake_http_get(url: str) -> bytes:
        return json.dumps(payload).encode("utf-8")

    provider = YahooPriceProvider(http_get=fake_http_get)
    result = provider.fetch(symbol="0050.TW")

    assert result.errors == []
    assert len(result.records) == 2
    assert result.records[0]["etf_symbol"] == "0050.TW"
    assert result.records[0]["close"] == 101.0
    assert result.source_name == "yahoo-finance"
    assert result.data_date is not None


def test_yahoo_price_provider_failure_returns_no_fabrication():
    def failing_http_get(url: str) -> bytes:
        raise ConnectionError("network down")

    provider = YahooPriceProvider(http_get=failing_http_get)
    result = provider.fetch(symbol="0050.TW")

    assert result.records == []
    assert result.errors
    assert "network down" in result.errors[0]


def test_yahoo_price_provider_empty_payload_returns_no_fabrication():
    def empty_http_get(url: str) -> bytes:
        return b""

    provider = YahooPriceProvider(http_get=empty_http_get)
    result = provider.fetch(symbol="0050.TW")

    assert result.records == []
    assert result.errors


def test_twse_provider_success_with_fake_http():
    payload = [
        {"Code": "2330", "Name": "台積電", "Weight": "12.5"},
        {"Code": "2317", "Name": "鴻海", "Weight": "5.0"},
    ]

    def fake_http_get(url: str) -> bytes:
        return json.dumps(payload).encode("utf-8")

    provider = TwseProvider(http_get=fake_http_get)
    result = provider.fetch(symbol="0050", holding_date=dt.date(2026, 6, 1))

    assert result.errors == []
    assert len(result.records) == 2
    assert result.records[0]["asset_symbol"] == "2330"
    assert result.records[0]["weight"] == 12.5
    assert result.data_date == dt.date(2026, 6, 1)


def test_twse_provider_failure_returns_no_fabrication():
    def failing_http_get(url: str) -> bytes:
        raise TimeoutError("timed out")

    provider = TwseProvider(http_get=failing_http_get)
    result = provider.fetch(symbol="0050")

    assert result.records == []
    assert result.errors


def test_factory_returns_correct_classes():
    assert isinstance(get_data_provider("local-file"), CsvFileProvider)
    assert isinstance(get_data_provider("yahoo-finance"), YahooPriceProvider)
    assert isinstance(get_data_provider("twse"), TwseProvider)


def test_factory_unknown_provider_raises():
    import pytest

    with pytest.raises(ValueError):
        get_data_provider("not-a-real-provider")
