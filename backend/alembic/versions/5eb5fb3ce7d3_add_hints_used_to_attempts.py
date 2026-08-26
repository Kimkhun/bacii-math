"""add hints_used to attempts

Revision ID: 5eb5fb3ce7d3
Revises: e5a0c4b3d2f1
Create Date: 2026-08-26 10:37:06.329296

"""
from alembic import op
import sqlalchemy as sa

revision = '5eb5fb3ce7d3'
down_revision = 'e5a0c4b3d2f1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Scoped to this change only — autogenerate also flagged unrelated
    # pre-existing nullability drift on study_sessions.{created_at,updated_at}
    # (a separate, older discrepancy), which is left untouched here.
    op.add_column('attempts', sa.Column('hints_used', sa.Integer(), server_default='0', nullable=False))


def downgrade() -> None:
    op.drop_column('attempts', 'hints_used')
