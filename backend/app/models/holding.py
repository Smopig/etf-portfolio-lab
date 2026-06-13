from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class EtfHolding(Base):
    """ETF 目前或指定日期成分股."""

    __tablename__ = "etf_holdings"
    __table_args__ = (
        UniqueConstraint("etf_symbol", "holding_date", "asset_symbol"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    etf_symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    holding_date: Mapped[date] = mapped_column(Date, nullable=False)
    asset_symbol: Mapped[str | None] = mapped_column(String(20))
    asset_name: Mapped[str | None] = mapped_column(Text)
    asset_type: Mapped[str | None] = mapped_column(Text)
    weight: Mapped[float | None] = mapped_column(Numeric)
    shares: Mapped[float | None] = mapped_column(Numeric)
    market_value: Mapped[float | None] = mapped_column(Numeric)

    source_name: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(Text)
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime)
    confidence_level: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default="now()")


class EtfHoldingSnapshot(Base):
    """每次抓取 ETF 持股時建立一筆快照."""

    __tablename__ = "etf_holding_snapshots"
    __table_args__ = (
        UniqueConstraint("etf_symbol", "snapshot_date", "source_name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    etf_symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    source_name: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(Text)
    raw_file_path: Mapped[str | None] = mapped_column(Text)
    parser_version: Mapped[str | None] = mapped_column(Text)
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime, server_default="now()")
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default="now()")


class EtfHoldingSnapshotItem(Base):
    """快照中的成分股明細."""

    __tablename__ = "etf_holding_snapshot_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    snapshot_id: Mapped[int] = mapped_column(
        ForeignKey("etf_holding_snapshots.id"), nullable=False
    )
    asset_symbol: Mapped[str | None] = mapped_column(String(20))
    asset_name: Mapped[str | None] = mapped_column(Text)
    asset_type: Mapped[str | None] = mapped_column(Text)
    weight: Mapped[float | None] = mapped_column(Numeric)
    shares: Mapped[float | None] = mapped_column(Numeric)
    market_value: Mapped[float | None] = mapped_column(Numeric)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default="now()")


class EtfHoldingChangeEvent(Base):
    """ETF 持股變化事件.

    change_type: ADDED / REMOVED / WEIGHT_INCREASE / WEIGHT_DECREASE / UNCHANGED
    source_type: OFFICIAL_ANNOUNCEMENT / SNAPSHOT_DIFF / MANUAL_INPUT
    """

    __tablename__ = "etf_holding_change_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    etf_symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    from_date: Mapped[date] = mapped_column(Date, nullable=False)
    to_date: Mapped[date] = mapped_column(Date, nullable=False)

    change_type: Mapped[str] = mapped_column(Text, nullable=False)
    asset_symbol: Mapped[str | None] = mapped_column(String(20))
    asset_name: Mapped[str | None] = mapped_column(Text)

    old_weight: Mapped[float | None] = mapped_column(Numeric)
    new_weight: Mapped[float | None] = mapped_column(Numeric)
    weight_delta: Mapped[float | None] = mapped_column(Numeric)

    change_reason: Mapped[str | None] = mapped_column(Text)
    confidence_level: Mapped[str | None] = mapped_column(Text)
    source_type: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default="now()")
