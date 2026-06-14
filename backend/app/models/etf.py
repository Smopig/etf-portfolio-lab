from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class EtfMaster(Base):
    """ETF 主檔."""

    __tablename__ = "etf_master"

    id: Mapped[int] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    issuer: Mapped[str | None] = mapped_column(Text)
    listing_date: Mapped[date | None] = mapped_column(Date)

    management_type: Mapped[str | None] = mapped_column(Text)
    asset_class: Mapped[str | None] = mapped_column(Text)
    investment_style: Mapped[str | None] = mapped_column(Text)
    strategy_type: Mapped[str | None] = mapped_column(Text)

    tracking_index: Mapped[str | None] = mapped_column(Text)
    index_provider: Mapped[str | None] = mapped_column(Text)
    selection_method: Mapped[str | None] = mapped_column(Text)
    weighting_method: Mapped[str | None] = mapped_column(Text)
    rebalance_frequency: Mapped[str | None] = mapped_column(Text)
    replication_method: Mapped[str | None] = mapped_column(Text)

    expense_ratio: Mapped[float | None] = mapped_column(Numeric)
    management_fee: Mapped[float | None] = mapped_column(Numeric)
    custody_fee: Mapped[float | None] = mapped_column(Numeric)
    dividend_frequency: Mapped[str | None] = mapped_column(Text)

    # 規模 (AUM, NTD) + 淨值 (NAV per unit, NTD) + 淨值資料日期.
    aum: Mapped[float | None] = mapped_column(Numeric)
    nav: Mapped[float | None] = mapped_column(Numeric)
    nav_date: Mapped[date | None] = mapped_column(Date)

    source_name: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(Text)
    data_date: Mapped[date | None] = mapped_column(Date)
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime)
    confidence_level: Mapped[str | None] = mapped_column(Text)

    is_active: Mapped[bool | None] = mapped_column(Boolean, server_default="true")
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default="now()")
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, server_default="now()")
