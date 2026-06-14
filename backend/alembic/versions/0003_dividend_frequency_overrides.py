"""add etf_dividend_frequency_overrides table

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-14

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "etf_dividend_frequency_overrides",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("etf_symbol", sa.String(length=20), nullable=False),
        sa.Column("frequency", sa.Text(), nullable=False),
        sa.Column("note", sa.Text()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.UniqueConstraint("etf_symbol", name="uq_dividend_freq_override_symbol"),
    )


def downgrade() -> None:
    op.drop_table("etf_dividend_frequency_overrides")
