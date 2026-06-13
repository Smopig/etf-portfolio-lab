"""API-layer tests using FastAPI TestClient against an in-memory SQLite DB.

Only JSONB-free tables are created (backtest_runs/projection_runs are
skipped), so backtest/projection endpoints are exercised with
persist=false only.
"""

from __future__ import annotations

import datetime as dt

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import get_db
from app.main import app
from app.models import (
    DataQualityCheck,
    DataSourceRegistry,
    EtfDividend,
    EtfHolding,
    EtfMaster,
    EtfPrice,
    FetchLog,
    Portfolio,
    PortfolioItem,
    StockIndustry,
)

TABLES = [
    EtfMaster.__table__,
    EtfHolding.__table__,
    StockIndustry.__table__,
    EtfPrice.__table__,
    EtfDividend.__table__,
    Portfolio.__table__,
    PortfolioItem.__table__,
    DataSourceRegistry.__table__,
    DataQualityCheck.__table__,
    FetchLog.__table__,
]


@pytest.fixture()
def client(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/test_api.db")

    from sqlalchemy import MetaData

    metadata = MetaData()
    for table in TABLES:
        new_table = table.to_metadata(metadata)
        for column in new_table.columns:
            if column.server_default is not None:
                column.server_default = None
    metadata.create_all(engine)

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def _get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _get_db

    # Seed data
    session = SessionLocal()
    HOLDING_DATE = dt.date(2026, 6, 1)

    session.add_all(
        [
            EtfMaster(symbol="0050", name="Yuanta Taiwan 50", issuer="Yuanta", is_active=True),
            EtfMaster(symbol="006208", name="Fubon Taiwan 50", issuer="Fubon", is_active=True),
            EtfMaster(symbol="0099", name="Inactive ETF", issuer="Test", is_active=False),
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
                source_name="TEST",
            ),
            EtfHolding(
                etf_symbol="0050",
                holding_date=HOLDING_DATE,
                asset_symbol="2317",
                asset_name="Hon Hai",
                weight=50.0,
                source_name="TEST",
            ),
            EtfHolding(
                etf_symbol="006208",
                holding_date=HOLDING_DATE,
                asset_symbol="2330",
                asset_name="TSMC",
                weight=100.0,
                source_name="TEST",
            ),
        ]
    )

    session.add_all(
        [
            StockIndustry(stock_symbol="2330", industry_level_1="Tech", industry_level_2="Semis"),
            StockIndustry(stock_symbol="2317", industry_level_1="Tech", industry_level_2="Hardware"),
        ]
    )

    # Synthetic price series for backtest (two ETFs, simple linear growth)
    for i in range(10):
        d = dt.date(2026, 1, 1) + dt.timedelta(days=i)
        session.add(
            EtfPrice(
                etf_symbol="0050",
                trade_date=d,
                close=100.0 + i,
                adjusted_close=100.0 + i,
                source_name="TEST",
            )
        )
        session.add(
            EtfPrice(
                etf_symbol="006208",
                trade_date=d,
                close=50.0 + i * 0.5,
                adjusted_close=50.0 + i * 0.5,
                source_name="TEST",
            )
        )

    session.add(
        DataSourceRegistry(
            source_name="TWSE",
            source_type="official",
            base_url="https://www.twse.com.tw",
            enabled=True,
        )
    )
    session.add(
        DataQualityCheck(
            dataset_type="etf_holdings",
            dataset_key="0050",
            check_name="weight_sum",
            status="PASS",
            checked_at=dt.datetime(2026, 1, 1, 0, 0, 0),
        )
    )

    session.commit()
    session.close()

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# health
# ---------------------------------------------------------------------------


def test_health_still_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# etfs
# ---------------------------------------------------------------------------


def test_list_etfs(client):
    response = client.get("/api/etfs")
    assert response.status_code == 200
    body = response.json()
    assert "data" in body
    symbols = [e["symbol"] for e in body["data"]]
    assert "0050" in symbols
    assert "006208" in symbols


