"""add lines_boxes to attempts

Revision ID: f2a3b4c5d6e7
Revises: e0a1b2c3d4e5
Create Date: 2026-08-22 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = 'f2a3b4c5d6e7'
down_revision = 'e0a1b2c3d4e5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('attempts', sa.Column('lines_boxes', postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column('attempts', 'lines_boxes')