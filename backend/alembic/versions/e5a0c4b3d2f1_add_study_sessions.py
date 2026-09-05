"""add study sessions (save progress)

Revision ID: e5a0c4b3d2f1
Revises: f2a3b4c5d6e7
Create Date: 2026-08-25 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = 'e5a0c4b3d2f1'
down_revision = 'f2a3b4c5d6e7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'study_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            'user_id', postgresql.UUID(as_uuid=True),
            sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False,
        ),
        sa.Column(
            'question_id', postgresql.UUID(as_uuid=True),
            sa.ForeignKey('questions.id', ondelete='CASCADE'), nullable=False,
        ),
        sa.Column('status', sa.String(length=20), server_default='in_progress', nullable=False),
        sa.Column('state', postgresql.JSONB(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint('user_id', 'question_id', name='uq_study_session_user_question'),
    )
    op.create_index('ix_study_sessions_user_id', 'study_sessions', ['user_id'])
    op.create_index('ix_study_sessions_question_id', 'study_sessions', ['question_id'])


def downgrade() -> None:
    op.drop_index('ix_study_sessions_question_id', table_name='study_sessions')
    op.drop_index('ix_study_sessions_user_id', table_name='study_sessions')
    op.drop_table('study_sessions')