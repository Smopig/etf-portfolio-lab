"""Tests for concentration_service using an in-memory SQLite DB."""

from __future__ import annotations

import datetime as dt

import pytest
from sqlalchemy import MetaData, create_engine
from sqlalchemy.orm import sessionmaker

from app.models import EtfHolding, EtfMaster
from app.services.concentration_service import get_concentration, get_top_holdings

TABLES = [
    EtfMaster.__table__,
    EtfHolding.__table__,
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

# Weights sum to 100%: 40, 25, 15, 10, 5, 5
PERCENT_WEIGHTS = [
    ("S1", "Stock 1", 40.0),
    ("S2", "Stock 2", 25.0),
    ("S3", "Stock 3", 15.0),
    ("S4", "Stock 4", 10.0),
    ("S5", "Stock 5", 5.0),
    ("S6", "Stock 6", 5.0),
]

# Hand-computed HHI = 0.40^2 + 0.25^2 + 0.15^2 + 0.10^2 + 0.05^2 + 0.05^2
EXPECTED_HHI = 0.40**2 + 0.25**2 + 0.15**2 + 0.10**2 + 0.05**2 + 0.05**2


def _seed(session, etf_symbol="0050", scale="percent"):
    for symbol, name, pct in PERCENT_WEIGHTS:
        weight = pct if scale == "percent" else pct / 100.0
        session.add(
            EtfHolding(
                etf_symbol=etf_symbol,
                holding_date=HOLDING_DATE,
                asset_symbol=symbol,
                asset_name=name,
                weight=weight,
                source_name="TEST",
            )
        )
    session.commit()


@pytest.mark.parametrize("scale", ["percent", "fraction"])
def test_get_concentration(sqlite_session, scale):
    session = sqlite_session()
    try:
        _seed(session, scale=scale)

        result = get_concentration(session, "0050")

        assert result["holding_date"] == HOLDING_DATE
        assert result["num_holdings"] == 6

        assert result["top1_fraction"] == pytest.approx(0.40)
        assert result["top1_pct"] == pytest.approx(40.0)

        assert result["top3_fraction"] == pytest.approx(0.40 + 0.25 + 0.15)
        assert result["top3_pct"] == pytest.approx(80.0)

        assert result["top5_fraction"] == pytest.approx(0.40 + 0.25 + 0.15 + 0.10 + 0.05)
        assert result["top10_fraction"] == pytest.approx(1.0)

        assert result["hhi"] == pytest.approx(EXPECTED_HHI)
        assert result["effective_holdings"] == pytest.approx(1.0 / EXPECTED_HHI)
    finally:
        session.close()


def test_get_top_holdings(sqlite_session):
    session = sqlite_session()
    try:
        _seed(session)

        top3 = get_top_holdings(session, "0050", n=3)

        assert len(top3) == 3
        assert [h["asset_symbol"] for h in top3] == ["S1", "S2", "S3"]
        assert top3[0]["weight_fraction"] == pytest.approx(0.40)
        assert top3[0]["weight_pct"] == pytest.approx(40.0)
    finally:
        session.close()


def test_get_concentration_no_holdings(sqlite_session):
    session = sqlite_session()
    try:
        result = get_concentration(session, "NOPE")
        assert result["holding_date"] is None
        assert result["num_holdings"] == 0
        assert result["hhi"] is None

        assert get_top_holdings(session, "NOPE") == []
    finally:
        session.close()
