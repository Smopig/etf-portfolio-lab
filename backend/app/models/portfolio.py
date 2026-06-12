from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Portfolio(Base):
    """使用者配置方案."""

    __tablename__ = "portfolio"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    base_currency: Mapped[str | None] = mapped_column(Text, server_default="TWD")
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default="now()")
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, server_default="now()")


class PortfolioItem(Base):
    """配置方案明細."""

    __tablename__ = "portfolio_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolio.id"), nullable=False)
    etf_symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    target_weight: Mapped[float] = mapped_column(Numeric, nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default="now()")


class BacktestRun(Base):
    """回測紀錄."""

    __tablename__ = "backtest_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    portfolio_id: Mapped[int | None] = mapped_column(ForeignKey("portfolio.id"))
    name: Mapped[str | None] = mapped_column(Text)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)

    initial_amount: Mapped[float] = mapped_column(Numeric, nullable=False)
    monthly_contribution: Mapped[float | None] = mapped_column(Numeric, server_default="0")

    rebalance_frequency: Mapped[str | None] = mapped_column(Text)
    dividend_reinvest: Mapped[bool | None] = mapped_column(Boolean, server_default="true")
    transaction_cost_rate: Mapped[float | None] = mapped_column(Numeric, server_default="0")

    final_value: Mapped[float | None] = mapped_column(Numeric)
    total_contribution: Mapped[float | None] = mapped_column(Numeric)
    total_profit: Mapped[float | None] = mapped_column(Numeric)
    cagr: Mapped[float | None] = mapped_column(Numeric)
    max_drawdown: Mapped[float | None] = mapped_column(Numeric)
    annualized_volatility: Mapped[float | None] = mapped_column(Numeric)
    sharpe_ratio: Mapped[float | None] = mapped_column(Numeric)

    result_json: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default="now()")


class ProjectionRun(Base):
    """財務模擬紀錄."""

    __tablename__ = "projection_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str | None] = mapped_column(Text)
    initial_amount: Mapped[float] = mapped_column(Numeric, nullable=False)
    monthly_contribution: Mapped[float | None] = mapped_column(Numeric, server_default="0")
    annual_return_rate: Mapped[float] = mapped_column(Numeric, nullable=False)
    years: Mapped[int] = mapped_column(Integer, nullable=False)
    target_amount: Mapped[float | None] = mapped_column(Numeric)

    final_value: Mapped[float | None] = mapped_column(Numeric)
    total_contribution: Mapped[float | None] = mapped_column(Numeric)
    total_profit: Mapped[float | None] = mapped_column(Numeric)
    target_achieved: Mapped[bool | None] = mapped_column(Boolean)
    result_json: Mapped[dict | None] = mapped_column(JSONB)

    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default="now()")