def test_list_etfs_active_filter(client):
    response = client.get("/api/etfs", params={"active": True})
    assert response.status_code == 200
    symbols = [e["symbol"] for e in response.json()["data"]]
    assert "0099" not in symbols


def test_get_etf_card(client):
    response = client.get("/api/etfs/0050")
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["symbol"] == "0050"


def test_get_etf_unknown(client):
    response = client.get("/api/etfs/NOPE")
    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "NOT_FOUND"


def test_get_holdings(client):
    response = client.get("/api/etfs/0050/holdings")
    assert response.status_code == 200
    body = response.json()
    assert "data" in body


def test_get_concentration(client):
    response = client.get("/api/etfs/0050/concentration")
    assert response.status_code == 200
    assert "data" in response.json()


def test_get_industry_exposure(client):
    response = client.get("/api/etfs/0050/industry-exposure", params={"level": 1})
    assert response.status_code == 200
    assert "data" in response.json()


def test_compare_etfs(client):
    response = client.get("/api/etfs/compare", params={"symbols": "0050,006208"})
    assert response.status_code == 200
    assert "data" in response.json()


def test_overlap_etfs(client):
    response = client.get("/api/etfs/overlap", params={"symbols": "0050,006208"})
    assert response.status_code == 200
    body = response.json()
    assert "overlap" in body["data"]
    assert "industry_similarity" in body["data"]


def test_overlap_etfs_wrong_count(client):
    response = client.get("/api/etfs/overlap", params={"symbols": "0050"})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


# ---------------------------------------------------------------------------
# industries / stocks reverse lookup
# ---------------------------------------------------------------------------


def test_industry_etf_ranking(client):
    response = client.get("/api/industries/Tech/etf-ranking", params={"level": 1})
    assert response.status_code == 200
    assert "data" in response.json()


def test_stock_etfs(client):
    response = client.get("/api/stocks/2330/etfs")
    assert response.status_code == 200
    assert "data" in response.json()


# ---------------------------------------------------------------------------
# portfolios
# ---------------------------------------------------------------------------


def test_portfolio_crud_roundtrip(client):
    # Create
    create_resp = client.post(
        "/api/portfolios",
        json={
            "name": "My Portfolio",
            "description": "test",
            "base_currency": "TWD",
            "items": [
                {"etf_symbol": "0050", "target_weight": 60.0},
                {"etf_symbol": "006208", "target_weight": 40.0},
            ],
        },
    )
    assert create_resp.status_code == 200
    portfolio = create_resp.json()["data"]
    pid = portfolio["id"]
    assert portfolio["name"] == "My Portfolio"

    # List
    list_resp = client.get("/api/portfolios")
    assert list_resp.status_code == 200
    assert any(p["id"] == pid for p in list_resp.json()["data"])

    # Get
    get_resp = client.get(f"/api/portfolios/{pid}")
    assert get_resp.status_code == 200
    assert get_resp.json()["data"]["id"] == pid

    # Update
    update_resp = client.put(f"/api/portfolios/{pid}", json={"name": "Renamed"})
    assert update_resp.status_code == 200
    assert update_resp.json()["data"]["name"] == "Renamed"

    # Exposure
    exposure_resp = client.get(f"/api/portfolios/{pid}/exposure")
    assert exposure_resp.status_code == 200
    body = exposure_resp.json()["data"]
    assert "stock_exposure" in body
    assert "industry_exposure" in body

    # Concentration
    conc_resp = client.get(f"/api/portfolios/{pid}/concentration")
    assert conc_resp.status_code == 200

    # Overlap risk
    overlap_resp = client.get(f"/api/portfolios/{pid}/overlap-risk")
    assert overlap_resp.status_code == 200

    # Warnings
    warn_resp = client.get(f"/api/portfolios/{pid}/warnings")
    assert warn_resp.status_code == 200
    assert "data" in warn_resp.json()

    # Delete
    delete_resp = client.delete(f"/api/portfolios/{pid}")
    assert delete_resp.status_code == 200
    assert delete_resp.json()["data"]["deleted"] is True

    # Now 404
    get_resp2 = client.get(f"/api/portfolios/{pid}")
    assert get_resp2.status_code == 404
    assert get_resp2.json()["error"]["code"] == "NOT_FOUND"


