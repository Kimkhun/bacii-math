"""sync api_usage_logs + study_sessions with models.py

`ApiUsageLog` gained prompt/completion cost and prompt/response text columns
without a migration, so every usage-log INSERT failed against a migrated
database (UndefinedColumnError) and /admin/costs never saw any data.
`StudySession.created_at/updated_at` are NOT NULL in the model but were
created nullable.

Revision ID: a1b2c3d4e5f6
Revises: f4e5d6c7b8a9
Create Date: 2026-09-24 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'a1b2c3d4e5f6'
down_revision = 'f4e5d6c7b8a9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('api_usage_logs', sa.Column('prompt_cost_usd', sa.Float(), nullable=False, server_default='0'))
    op.add_column('api_usage_logs', sa.Column('completion_cost_usd', sa.Float(), nullable=False, server_default='0'))
    op.add_column('api_usage_logs', sa.Column('prompt_text', sa.Text(), nullable=True))
    op.add_column('api_usage_logs', sa.Column('response_text', sa.Text(), nullable=True))

    for col in ('created_at', 'updated_at'):
        op.execute(f"UPDATE study_sessions SET {col} = now() WHERE {col} IS NULL")
        op.alter_column(
            'study_sessions', col,
            existing_type=sa.DateTime(timezone=True),
            existing_server_default=sa.func.now(),
            nullable=False,
        )


def downgrade() -> None:
    for col in ('updated_at', 'created_at'):
        op.alter_column(
            'study_sessions', col,
            existing_type=sa.DateTime(timezone=True),
            existing_server_default=sa.func.now(),
            nullable=True,
        )
    op.drop_column('api_usage_logs', 'response_text')
    op.drop_column('api_usage_logs', 'prompt_text')
    op.drop_column('api_usage_logs', 'completion_cost_usd')
    op.drop_column('api_usage_logs', 'prompt_cost_usd')
