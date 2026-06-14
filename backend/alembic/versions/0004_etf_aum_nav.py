"""add aum/nav/nav_date columns to etf_master

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-14

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("etf_master", sa.Column("aum", sa.Numeric(), nullable=True))
    op.add_column("etf_master", sa.Column("nav", sa.Numeric(), nullable=True))
    op.add_column("etf_master", sa.Column("nav_date", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("etf_master", "nav_date")
    op.drop_column("etf_master", "nav")
    op.drop_column("etf_master", "aum")
