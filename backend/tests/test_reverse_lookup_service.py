"""Tests for reverse_lookup_service using an in-memory SQLite DB."""

from __future__ import annotations

import datetime as dt

import pytest
from sqlalchemy import MetaData, create_engine
from sqlalchemy.orm import sessionmaker

from app.models import EtfHolding, StockIndustry
from app.services.reverse_lookup_service import (
    find_etfs_by_industry,
    find_etfs_by_stock,
)

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


def _seed_two_etfs(session):
    # ETF A: S1 (shared) 30%, S2 70%
    for symbol, pct in [("S1", 30.0), ("S2", 70.0)]:
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
    # ETF B: S1 (shared) 50%, S3 50%
    for symbol, pct in [("S1", 50.0), ("S3", 50.0)]:
        session.add(
            EtfHolding(
                etf_symbol="ETF_B",
                holding_date=HOLDING_DATE,
                asset_symbol=symbol,
                asset_name=f"Stock {symbol}",
                weight=pct,
                source_name="TEST",
            )
        )

    session.add(StockIndustry(stock_symbol="S1", industry_level_1="Tech"))
    session.add(StockIndustry(stock_symbol="S2", industry_level_1="Finance"))
    session.add(StockIndustry(stock_symbol="S3", industry_level_1="Tech"))
    session.commit()


def test_find_etfs_by_stock(sqlite_session):
    session = sqlite_session()
    try:
        _seed_two_etfs(session)

        results = find_etfs_by_stock(session, "S1")

        assert len(results) == 2
        assert results[0]["etf_symbol"] == "ETF_B"
        assert results[0]["weight_fraction"] == pytest.approx(0.5)
        assert results[1]["etf_symbol"] == "ETF_A"
        assert results[1]["weight_fraction"] == pytest.approx(0.3)
    finally:
        session.close()


def test_find_etfs_by_stock_not_found(sqlite_session):
    session = sqlite_session()
    try:
        _seed_two_etfs(session)
        assert find_etfs_by_stock(session, "NOPE") == []
    finally:
        session.close()


def test_find_etfs_by_industry(sqlite_session):
    session = sqlite_session()
    try:
        _seed_two_etfs(session)

        # Tech exposure: ETF_A has S1 (30%) -> 0.3; ETF_B has S1+S3 (50%+50%) -> 1.0
        results = find_etfs_by_industry(session, "Tech", level=1)

        assert len(results) == 2
        assert results[0]["etf_symbol"] == "ETF_B"
        assert results[0]["weight_fraction"] == pytest.approx(1.0)
        assert results[1]["etf_symbol"] == "ETF_A"
        assert results[1]["weight_fraction"] == pytest.approx(0.3)
    finally:
        session.close()


def test_find_etfs_by_industry_not_found(sqlite_session):
    session = sqlite_session()
    try:
        _seed_two_etfs(session)
        assert find_etfs_by_industry(session, "Energy", level=1) == []
    finally:
        session.close()
