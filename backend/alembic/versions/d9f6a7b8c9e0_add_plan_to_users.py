"""add plan column to users

Revision ID: d9f6a7b8c9e0
Revises: c8f4a5b6d7e8
Create Date: 2026-08-22 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'd9f6a7b8c9e0'
down_revision = 'c8f4a5b6d7e8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column('plan', sa.String(length=20), nullable=False, server_default='free'),
    )


def downgrade() -> None:
    op.drop_column('users', 'plan')