"""Tests for the Phase 13 AI analysis service and API (CLAUDE.md §7).

All tests use the deterministic Mock provider (default, no network, no API
key). A separate ClaudeAIProvider refusal test monkeypatches the anthropic
client and is skipped if the `anthropic` package is not installed.
"""

from __future__ import annotations

import datetime as dt

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import MetaData, create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import get_db
from app.main import app
from app.models import EtfHolding, EtfMaster, StockIndustry
from app.providers.ai.mock_provider import DISCLAIMER
from app.services import ai_analysis_service

TABLES = [EtfMaster.__table__, EtfHolding.__table__, StockIndustry.__table__]


@pytest.fixture()
def db_session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/test_ai.db")

    metadata = MetaData()
    for table in TABLES:
        new_table = table.to_metadata(metadata)
        for column in new_table.columns:
            if column.server_default is not None:
                column.server_default = None
    metadata.create_all(engine)

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()

    HOLDING_DATE = dt.date(2026, 6, 1)
    session.add_all(
        [
            EtfMaster(
                symbol="0050",
                name="Yuanta Taiwan 50",
                issuer="Yuanta",
                is_active=True,
                source_name="TWSE",
                data_date=HOLDING_DATE,
            ),
            EtfMaster(symbol="EMPTY", name="No Holdings ETF", issuer="Test", is_active=True),
        ]
    )
    session.add_all(
        [
            EtfHolding(
                etf_symbol="0050",
                holding_date=HOLDING_DATE,
                asset_symbol="2330",
                asset_name="TSMC",
                weight=50.0,
                source_name="TWSE",
            ),
            EtfHolding(
                etf_symbol="0050",
                holding_date=HOLDING_DATE,
                asset_symbol="2317",
                asset_name="Hon Hai",
                weight=50.0,
                source_name="TWSE",
            ),
        ]
    )
    session.add(StockIndustry(stock_symbol="2330", industry_level_1="Tech", industry_level_2="Semis"))
    session.add(StockIndustry(stock_symbol="2317", industry_level_1="Tech", industry_level_2="Hardware"))
    session.commit()

    yield session, SessionLocal

    session.close()


@pytest.fixture()
def client(db_session):
    _, SessionLocal = db_session

    def _get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Service-level tests
# ---------------------------------------------------------------------------


def test_analyze_etf_returns_grounded_mock_result(db_session):
    session, _ = db_session
    result = ai_analysis_service.analyze_etf(session, "0050")

    assert result["provider"] == "mock"
    assert result["refused"] is False
    assert "0050" in result["analysis_text"]
    assert "TWSE" in result["analysis_text"]  # data source citation
    assert "2026-06-01" in result["analysis_text"]  # data date citation
    assert DISCLAIMER in result["analysis_text"]
    assert "TWSE" in result["data_sources"]
    assert "2026-06-01" in result["data_dates"]


def test_analyze_etf_no_holdings_returns_insufficient_data(db_session, monkeypatch):
    session, _ = db_session

    called = {"flag": False}

    class _Boom:
        def generate(self, system, user):
            called["flag"] = True
            raise AssertionError("LLM should not be called when data is missing")

    monkeypatch.setattr(ai_analysis_service, "get_ai_provider", lambda: _Boom())

    result = ai_analysis_service.analyze_etf(session, "NOPE")

    assert called["flag"] is False
    assert "資料不足" in result["analysis_text"]
    assert result["provider"] is None


def test_analyze_portfolio_from_items(db_session):
    session, _ = db_session
    items = [{"etf_symbol": "0050", "target_weight": 100.0}]
    result = ai_analysis_service.analyze_portfolio(session, items)

    assert result["provider"] == "mock"
    assert DISCLAIMER in result["analysis_text"]
    assert "0050" in result["analysis_text"]


def test_explain_backtest_includes_caveat():
    result = ai_analysis_service.explain_backtest({"total_return_pct": 12.3, "cagr_pct": 5.0})

    assert result["provider"] == "mock"
    assert DISCLAIMER in result["analysis_text"]
    assert "回測" in ai_analysis_service.SYSTEM_PROMPT


def test_explain_projection_includes_caveat():
    result = ai_analysis_service.explain_projection({"final_value": 1000000})

    assert result["provider"] == "mock"
    assert DISCLAIMER in result["analysis_text"]


def test_explain_backtest_no_data_returns_insufficient():
    result = ai_analysis_service.explain_backtest({})
    assert "資料不足" in result["analysis_text"]


def test_build_etf_context_uses_real_fields(db_session):
    session, _ = db_session
    context = ai_analysis_service.build_etf_context(session, "0050")

    assert context["symbol"] == "0050"
    assert context["data_provenance"]["source_name"] == "TWSE"
    symbols = {h["asset_symbol"] for h in context["top_holdings"]}
    assert symbols == {"2330", "2317"}


def test_build_etf_context_missing_etf_returns_empty(db_session):
    session, _ = db_session
    assert ai_analysis_service.build_etf_context(session, "DOES_NOT_EXIST") == {}


# ---------------------------------------------------------------------------
# Claude provider refusal handling
# ---------------------------------------------------------------------------


def test_claude_provider_handles_refusal(monkeypatch):
    anthropic = pytest.importorskip("anthropic")

    from app.providers.ai.claude_provider import ClaudeAIProvider

    class _FakeResponse:
        stop_reason = "refusal"
        content = []

    class _FakeMessages:
        def create(self, **kwargs):
            return _FakeResponse()

    class _FakeClient:
        def __init__(self, api_key=None):
            self.messages = _FakeMessages()

    monkeypatch.setattr(anthropic, "Anthropic", _FakeClient)

    provider = ClaudeAIProvider(api_key="fake-key")
    result = provider.generate("system prompt", "user prompt")

    assert result.refused is True
    assert result.provider == "claude"


# ---------------------------------------------------------------------------
# API-level tests
# ---------------------------------------------------------------------------


def test_api_analyze_etf(client):
    response = client.post("/api/ai/analyze-etf", json={"symbol": "0050"})
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["provider"] == "mock"
    assert "0050" in body["data"]["analysis_text"]
    assert DISCLAIMER in body["data"]["analysis_text"]


def test_api_analyze_portfolio_with_items(client):
    response = client.post(
        "/api/ai/analyze-portfolio",
        json={"items": [{"etf_symbol": "0050", "target_weight": 100.0}]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["provider"] == "mock"


def test_api_explain_backtest(client):
    response = client.post(
        "/api/ai/explain-backtest", json={"result": {"total_return_pct": 10.0}}
    )
    assert response.status_code == 200
    assert response.json()["data"]["provider"] == "mock"


def test_api_explain_projection(client):
    response = client.post(
        "/api/ai/explain-projection", json={"result": {"final_value": 100}}
    )
    assert response.status_code == 200
    assert response.json()["data"]["provider"] == "mock"
