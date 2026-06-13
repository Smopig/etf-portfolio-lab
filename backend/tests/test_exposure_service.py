"""Tests for exposure_service using an in-memory SQLite DB."""

from __future__ import annotations

import datetime as dt

import pytest
from sqlalchemy import MetaData, create_engine
from sqlalchemy.orm import sessionmaker

from app.models import EtfHolding, StockIndustry
from app.services.exposure_service import UNCLASSIFIED, get_industry_exposure

TABLES = [
    EtfHolding.__table__,
    StockIndustry.__table__,
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


def test_industry_exposure(sqlite_session):
    session = sqlite_session()
    try:
        # Holdings: S1 40% (Tech), S2 30% (Tech), S3 20% (Finance), S4 10% (no mapping)
        for symbol, pct in [("S1", 40.0), ("S2", 30.0), ("S3", 20.0), ("S4", 10.0)]:
            session.add(
                EtfHolding(
                    etf_symbol="0050",
                    holding_date=HOLDING_DATE,
                    asset_symbol=symbol,
                    asset_name=f"Stock {symbol}",
                    weight=pct,
                    source_name="TEST",
                )
            )

        session.add(
            StockIndustry(stock_symbol="S1", industry_level_1="Tech", industry_level_2="Semis")
        )
        session.add(
            StockIndustry(stock_symbol="S2", industry_level_1="Tech", industry_level_2="Hardware")
        )
        session.add(
            StockIndustry(stock_symbol="S3", industry_level_1="Finance", industry_level_2="Banks")
        )
        # S4 has no StockIndustry row -> unclassified
        session.commit()

        result = get_industry_exposure(session, "0050", level=1)

        industries = {i["industry"]: i for i in result["industries"]}
        assert industries["Tech"]["weight_fraction"] == pytest.approx(0.70)
        assert industries["Finance"]["weight_fraction"] == pytest.approx(0.20)

        assert result["max_industry"]["industry"] == "Tech"
        assert [i["industry"] for i in result["top3_industries"]] == ["Tech", "Finance"]

        assert result["unclassified"]["industry"] == UNCLASSIFIED
        assert result["unclassified"]["weight_fraction"] == pytest.approx(0.10)

        total = sum(i["weight_fraction"] for i in result["industries"]) + result[
            "unclassified"
        ]["weight_fraction"]
        assert total == pytest.approx(1.0)
    finally:
        session.close()


def test_industry_exposure_level_2(sqlite_session):
    session = sqlite_session()
    try:
        for symbol, pct in [("S1", 50.0), ("S2", 50.0)]:
            session.add(
                EtfHolding(
                    etf_symbol="0050",
                    holding_date=HOLDING_DATE,
                    asset_symbol=symbol,
                    asset_name=f"Stock {symbol}",
                    weight=pct,
                    source_name="TEST",
                )
            )

        session.add(
            StockIndustry(stock_symbol="S1", industry_level_1="Tech", industry_level_2="Semis")
        )
        session.add(
            StockIndustry(stock_symbol="S2", industry_level_1="Tech", industry_level_2="Hardware")
        )
        session.commit()

        result = get_industry_exposure(session, "0050", level=2)

        industries = {i["industry"]: i for i in result["industries"]}
        assert industries["Semis"]["weight_fraction"] == pytest.approx(0.5)
        assert industries["Hardware"]["weight_fraction"] == pytest.approx(0.5)
    finally:
        session.close()


def test_industry_exposure_no_holdings(sqlite_session):
    session = sqlite_session()
    try:
        result = get_industry_exposure(session, "NOPE")
        assert result["industries"] == []
        assert result["max_industry"] is None
        assert result["unclassified"]["weight_fraction"] == 0.0
    finally:
        session.close()
