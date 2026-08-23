"""split calculus topic into limit and integral

Revision ID: c8f4a5b6d7e8
Revises: b7e2f3a4c5d6
Create Date: 2026-08-21 13:00:00.000000

"""
from alembic import op


revision = 'c8f4a5b6d7e8'
down_revision = 'b7e2f3a4c5d6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE questions SET topic = 'limit' WHERE topic = 'calculus' AND question_type = 'limit'")
    op.execute(
        "UPDATE questions SET topic = 'integral' "
        "WHERE topic = 'calculus' AND question_type = 'definite_integral'"
    )


def downgrade() -> None:
    op.execute("UPDATE questions SET topic = 'calculus' WHERE topic IN ('limit', 'integral')")
