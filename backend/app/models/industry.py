from datetime import date, datetime

from sqlalchemy import Date, DateTime, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class StockIndustry(Base):
    """股票產業分類."""

    __tablename__ = "stock_industry"

    id: Mapped[int] = mapped_column(primary_key=True)
    stock_symbol: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    stock_name: Mapped[str | None] = mapped_column(Text)
    market: Mapped[str | None] = mapped_column(Text)

    industry_level_1: Mapped[str | None] = mapped_column(Text)
    industry_level_2: Mapped[str | None] = mapped_column(Text)
    industry_level_3: Mapped[str | None] = mapped_column(Text)

    custom_sector: Mapped[str | None] = mapped_column(Text)
    custom_theme: Mapped[str | None] = mapped_column(Text)

    source_name: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, server_default="now()")


class EtfIndustryExposure(Base):
    """ETF 產業曝險快取表."""

    __tablename__ = "etf_industry_exposure"
    __table_args__ = (
        UniqueConstraint(
            "etf_symbol", "exposure_date", "industry_level_1", "industry_level_2"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    etf_symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    exposure_date: Mapped[date] = mapped_column(Date, nullable=False)
    industry_level_1: Mapped[str] = mapped_column(Text, nullable=False)
    industry_level_2: Mapped[str | None] = mapped_column(Text)
    weight: Mapped[float] = mapped_column(Numeric, nullable=False)
    source_holding_date: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default="now()")
