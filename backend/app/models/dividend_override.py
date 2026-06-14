from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class EtfDividendFrequencyOverride(Base):
    """Manual override for an ETF's 配息週期 (dividend frequency).

    When present, this takes precedence over both the classified frequency
    and ``EtfMaster.dividend_frequency``. The table is empty by default;
    rows are inserted manually to correct mis-classifications.
    """

    __tablename__ = "etf_dividend_frequency_overrides"

    id: Mapped[int] = mapped_column(primary_key=True)
    etf_symbol: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    frequency: Mapped[str] = mapped_column(Text, nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime, server_default="now()"
    )
