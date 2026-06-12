from datetime import date, datetime

from sqlalchemy import Date, DateTime, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class EtfDividend(Base):
    """ETF 配息資料."""

    __tablename__ = "etf_dividends"
    __table_args__ = (
        UniqueConstraint("etf_symbol", "ex_dividend_date", "source_name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    etf_symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    ex_dividend_date: Mapped[date] = mapped_column(Date, nullable=False)
    payment_date: Mapped[date | None] = mapped_column(Date)
    dividend_amount: Mapped[float | None] = mapped_column(Numeric)
    dividend_yield: Mapped[float | None] = mapped_column(Numeric)

    source_name: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(Text)
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime)

    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default="now()")
