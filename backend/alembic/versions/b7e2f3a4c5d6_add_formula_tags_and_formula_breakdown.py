"""add formula tags and formula_breakdown columns

Revision ID: b7e2f3a4c5d6
Revises: f3a1c9b7e2d4
Create Date: 2026-08-21 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = 'b7e2f3a4c5d6'
down_revision = 'f3a1c9b7e2d4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('questions', sa.Column('formula_tags', postgresql.JSONB(), nullable=True))
    op.add_column('steps', sa.Column('formula', sa.String(length=50), nullable=True))
    op.add_column('attempts', sa.Column('formula_breakdown', postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column('attempts', 'formula_breakdown')
    op.drop_column('steps', 'formula')
    op.drop_column('questions', 'formula_tags')