def test_portfolio_not_found(client):
    response = client.get("/api/portfolios/999999")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_portfolio_analyze_draft(client):
    response = client.post(
        "/api/portfolios/analyze",
        json={
            "items": [
                {"etf_symbol": "0050", "target_weight": 60.0},
                {"etf_symbol": "006208", "target_weight": 40.0},
            ]
        },
    )
    assert response.status_code == 200
    body = response.json()["data"]
    for key in ("validation", "stock_exposure", "industry_exposure", "concentration", "warnings"):
        assert key in body


# ---------------------------------------------------------------------------
# backtests
# ---------------------------------------------------------------------------


def test_backtest_persist_false(client):
    response = client.post(
        "/api/backtests",
        params={"persist": False},
        json={
            "symbols": ["0050", "006208"],
            "weights": [0.6, 0.4],
            "start_date": "2026-01-01",
            "end_date": "2026-01-10",
            "initial_amount": 100000,
            "monthly_contribution": 0,
            "dividend_reinvest": True,
            "rebalance_frequency": "none",
        },
    )
    assert response.status_code == 200
    body = response.json()["data"]
    assert "final_value" in body or "metrics" in body


# ---------------------------------------------------------------------------
# projections
# ---------------------------------------------------------------------------


def test_projection(client):
    response = client.post(
        "/api/projections",
        json={
            "initial_amount": 100000,
            "monthly_contribution": 5000,
            "annual_return_rate": 0.06,
            "years": 10,
            "persist": False,
        },
    )
    assert response.status_code == 200
    assert "data" in response.json()


def test_projection_scenarios(client):
    response = client.post(
        "/api/projections/scenarios",
        json={
            "initial_amount": 100000,
            "monthly_contribution": 5000,
            "years": 10,
        },
    )
    assert response.status_code == 200
    assert "data" in response.json()


def test_projection_goal_seek(client):
    response = client.post(
        "/api/projections/goal-seek",
        json={
            "solve_for": "years",
            "initial_amount": 100000,
            "monthly_contribution": 5000,
            "annual_return_rate": 0.06,
            "target_amount": 1000000,
        },
    )
    assert response.status_code == 200
    assert "data" in response.json()


# ---------------------------------------------------------------------------
# data sources / data quality / imports
# ---------------------------------------------------------------------------


def test_data_sources(client):
    response = client.get("/api/data-sources")
    assert response.status_code == 200
    assert "data" in response.json()


def test_data_quality(client):
    response = client.get("/api/data-quality")
    assert response.status_code == 200
    assert "data" in response.json()


def test_fetch_logs(client):
    response = client.get("/api/data-sources/fetch-logs")
    assert response.status_code == 200
    assert "data" in response.json()


def test_imports_status(client):
    response = client.get("/api/imports/status")
    assert response.status_code == 200
    assert "data" in response.json()


# ---------------------------------------------------------------------------
# ai placeholders
# ---------------------------------------------------------------------------


def test_ai_analyze_etf(client):
    response = client.post("/api/ai/analyze-etf", json={"symbol": "0050"})
    assert response.status_code == 200
    assert response.json()["data"]["provider"] == "mock"


def test_ai_analyze_portfolio(client):
    response = client.post(
        "/api/ai/analyze-portfolio",
        json={"items": [{"etf_symbol": "0050", "target_weight": 100.0}]},
    )
    assert response.status_code == 200
    assert response.json()["data"]["provider"] == "mock"


def test_ai_analyze_portfolio_missing_target(client):
    response = client.post("/api/ai/analyze-portfolio", json={})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_ai_analyze_etf_unknown_symbol_insufficient_data(client):
    response = client.post("/api/ai/analyze-etf", json={"symbol": "NOPE"})
    assert response.status_code == 200
    body = response.json()["data"]
    assert "資料不足" in body["analysis_text"]
    assert body["provider"] is None


