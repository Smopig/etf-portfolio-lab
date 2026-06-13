"""Tests for portfolio_service using an in-memory SQLite DB."""

from __future__ import annotations

import datetime as dt

import pytest
from sqlalchemy import MetaData, create_engine
from sqlalchemy.orm import sessionmaker

from app.models import EtfHolding, EtfMaster, Portfolio, PortfolioItem, StockIndustry
from app.services import portfolio_service as svc

TABLES = [
    EtfHolding.__table__,
    StockIndustry.__table__,
    EtfMaster.__table__,
    Portfolio.__table__,
    PortfolioItem.__table__,
]


@pytest.fixture()
def sqlite_session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/test.db")
    metadata = MetaData()
    for table in TABLES:
        new_table = table.to_metadata(metadata)
        for column in new_table.columns:
            if column.server_default is not None:
                column.server_default = None
    metadata.create_all(engine)

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal


HOLDING_DATE = dt.date(2026, 6, 1)


def _seed_fixture(session):
    """ETF_A 60%: 2330 @ 50%, 2317 @ 50%. ETF_B 40%: 2330 @ 100%."""
    for symbol, pct in [("2330", 50.0), ("2317", 50.0)]:
        session.add(
            EtfHolding(
                etf_symbol="ETF_A",
                holding_date=HOLDING_DATE,
                asset_symbol=symbol,
                asset_name=f"Stock {symbol}",
                weight=pct,
                source_name="TEST",
            )
        )
    session.add(
        EtfHolding(
            etf_symbol="ETF_B",
            holding_date=HOLDING_DATE,
            asset_symbol="2330",
            asset_name="Stock 2330",
            weight=100.0,
            source_name="TEST",
        )
    )

    session.add(
        StockIndustry(stock_symbol="2330", industry_level_1="Tech", industry_level_2="Semis")
    )
    # 2317 has no industry mapping -> Unclassified

    session.add(EtfMaster(symbol="ETF_A", name="ETF A"))
    session.add(EtfMaster(symbol="ETF_B", name="ETF B"))
    session.commit()


FIXTURE_ITEMS = [
    {"etf_symbol": "ETF_A", "target_weight": 60.0},
    {"etf_symbol": "ETF_B", "target_weight": 40.0},
]


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

def test_crud_round_trip(sqlite_session):
    session = sqlite_session()
    try:
        _seed_fixture(session)

        created = svc.create_portfolio(
            session, "Test Portfolio", FIXTURE_ITEMS, description="desc"
        )
        assert created["id"] is not None
        assert created["name"] == "Test Portfolio"
        assert len(created["items"]) == 2

        fetched = svc.get_portfolio(session, created["id"])
        assert fetched["name"] == "Test Portfolio"
        assert {i["etf_symbol"] for i in fetched["items"]} == {"ETF_A", "ETF_B"}

        all_portfolios = svc.list_portfolios(session)
        assert len(all_portfolios) == 1

        updated = svc.update_portfolio(
            session,
            created["id"],
            name="Renamed",
            items=[{"etf_symbol": "ETF_A", "target_weight": 100.0}],
        )
        assert updated["name"] == "Renamed"
        assert len(updated["items"]) == 1
        assert updated["items"][0]["etf_symbol"] == "ETF_A"

        assert svc.delete_portfolio(session, created["id"]) is True
        assert svc.get_portfolio(session, created["id"]) is None
        assert svc.delete_portfolio(session, created["id"]) is False
    finally:
        session.close()


# ---------------------------------------------------------------------------
# validate_weights
# ---------------------------------------------------------------------------

def test_validate_weights_pass(sqlite_session):
    session = sqlite_session()
    try:
        _seed_fixture(session)
        items = [
            {"etf_symbol": "ETF_A", "target_weight": 40.0},
            {"etf_symbol": "ETF_B", "target_weight": 30.0},
            {"etf_symbol": "0050", "target_weight": 0.0},  # placeholder unused
        ]
        # Use a clean 40/30/30 with known symbols
        items = [
            {"etf_symbol": "ETF_A", "target_weight": 40.0},
            {"etf_symbol": "ETF_B", "target_weight": 30.0},
        ]
        result = svc.validate_weights(session, items)
        # 40+30 = 70, not 100 -> should not be PASS
        assert result["status"] != "PASS"

        items_pass = [
            {"etf_symbol": "ETF_A", "target_weight": 40.0},
            {"etf_symbol": "ETF_B", "target_weight": 30.0},
            {"etf_symbol": "ETF_A", "target_weight": 30.0},
        ]
        # This has duplicate ETF_A but sums to 100
        result2 = svc.validate_weights(session, items_pass)
        assert result2["status"] == "WARN"
        assert "ETF_A" in result2["duplicate_symbols"]
    finally:
        session.close()


