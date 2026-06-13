"""Seed script for ETF Portfolio Lab.

Loads sample data from /data/samples/ (if present) into the database via
SessionLocal, idempotently (skips rows that already exist based on unique
keys). If the CSV files are missing, inserts a minimal hardcoded fallback
dataset so the app has something to display.

Expected CSV files and columns (produced by the data-research agent):

- data_source_registry.csv
    columns: source_name, source_type, base_url, description,
             update_frequency, reliability_level, license_note, enabled

- etf_master.csv
    columns: symbol, name, issuer, listing_date, management_type,
             asset_class, investment_style, strategy_type, tracking_index,
             index_provider, selection_method, weighting_method,
             rebalance_frequency, replication_method, expense_ratio,
             management_fee, custody_fee, dividend_frequency,
             source_name, source_url, data_date, confidence_level

- 0050_holdings.csv (holdings for ETF symbol "0050")
    columns: etf_symbol, holding_date, asset_symbol, asset_name, asset_type,
             weight, shares, market_value, source_name, source_url,
             confidence_level

- stock_industry.csv
    columns: stock_symbol, stock_name, market, industry_level_1,
             industry_level_2, industry_level_3, custom_sector,
             custom_theme, source_name, source_url

Run with:
    python -m scripts.seed
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pandas as pd

from app.core.database import SessionLocal
from app.models import (
    DataSourceRegistry,
    EtfHolding,
    EtfMaster,
    StockIndustry,
)
from app.utils.importers import _clean, _parse_date

SAMPLES_DIR = Path("/data/samples")


def seed_data_source_registry(session) -> None:
    csv_path = SAMPLES_DIR / "data_source_registry.csv"
    if csv_path.exists():
        df = pd.read_csv(csv_path)
        for _, row in df.iterrows():
            source_name = _clean(row.get("source_name"))
            source_type = _clean(row.get("source_type"))
            if not source_name or not source_type:
                continue
            exists = (
                session.query(DataSourceRegistry)
                .filter_by(source_name=source_name, source_type=source_type)
                .first()
            )
            if exists:
                continue
            session.add(
                DataSourceRegistry(
                    source_name=source_name,
                    source_type=source_type,
                    base_url=_clean(row.get("base_url")),
                    description=_clean(row.get("description")),
                    update_frequency=_clean(row.get("update_frequency")),
                    reliability_level=_clean(row.get("reliability_level")),
                    license_note=_clean(row.get("license_note")),
                    enabled=bool(row.get("enabled", True)),
                )
            )
        session.commit()
        print(f"Seeded data_source_registry from {csv_path}")
    else:
        # Minimal hardcoded fallback
        fallback = [
            dict(
                source_name="TWSE OpenAPI",
                source_type="OFFICIAL",
                base_url="https://openapi.twse.com.tw",
                description="Taiwan Stock Exchange open data API",
                update_frequency="daily",
                reliability_level="high",
                license_note="Public domain / open data",
                enabled=True,
            ),
            dict(
                source_name="Yuanta ETF Official Site",
                source_type="ISSUER",
                base_url="https://www.yuantaetfs.com",
                description="Yuanta Securities Investment Trust ETF info",
                update_frequency="daily",
                reliability_level="high",
                license_note="Issuer official disclosure",
                enabled=True,
            ),
        ]
        for entry in fallback:
            exists = (
                session.query(DataSourceRegistry)
                .filter_by(
                    source_name=entry["source_name"], source_type=entry["source_type"]
                )
                .first()
            )
            if exists:
                continue
            session.add(DataSourceRegistry(**entry))
        session.commit()
        print("Seeded data_source_registry with hardcoded fallback")


def seed_etf_master(session) -> None:
    csv_path = SAMPLES_DIR / "etf_master.csv"
    if csv_path.exists():
        df = pd.read_csv(csv_path)
        for _, row in df.iterrows():
            symbol = _clean(row.get("symbol"))
            if not symbol:
                continue
            exists = session.query(EtfMaster).filter_by(symbol=symbol).first()
            if exists:
                continue
            session.add(
                EtfMaster(
                    symbol=symbol,
                    name=_clean(row.get("name")) or symbol,
                    issuer=_clean(row.get("issuer")),
                    listing_date=_parse_date(row.get("listing_date")),
                    management_type=_clean(row.get("management_type")),
                    asset_class=_clean(row.get("asset_class")),
                    investment_style=_clean(row.get("investment_style")),
                    strategy_type=_clean(row.get("strategy_type")),
                    tracking_index=_clean(row.get("tracking_index")),
                    index_provider=_clean(row.get("index_provider")),
                    selection_method=_clean(row.get("selection_method")),
                    weighting_method=_clean(row.get("weighting_method")),
                    rebalance_frequency=_clean(row.get("rebalance_frequency")),
                    replication_method=_clean(row.get("replication_method")),
                    expense_ratio=_clean(row.get("expense_ratio")),
                    management_fee=_clean(row.get("management_fee")),
                    custody_fee=_clean(row.get("custody_fee")),
                    dividend_frequency=_clean(row.get("dividend_frequency")),
                    source_name=_clean(row.get("source_name")),
                    source_url=_clean(row.get("source_url")),
                    data_date=_parse_date(row.get("data_date")),
                    fetched_at=dt.datetime.utcnow(),
                    confidence_level=_clean(row.get("confidence_level")),
                )
            )
        session.commit()
        print(f"Seeded etf_master from {csv_path}")
    else:
        fallback = [
            dict(
                symbol="0050",
                name="元大台灣50",
                issuer="元大投信",
                asset_class="equity",
                tracking_index="台灣50指數",
                confidence_level="low",
            ),
            dict(
                symbol="0056",
                name="元大高股息",
                issuer="元大投信",
                asset_class="equity",
                tracking_index="台灣高股息指數",
                confidence_level="low",
            ),
        ]
        for entry in fallback:
            exists = session.query(EtfMaster).filter_by(symbol=entry["symbol"]).first()
            if exists:
                continue
            session.add(EtfMaster(**entry))
        session.commit()
        print("Seeded etf_master with hardcoded fallback")


def seed_holdings(session) -> None:
    csv_path = SAMPLES_DIR / "0050_holdings.csv"
    if csv_path.exists():
        df = pd.read_csv(csv_path)
        for _, row in df.iterrows():
            etf_symbol = _clean(row.get("etf_symbol")) or "0050"
            holding_date = _parse_date(row.get("holding_date"))
            asset_symbol = _clean(row.get("asset_symbol"))
            if holding_date is None:
                continue
            exists = (
                session.query(EtfHolding)
                .filter_by(
                    etf_symbol=etf_symbol,
                    holding_date=holding_date,
                    asset_symbol=asset_symbol,
                )
                .first()
            )
            if exists:
                continue
            session.add(
                EtfHolding(
                    etf_symbol=etf_symbol,
                    holding_date=holding_date,
                    asset_symbol=asset_symbol,
                    asset_name=_clean(row.get("asset_name")),
                    asset_type=_clean(row.get("asset_type")),
                    weight=_clean(row.get("weight")),
                    shares=_clean(row.get("shares")),
                    market_value=_clean(row.get("market_value")),
                    source_name=_clean(row.get("source_name")),
                    source_url=_clean(row.get("source_url")),
                    fetched_at=dt.datetime.utcnow(),
                    confidence_level=_clean(row.get("confidence_level")),
                )
            )
        session.commit()
        print(f"Seeded etf_holdings from {csv_path}")
    else:
        today = dt.date.today()
        fallback = [
            ("2330", "台積電", 0.45),
            ("2317", "鴻海", 0.05),
            ("2454", "聯發科", 0.04),
        ]
        for asset_symbol, asset_name, weight in fallback:
            exists = (
                session.query(EtfHolding)
                .filter_by(
                    etf_symbol="0050", holding_date=today, asset_symbol=asset_symbol
                )
                .first()
            )
            if exists:
                continue
            session.add(
                EtfHolding(
                    etf_symbol="0050",
                    holding_date=today,
                    asset_symbol=asset_symbol,
                    asset_name=asset_name,
                    asset_type="equity",
                    weight=weight,
                    confidence_level="low",
                )
            )
        session.commit()
        print("Seeded etf_holdings (0050) with hardcoded fallback")


def seed_stock_industry(session) -> None:
    csv_path = SAMPLES_DIR / "stock_industry.csv"
    if csv_path.exists():
        df = pd.read_csv(csv_path)
        for _, row in df.iterrows():
            stock_symbol = _clean(row.get("stock_symbol"))
            if not stock_symbol:
                continue
            exists = (
                session.query(StockIndustry)
                .filter_by(stock_symbol=stock_symbol)
                .first()
            )
            if exists:
                continue
            session.add(
                StockIndustry(
                    stock_symbol=stock_symbol,
                    stock_name=_clean(row.get("stock_name")),
                    market=_clean(row.get("market")),
                    industry_level_1=_clean(row.get("industry_level_1")),
                    industry_level_2=_clean(row.get("industry_level_2")),
                    industry_level_3=_clean(row.get("industry_level_3")),
                    custom_sector=_clean(row.get("custom_sector")),
                    custom_theme=_clean(row.get("custom_theme")),
                    source_name=_clean(row.get("source_name")),
                    source_url=_clean(row.get("source_url")),
                )
            )
        session.commit()
        print(f"Seeded stock_industry from {csv_path}")
    else:
        fallback = [
            ("2330", "台積電", "半導體業", "電子工業"),
            ("2317", "鴻海", "電腦及週邊設備業", "電子工業"),
            ("2454", "聯發科", "半導體業", "電子工業"),
        ]
        for stock_symbol, stock_name, industry_level_1, industry_level_2 in fallback:
            exists = (
                session.query(StockIndustry)
                .filter_by(stock_symbol=stock_symbol)
                .first()
            )
            if exists:
                continue
            session.add(
                StockIndustry(
                    stock_symbol=stock_symbol,
                    stock_name=stock_name,
                    market="TWSE",
                    industry_level_1=industry_level_1,
                    industry_level_2=industry_level_2,
                )
            )
        session.commit()
        print("Seeded stock_industry with hardcoded fallback")


def main() -> None:
    session = SessionLocal()
    try:
        seed_data_source_registry(session)
        seed_etf_master(session)
        seed_holdings(session)
        seed_stock_industry(session)
    finally:
        session.close()


if __name__ == "__main__":
    main()
