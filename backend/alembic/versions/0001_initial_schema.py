"""initial schema - create all 15 tables

Revision ID: 0001
Revises:
Create Date: 2026-06-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "etf_master",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("issuer", sa.Text()),
        sa.Column("listing_date", sa.Date()),
        sa.Column("management_type", sa.Text()),
        sa.Column("asset_class", sa.Text()),
        sa.Column("investment_style", sa.Text()),
        sa.Column("strategy_type", sa.Text()),
        sa.Column("tracking_index", sa.Text()),
        sa.Column("index_provider", sa.Text()),
        sa.Column("selection_method", sa.Text()),
        sa.Column("weighting_method", sa.Text()),
        sa.Column("rebalance_frequency", sa.Text()),
        sa.Column("replication_method", sa.Text()),
        sa.Column("expense_ratio", sa.Numeric()),
        sa.Column("management_fee", sa.Numeric()),
        sa.Column("custody_fee", sa.Numeric()),
        sa.Column("dividend_frequency", sa.Text()),
        sa.Column("source_name", sa.Text()),
        sa.Column("source_url", sa.Text()),
        sa.Column("data_date", sa.Date()),
        sa.Column("fetched_at", sa.DateTime()),
        sa.Column("confidence_level", sa.Text()),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.UniqueConstraint("symbol"),
    )

    op.create_table(
        "etf_holdings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("etf_symbol", sa.String(length=20), nullable=False),
        sa.Column("holding_date", sa.Date(), nullable=False),
        sa.Column("asset_symbol", sa.String(length=20)),
        sa.Column("asset_name", sa.Text()),
        sa.Column("asset_type", sa.Text()),
        sa.Column("weight", sa.Numeric()),
        sa.Column("shares", sa.Numeric()),
        sa.Column("market_value", sa.Numeric()),
        sa.Column("source_name", sa.Text()),
        sa.Column("source_url", sa.Text()),
        sa.Column("fetched_at", sa.DateTime()),
        sa.Column("confidence_level", sa.Text()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.UniqueConstraint("etf_symbol", "holding_date", "asset_symbol"),
    )

    op.create_table(
        "stock_industry",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("stock_symbol", sa.String(length=20), nullable=False),
        sa.Column("stock_name", sa.Text()),
        sa.Column("market", sa.Text()),
        sa.Column("industry_level_1", sa.Text()),
        sa.Column("industry_level_2", sa.Text()),
        sa.Column("industry_level_3", sa.Text()),
        sa.Column("custom_sector", sa.Text()),
        sa.Column("custom_theme", sa.Text()),
        sa.Column("source_name", sa.Text()),
        sa.Column("source_url", sa.Text()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.UniqueConstraint("stock_symbol"),
    )

    op.create_table(
        "etf_industry_exposure",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("etf_symbol", sa.String(length=20), nullable=False),
        sa.Column("exposure_date", sa.Date(), nullable=False),
        sa.Column("industry_level_1", sa.Text(), nullable=False),
        sa.Column("industry_level_2", sa.Text()),
        sa.Column("weight", sa.Numeric(), nullable=False),
        sa.Column("source_holding_date", sa.Date()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.UniqueConstraint(
            "etf_symbol", "exposure_date", "industry_level_1", "industry_level_2"
        ),
    )

    op.create_table(
        "etf_holding_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("etf_symbol", sa.String(length=20), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("source_name", sa.Text()),
        sa.Column("source_url", sa.Text()),
        sa.Column("raw_file_path", sa.Text()),
        sa.Column("parser_version", sa.Text()),
        sa.Column("fetched_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.UniqueConstraint("etf_symbol", "snapshot_date", "source_name"),
    )

    op.create_table(
        "etf_holding_snapshot_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "snapshot_id",
            sa.Integer(),
            sa.ForeignKey("etf_holding_snapshots.id"),
            nullable=False,
        ),
        sa.Column("asset_symbol", sa.String(length=20)),
        sa.Column("asset_name", sa.Text()),
        sa.Column("asset_type", sa.Text()),
        sa.Column("weight", sa.Numeric()),
        sa.Column("shares", sa.Numeric()),
        sa.Column("market_value", sa.Numeric()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
    )

    op.create_table(
        "etf_holding_change_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("etf_symbol", sa.String(length=20), nullable=False),
        sa.Column("from_date", sa.Date(), nullable=False),
        sa.Column("to_date", sa.Date(), nullable=False),
        sa.Column("change_type", sa.Text(), nullable=False),
        sa.Column("asset_symbol", sa.String(length=20)),
        sa.Column("asset_name", sa.Text()),
        sa.Column("old_weight", sa.Numeric()),
        sa.Column("new_weight", sa.Numeric()),
        sa.Column("weight_delta", sa.Numeric()),
        sa.Column("change_reason", sa.Text()),
        sa.Column("confidence_level", sa.Text()),
        sa.Column("source_type", sa.Text()),
        sa.Column("source_url", sa.Text()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
    )

    op.create_table(
        "etf_prices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("etf_symbol", sa.String(length=20), nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("open", sa.Numeric()),
        sa.Column("high", sa.Numeric()),
        sa.Column("low", sa.Numeric()),
        sa.Column("close", sa.Numeric()),
        sa.Column("adjusted_close", sa.Numeric()),
        sa.Column("volume", sa.Numeric()),
        sa.Column("turnover", sa.Numeric()),
        sa.Column("source_name", sa.Text()),
        sa.Column("source_url", sa.Text()),
        sa.Column("fetched_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.UniqueConstraint("etf_symbol", "trade_date", "source_name"),
    )

    op.create_table(
        "etf_dividends",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("etf_symbol", sa.String(length=20), nullable=False),
        sa.Column("ex_dividend_date", sa.Date(), nullable=False),
        sa.Column("payment_date", sa.Date()),
        sa.Column("dividend_amount", sa.Numeric()),
        sa.Column("dividend_yield", sa.Numeric()),
        sa.Column("source_name", sa.Text()),
        sa.Column("source_url", sa.Text()),
        sa.Column("fetched_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.UniqueConstraint("etf_symbol", "ex_dividend_date", "source_name"),
    )

    op.create_table(
        "portfolio",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("base_currency", sa.Text(), server_default="TWD"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()")),
    )

    op.create_table(
        "portfolio_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("portfolio_id", sa.Integer(), sa.ForeignKey("portfolio.id"), nullable=False),
        sa.Column("etf_symbol", sa.String(length=20), nullable=False),
        sa.Column("target_weight", sa.Numeric(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
    )

    op.create_table(
        "backtest_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("portfolio_id", sa.Integer(), sa.ForeignKey("portfolio.id")),
        sa.Column("name", sa.Text()),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("initial_amount", sa.Numeric(), nullable=False),
        sa.Column("monthly_contribution", sa.Numeric(), server_default="0"),
        sa.Column("rebalance_frequency", sa.Text()),
        sa.Column("dividend_reinvest", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("transaction_cost_rate", sa.Numeric(), server_default="0"),
        sa.Column("final_value", sa.Numeric()),
        sa.Column("total_contribution", sa.Numeric()),
        sa.Column("total_profit", sa.Numeric()),
        sa.Column("cagr", sa.Numeric()),
        sa.Column("max_drawdown", sa.Numeric()),
        sa.Column("annualized_volatility", sa.Numeric()),
        sa.Column("sharpe_ratio", sa.Numeric()),
        sa.Column("result_json", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
    )

    op.create_table(
        "projection_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.Text()),
        sa.Column("initial_amount", sa.Numeric(), nullable=False),
        sa.Column("monthly_contribution", sa.Numeric(), server_default="0"),
        sa.Column("annual_return_rate", sa.Numeric(), nullable=False),
        sa.Column("years", sa.Integer(), nullable=False),
        sa.Column("target_amount", sa.Numeric()),
        sa.Column("final_value", sa.Numeric()),
        sa.Column("total_contribution", sa.Numeric()),
        sa.Column("total_profit", sa.Numeric()),
        sa.Column("target_achieved", sa.Boolean()),
        sa.Column("result_json", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
    )

    op.create_table(
        "data_source_registry",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_name", sa.Text(), nullable=False),
        sa.Column("source_type", sa.Text(), nullable=False),
        sa.Column("base_url", sa.Text()),
        sa.Column("description", sa.Text()),
        sa.Column("update_frequency", sa.Text()),
        sa.Column("reliability_level", sa.Text()),
        sa.Column("license_note", sa.Text()),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()")),
    )

    op.create_table(
        "data_quality_checks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("dataset_type", sa.Text(), nullable=False),
        sa.Column("dataset_key", sa.Text(), nullable=False),
        sa.Column("check_name", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("severity", sa.Text()),
        sa.Column("message", sa.Text()),
        sa.Column("checked_at", sa.DateTime(), server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("data_quality_checks")
    op.drop_table("data_source_registry")
    op.drop_table("projection_runs")
    op.drop_table("backtest_runs")
    op.drop_table("portfolio_items")
    op.drop_table("portfolio")
    op.drop_table("etf_dividends")
    op.drop_table("etf_prices")
    op.drop_table("etf_holding_change_events")
    op.drop_table("etf_holding_snapshot_items")
    op.drop_table("etf_holding_snapshots")
    op.drop_table("etf_industry_exposure")
    op.drop_table("stock_industry")
    op.drop_table("etf_holdings")
    op.drop_table("etf_master")