# ---------------------------------------------------------------------------
# error envelope consistency
# ---------------------------------------------------------------------------


def test_error_envelope_shape_404(client):
    response = client.get("/api/etfs/UNKNOWN")
    body = response.json()
    assert set(body.keys()) == {"error"}
    assert set(body["error"].keys()) == {"code", "message"}


def test_error_envelope_shape_validation(client):
    response = client.get("/api/etfs/overlap", params={"symbols": "0050,006208,0099"})
    body = response.json()
    assert set(body.keys()) == {"error"}
    assert body["error"]["code"] == "VALIDATION_ERROR"


# ---------------------------------------------------------------------------
# dashboard / availability / ranking (Phase 9.5)
# ---------------------------------------------------------------------------


def test_dashboard_summary(client):
    response = client.get("/api/dashboard/summary")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total_etfs"] == 3
    assert data["active_etfs"] == 2
    # 0050 and 006208 have holdings; 0099 does not
    assert data["etfs_with_holdings"] == 2
    # 0050 and 006208 have prices; 0099 does not
    assert data["etfs_with_prices"] == 2
    assert data["recent_quality_warnings"] == 0
    assert data["last_updated"] is not None


def test_list_etfs_has_availability_flags(client):
    response = client.get("/api/etfs")
    assert response.status_code == 200
    by_symbol = {e["symbol"]: e for e in response.json()["data"]}
    assert by_symbol["0050"]["has_holdings"] is True
    assert by_symbol["0050"]["has_price_data"] is True
    assert by_symbol["0099"]["has_holdings"] is False
    assert by_symbol["0099"]["has_price_data"] is False


def test_etfs_ranking_hhi_desc(client):
    response = client.get("/api/etfs/ranking", params={"metric": "hhi"})
    assert response.status_code == 200
    body = response.json()
    data = body["data"]
    assert len(data) >= 2
    symbols = [r["etf_symbol"] for r in data]
    # 006208 (100% TSMC) is more concentrated than 0050 (50/50)
    assert symbols.index("006208") < symbols.index("0050")
    values = [r["value"] for r in data]
    assert values == sorted(values, reverse=True)


def test_etfs_ranking_industry_exposure(client):
    response = client.get(
        "/api/etfs/ranking", params={"metric": "industry_exposure", "industry": "Tech", "level": 1}
    )
    assert response.status_code == 200
    data = response.json()["data"]
    for row in data:
        assert row["industry"] == "Tech"
    # both 0050 and 006208 are 100% Tech
    by_symbol = {r["etf_symbol"]: r for r in data}
    assert by_symbol["0050"]["value"] == pytest.approx(1.0)
    assert by_symbol["006208"]["value"] == pytest.approx(1.0)


def test_etfs_ranking_requires_industry_for_industry_exposure(client):
    response = client.get("/api/etfs/ranking", params={"metric": "industry_exposure"})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_etfs_ranking_invalid_metric(client):
    response = client.get("/api/etfs/ranking", params={"metric": "bogus"})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_etfs_ranking_route_not_shadowed_by_symbol(client):
    # /api/etfs/ranking must not be captured by /api/etfs/{symbol}
    response = client.get("/api/etfs/ranking", params={"metric": "hhi"})
    assert response.status_code == 200
    body = response.json()
    assert "error" not in body
    assert isinstance(body["data"], list)


def test_multi_overlap_pairs_include_rating_and_jaccard(client):
    response = client.get("/api/etfs/compare", params={"symbols": "0050,006208"})
    assert response.status_code == 200
    pairs = response.json()["data"]["pairs"]
    assert len(pairs) == 1
    pair = pairs[0]
    assert "overlap_rating" in pair
    assert set(pair["overlap_rating"].keys()) == {"label", "value"}
    assert "jaccard" in pair
    assert 0.0 <= pair["jaccard"] <= 1.0
