"""add prompt_latex to questions

Revision ID: f3a1c9b7e2d4
Revises: d9a97322172e
Create Date: 2026-08-15 07:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'f3a1c9b7e2d4'
down_revision = 'd9a97322172e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('questions', sa.Column('prompt_latex', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('questions', 'prompt_latex')
