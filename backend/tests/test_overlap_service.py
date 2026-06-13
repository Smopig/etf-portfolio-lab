"""Tests for overlap_service using an in-memory SQLite DB."""

from __future__ import annotations

import datetime as dt

import pytest
from sqlalchemy import MetaData, create_engine
from sqlalchemy.orm import sessionmaker

from app.models import EtfHolding, StockIndustry
from app.services.overlap_service import (
    get_industry_similarity,
    get_multi_overlap,
    get_pairwise_overlap,
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


def _add_holding(session, etf_symbol, asset_symbol, weight, asset_name=None, holding_date=HOLDING_DATE):
    session.add(
        EtfHolding(
            etf_symbol=etf_symbol,
            holding_date=holding_date,
            asset_symbol=asset_symbol,
            asset_name=asset_name or f"Stock {asset_symbol}",
            weight=weight,
            source_name="TEST",
        )
    )


def test_pairwise_overlap_hand_computed(sqlite_session):
    session = sqlite_session()
    try:
        # ETF A: S1 50%, S2 30%, S3 20%
        for sym, w in [("S1", 50.0), ("S2", 30.0), ("S3", 20.0)]:
            _add_holding(session, "AAA", sym, w)
        # ETF B: S1 40%, S2 20%, S4 40%
        for sym, w in [("S1", 40.0), ("S2", 20.0), ("S4", 40.0)]:
            _add_holding(session, "BBB", sym, w)
        session.commit()

        result = get_pairwise_overlap(session, "AAA", "BBB")

        # common assets: S1, S2
        assert result["overlap_count"] == 2

        # weighted overlap = min(0.5,0.4) + min(0.3,0.2) = 0.4 + 0.2 = 0.6
        assert result["weighted_overlap_fraction"] == pytest.approx(0.6)
        assert result["weighted_overlap_pct"] == pytest.approx(60.0)

        # jaccard = |{S1,S2}| / |{S1,S2,S3,S4}| = 2/4 = 0.5
        assert result["jaccard"] == pytest.approx(0.5)

        # rating: 0.6 -> 中度重疊
        assert result["overlap_rating"]["label"] == "中度重疊"
        assert result["overlap_rating"]["value"] == pytest.approx(0.6)

        # overlap_assets sorted by min_weight desc
        syms = [a["asset_symbol"] for a in result["overlap_assets"]]
        assert syms == ["S1", "S2"]
        assert result["overlap_assets"][0]["min_weight_pct"] == pytest.approx(40.0)
        assert result["overlap_assets"][1]["min_weight_pct"] == pytest.approx(20.0)
    finally:
        session.close()


def test_pairwise_overlap_scale_invariance(sqlite_session):
    session = sqlite_session()
    try:
        # Percent-scale fixture
        for sym, w in [("S1", 50.0), ("S2", 30.0), ("S3", 20.0)]:
            _add_holding(session, "PCT_A", sym, w)
        for sym, w in [("S1", 40.0), ("S2", 20.0), ("S4", 40.0)]:
            _add_holding(session, "PCT_B", sym, w)

        # Fraction-scale fixture (same proportions)
        for sym, w in [("S1", 0.50), ("S2", 0.30), ("S3", 0.20)]:
            _add_holding(session, "FRAC_A", sym, w)
        for sym, w in [("S1", 0.40), ("S2", 0.20), ("S4", 0.40)]:
            _add_holding(session, "FRAC_B", sym, w)

        session.commit()

        pct_result = get_pairwise_overlap(session, "PCT_A", "PCT_B")
        frac_result = get_pairwise_overlap(session, "FRAC_A", "FRAC_B")

        assert pct_result["weighted_overlap_fraction"] == pytest.approx(
            frac_result["weighted_overlap_fraction"]
        )
        assert pct_result["weighted_overlap_fraction"] == pytest.approx(0.6)
    finally:
        session.close()


def test_pairwise_overlap_self(sqlite_session):
    session = sqlite_session()
    try:
        for sym, w in [("S1", 50.0), ("S2", 30.0), ("S3", 20.0)]:
            _add_holding(session, "AAA", sym, w)
        session.commit()

        result = get_pairwise_overlap(session, "AAA", "AAA")

        assert result["weighted_overlap_fraction"] == pytest.approx(1.0)
        assert result["jaccard"] == pytest.approx(1.0)
        assert result["overlap_count"] == 3
        assert result["overlap_rating"]["label"] == "高度重疊"
    finally:
        session.close()


def test_industry_similarity(sqlite_session):
    session = sqlite_session()
    try:
        # ETF A: S1 60% Tech, S2 40% Finance
        for sym, w in [("S1", 60.0), ("S2", 40.0)]:
            _add_holding(session, "AAA", sym, w)
        # ETF B: S3 50% Tech, S4 50% Healthcare
        for sym, w in [("S3", 50.0), ("S4", 50.0)]:
            _add_holding(session, "BBB", sym, w)

        session.add(StockIndustry(stock_symbol="S1", industry_level_1="Tech", industry_level_2="Semis"))
        session.add(StockIndustry(stock_symbol="S2", industry_level_1="Finance", industry_level_2="Banks"))
        session.add(StockIndustry(stock_symbol="S3", industry_level_1="Tech", industry_level_2="Hardware"))
        session.add(StockIndustry(stock_symbol="S4", industry_level_1="Healthcare", industry_level_2="Pharma"))
        session.commit()

        result = get_industry_similarity(session, "AAA", "BBB", level=1)

        # shared industry: Tech -> min(0.6, 0.5) = 0.5
        # Finance (A only) and Healthcare (B only) contribute 0
        assert result["industry_similarity_fraction"] == pytest.approx(0.5)
        assert result["industry_similarity_pct"] == pytest.approx(50.0)

        breakdown = {b["industry"]: b for b in result["breakdown"]}
        assert breakdown["Tech"]["min_weight_pct"] == pytest.approx(50.0)
        assert breakdown["Finance"]["min_weight_pct"] == pytest.approx(0.0)
        assert breakdown["Healthcare"]["min_weight_pct"] == pytest.approx(0.0)
    finally:
        session.close()


def test_multi_overlap(sqlite_session):
    session = sqlite_session()
    try:
        # ETF A: S1 50%, S2 50%
        for sym, w in [("S1", 50.0), ("S2", 50.0)]:
            _add_holding(session, "AAA", sym, w)
        # ETF B: S1 50%, S3 50%
        for sym, w in [("S1", 50.0), ("S3", 50.0)]:
            _add_holding(session, "BBB", sym, w)
        # ETF C: S2 50%, S3 50%
        for sym, w in [("S2", 50.0), ("S3", 50.0)]:
            _add_holding(session, "CCC", sym, w)
        session.commit()

        result = get_multi_overlap(session, ["AAA", "BBB", "CCC"])

        assert result["symbols"] == ["AAA", "BBB", "CCC"]
        n = len(result["symbols"])

        # diagonal = 100
        for i in range(n):
            assert result["matrix"][i][i] == pytest.approx(100.0)

        # symmetric
        for i in range(n):
            for j in range(n):
                assert result["matrix"][i][j] == pytest.approx(result["matrix"][j][i])

        # AAA vs BBB overlap = min(0.5, 0.5) for S1 = 0.5 -> 50.0
        assert result["matrix"][0][1] == pytest.approx(50.0)
        assert result["matrix"][0][2] == pytest.approx(50.0)
        assert result["matrix"][1][2] == pytest.approx(50.0)

        assert len(result["pairs"]) == 3
    finally:
        session.close()


def test_pairwise_overlap_disjoint(sqlite_session):
    session = sqlite_session()
    try:
        for sym, w in [("S1", 50.0), ("S2", 50.0)]:
            _add_holding(session, "AAA", sym, w)
        for sym, w in [("S3", 50.0), ("S4", 50.0)]:
            _add_holding(session, "BBB", sym, w)
        session.commit()

        result = get_pairwise_overlap(session, "AAA", "BBB")

        assert result["weighted_overlap_fraction"] == pytest.approx(0.0)
        assert result["overlap_count"] == 0
        assert result["overlap_rating"]["label"] == "極低重疊"
        assert result["jaccard"] == pytest.approx(0.0)
    finally:
        session.close()


def test_pairwise_overlap_missing_etf(sqlite_session):
    session = sqlite_session()
    try:
        for sym, w in [("S1", 50.0), ("S2", 50.0)]:
            _add_holding(session, "AAA", sym, w)
        session.commit()

        result = get_pairwise_overlap(session, "AAA", "NOPE")

        assert result["overlap_count"] == 0
        assert result["overlap_assets"] == []
        assert result["weighted_overlap_fraction"] == 0.0
        assert result["holding_date_b"] is None
    finally:
        session.close()
