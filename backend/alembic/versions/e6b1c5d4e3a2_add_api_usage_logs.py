"""add api_usage_logs for cost tracking and observability

Revision ID: e6b1c5d4e3a2
Revises: e5a0c4b3d2f1
Create Date: 2026-09-12 02:40:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = 'e6b1c5d4e3a2'
down_revision = 'e5a0c4b3d2f1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'api_usage_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            'user_id', postgresql.UUID(as_uuid=True),
            sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True,
        ),
        sa.Column('endpoint', sa.String(length=50), nullable=False),
        sa.Column('provider', sa.String(length=30), nullable=False),
        sa.Column('model_name', sa.String(length=50), nullable=False),
        sa.Column('prompt_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('completion_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('estimated_cost_usd', sa.Float(), nullable=False, server_default='0'),
        sa.Column('latency_ms', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('success', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_api_usage_logs_user_id', 'api_usage_logs', ['user_id'])
    op.create_index('ix_api_usage_logs_endpoint', 'api_usage_logs', ['endpoint'])
    op.create_index('ix_api_usage_logs_created_at', 'api_usage_logs', ['created_at'])


def downgrade() -> None:
    op.drop_index('ix_api_usage_logs_created_at', table_name='api_usage_logs')
    op.drop_index('ix_api_usage_logs_endpoint', table_name='api_usage_logs')
    op.drop_index('ix_api_usage_logs_user_id', table_name='api_usage_logs')
    op.drop_table('api_usage_logs')
