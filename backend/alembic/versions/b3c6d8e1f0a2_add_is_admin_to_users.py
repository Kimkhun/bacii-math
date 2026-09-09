"""add is_admin to users

Revision ID: b3c6d8e1f0a2
Revises: 5eb5fb3ce7d3
Create Date: 2026-09-09 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b3c6d8e1f0a2'
down_revision = '5eb5fb3ce7d3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column('is_admin', sa.Boolean(), nullable=False, server_default='false'),
    )


def downgrade() -> None:
    op.drop_column('users', 'is_admin')
