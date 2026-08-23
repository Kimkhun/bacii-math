"""add work_text and step_check to attempts

Revision ID: e0a1b2c3d4e5
Revises: d9f6a7b8c9e0
Create Date: 2026-08-22 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = 'e0a1b2c3d4e5'
down_revision = 'd9f6a7b8c9e0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('attempts', sa.Column('work_text', sa.Text(), nullable=True))
    op.add_column('attempts', sa.Column('step_check', postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column('attempts', 'step_check')
    op.drop_column('attempts', 'work_text')