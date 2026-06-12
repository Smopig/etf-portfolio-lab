from datetime import date, datetime

from sqlalchemy import Date, DateTime, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class EtfPrice(Base):
    """ETF 歷史價格."""

    __tablename__ = "etf_prices"
    __table_args__ = (
        UniqueConstraint("etf_symbol", "trade_date", "source_name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    etf_symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    open: Mapped[float | None] = mapped_column(Numeric)
    high: Mapped[float | None] = mapped_column(Numeric)
    low: Mapped[float | None] = mapped_column(Numeric)
    close: Mapped[float | None] = mapped_column(Numeric)
    adjusted_close: Mapped[float | None] = mapped_column(Numeric)
    volume: Mapped[float | None] = mapped_column(Numeric)
    turnover: Mapped[float | None] = mapped_column(Numeric)

    source_name: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(Text)
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime)

    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default="now()")
