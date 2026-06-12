from datetime import datetime

from sqlalchemy import Boolean, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class DataSourceRegistry(Base):
    """資料來源登錄表."""

    __tablename__ = "data_source_registry"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_name: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(Text, nullable=False)
    base_url: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    update_frequency: Mapped[str | None] = mapped_column(Text)
    reliability_level: Mapped[str | None] = mapped_column(Text)
    license_note: Mapped[str | None] = mapped_column(Text)
    enabled: Mapped[bool | None] = mapped_column(Boolean, server_default="true")
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default="now()")
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, server_default="now()")


class DataQualityCheck(Base):
    """資料品質檢查結果."""

    __tablename__ = "data_quality_checks"

    id: Mapped[int] = mapped_column(primary_key=True)
    dataset_type: Mapped[str] = mapped_column(Text, nullable=False)
    dataset_key: Mapped[str] = mapped_column(Text, nullable=False)
    check_name: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str | None] = mapped_column(Text)
    message: Mapped[str | None] = mapped_column(Text)
    checked_at: Mapped[datetime | None] = mapped_column(DateTime, server_default="now()")
