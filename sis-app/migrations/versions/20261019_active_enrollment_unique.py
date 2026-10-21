"""Allow a student to re-enroll after dropping an offering.

Revision ID: 20261019_active_enrollment
Revises: c7dac0e3ea8d
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261019_active_enrollment"
down_revision: str | Sequence[str] | None = "c7dac0e3ea8d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("enrollments") as batch_op:
        batch_op.drop_constraint("uq_student_offering", type_="unique")
    op.create_index(
        "uq_active_student_offering", "enrollments", ["student_id", "offering_id"],
        unique=True,
        postgresql_where=sa.text("status = 'ENROLLED'"),
        sqlite_where=sa.text("status = 'ENROLLED'"),
    )


def downgrade() -> None:
    op.drop_index("uq_active_student_offering", table_name="enrollments")
    op.create_unique_constraint(
        "uq_student_offering", "enrollments", ["student_id", "offering_id"]
    )
