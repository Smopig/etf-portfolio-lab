from datetime import date, datetime

from sqlalchemy import Date, DateTime, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class FetchLog(Base):
    """資料擷取執行紀錄 (Phase 12 data provider automation)."""

    __tablename__ = "fetch_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    provider_name: Mapped[str] = mapped_column(Text, nullable=False)
    dataset_type: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    rows_fetched: Mapped[int | None] = mapped_column(Integer)
    rows_inserted: Mapped[int | None] = mapped_column(Integer)
    source_url: Mapped[str | None] = mapped_column(Text)
    data_date: Mapped[date | None] = mapped_column(Date)
    message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default="now()")
