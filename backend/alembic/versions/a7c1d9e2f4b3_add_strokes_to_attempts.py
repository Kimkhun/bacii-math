"""add strokes to attempts

Revision ID: a7c1d9e2f4b3
Revises: e5a0c4b3d2f1
Create Date: 2026-08-26 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = 'a7c1d9e2f4b3'
down_revision = 'e5a0c4b3d2f1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('attempts', sa.Column('strokes', postgresql.JSONB(), nullable=True))
    op.add_column('attempts', sa.Column('strokes_thumb', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('attempts', 'strokes_thumb')
    op.drop_column('attempts', 'strokes')