def test_validate_weights_warn_fail(sqlite_session):
    session = sqlite_session()
    try:
        _seed_fixture(session)

        # 40/30/30 -> PASS
        items_100 = [
            {"etf_symbol": "ETF_A", "target_weight": 40.0},
            {"etf_symbol": "ETF_B", "target_weight": 30.0},
            {"etf_symbol": "0050", "target_weight": 30.0},
        ]
        session.add(EtfMaster(symbol="0050", name="0050"))
        session.commit()
        result_100 = svc.validate_weights(session, items_100)
        assert result_100["status"] == "PASS"
        assert result_100["weight_sum_pct"] == pytest.approx(100.0)

        # 40/30/20 = 90 -> WARN or FAIL
        items_90 = [
            {"etf_symbol": "ETF_A", "target_weight": 40.0},
            {"etf_symbol": "ETF_B", "target_weight": 30.0},
            {"etf_symbol": "0050", "target_weight": 20.0},
        ]
        result_90 = svc.validate_weights(session, items_90)
        assert result_90["status"] in ("WARN", "FAIL")
        assert result_90["weight_sum_pct"] == pytest.approx(90.0)

        # unknown etf
        items_unknown = [
            {"etf_symbol": "ETF_A", "target_weight": 50.0},
            {"etf_symbol": "UNKNOWN_ETF", "target_weight": 50.0},
        ]
        result_unknown = svc.validate_weights(session, items_unknown)
        assert "UNKNOWN_ETF" in result_unknown["unknown_symbols"]
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Look-through stock exposure
# ---------------------------------------------------------------------------

def test_look_through_stock_exposure(sqlite_session):
    session = sqlite_session()
    try:
        _seed_fixture(session)

        result = svc.get_look_through_stock_exposure(session, FIXTURE_ITEMS)
        stocks = {s["asset_symbol"]: s["weight_fraction"] for s in result["stocks"]}

        assert stocks["2330"] == pytest.approx(0.6 * 0.5 + 0.4 * 1.0)  # 0.7
        assert stocks["2317"] == pytest.approx(0.3)

        total = sum(stocks.values())
        assert total == pytest.approx(1.0)

        # Top stock should be 2330
        assert result["stocks"][0]["asset_symbol"] == "2330"
        assert result["num_stocks"] == 2
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Look-through industry exposure
# ---------------------------------------------------------------------------

def test_look_through_industry_exposure(sqlite_session):
    session = sqlite_session()
    try:
        _seed_fixture(session)

        result = svc.get_look_through_industry_exposure(session, FIXTURE_ITEMS)
        industries = {i["industry"]: i["weight_fraction"] for i in result["industries"]}

        # 2330 (0.7) is Tech, 2317 (0.3) is Unclassified
        assert industries["Tech"] == pytest.approx(0.7)
        assert result["unclassified"]["weight_fraction"] == pytest.approx(0.3)

        assert result["max_industry"]["industry"] == "Tech"
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Concentration
# ---------------------------------------------------------------------------

def test_portfolio_concentration(sqlite_session):
    session = sqlite_session()
    try:
        _seed_fixture(session)

        result = svc.get_portfolio_concentration(session, FIXTURE_ITEMS)

        # HHI = 0.7^2 + 0.3^2 = 0.49 + 0.09 = 0.58
        assert result["hhi"] == pytest.approx(0.58)
        assert result["effective_holdings"] == pytest.approx(1 / 0.58)
        assert result["top1_pct"] == pytest.approx(70.0)
        assert result["top3_pct"] == pytest.approx(100.0)  # only 2 stocks total
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Overlap risk
# ---------------------------------------------------------------------------

def test_portfolio_overlap_risk(sqlite_session):
    session = sqlite_session()
    try:
        _seed_fixture(session)

        result = svc.get_portfolio_overlap_risk(session, FIXTURE_ITEMS)
        assert set(result["symbols"]) == {"ETF_A", "ETF_B"}
        assert len(result["pairs"]) == 1
        # ETF_A and ETF_B share 2330: ETF_A weight 0.5, ETF_B weight 1.0 -> min = 0.5
        assert result["pairs"][0]["weighted_overlap_pct"] == pytest.approx(50.0)
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Warnings
# ---------------------------------------------------------------------------

def test_portfolio_warnings_single_stock_concentration(sqlite_session):
    session = sqlite_session()
    try:
        _seed_fixture(session)

        result = svc.get_portfolio_warnings(session, FIXTURE_ITEMS)

        codes = {w["code"] for w in result["warnings"]}
        # 2330 is 70% look-through -> over 30% threshold
        assert "SINGLE_STOCK_CONCENTRATION" in codes
        assert result["disclaimer"]
    finally:
        session.close()


def test_compare_portfolios(sqlite_session):
    session = sqlite_session()
    try:
        _seed_fixture(session)

        single_etf_items = [{"etf_symbol": "ETF_B", "target_weight": 100.0}]

        result = svc.compare_portfolios(session, [FIXTURE_ITEMS, single_etf_items])
        assert len(result["portfolios"]) == 2
        assert result["disclaimer"]
        for p in result["portfolios"]:
            assert "concentration" in p
            assert "top_industries" in p
            assert "top_stocks" in p
    finally:
        session.close()
