"""add fetch_logs table

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "fetch_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider_name", sa.Text(), nullable=False),
        sa.Column("dataset_type", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("rows_fetched", sa.Integer()),
        sa.Column("rows_inserted", sa.Integer()),
        sa.Column("source_url", sa.Text()),
        sa.Column("data_date", sa.Date()),
        sa.Column("message", sa.Text()),
        sa.Column("started_at", sa.DateTime()),
        sa.Column("finished_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("fetch_logs")
