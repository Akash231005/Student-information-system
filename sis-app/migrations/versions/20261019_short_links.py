"""Persist short URL mappings.

Revision ID: 20261019_short_links
Revises: 20261019_active_enrollment
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261019_short_links"
down_revision: str | Sequence[str] | None = "20261019_active_enrollment"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "short_links",
        sa.Column("code", sa.String(length=16), nullable=False),
        sa.Column("target_url", sa.String(length=2048), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("code"),
    )


def downgrade() -> None:
    op.drop_table("short_links")
