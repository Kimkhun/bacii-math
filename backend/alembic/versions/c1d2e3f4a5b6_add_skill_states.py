"""add skill_states (per-student skill mastery tracker)

Revision ID: c1d2e3f4a5b6
Revises: b3c6d8e1f0a2
Create Date: 2026-09-09 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c1d2e3f4a5b6'
down_revision = 'b3c6d8e1f0a2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'skill_states',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('kind', sa.String(length=20), server_default='exercise', nullable=False),
        sa.Column('skill_key', sa.String(length=120), nullable=False),
        sa.Column('topic', sa.String(length=50), nullable=True),
        sa.Column('w_total', sa.Float(), server_default='0', nullable=False),
        sa.Column('w_correct', sa.Float(), server_default='0', nullable=False),
        sa.Column('evidence', sa.Float(), server_default='0', nullable=False),
        sa.Column('attempts', sa.Integer(), server_default='0', nullable=False),
        sa.Column('correct', sa.Integer(), server_default='0', nullable=False),
        sa.Column('streak', sa.Integer(), server_default='0', nullable=False),
        sa.Column('best_streak', sa.Integer(), server_default='0', nullable=False),
        sa.Column('last_score', sa.Float(), nullable=True),
        sa.Column('tracker_version', sa.Integer(), server_default='1', nullable=False),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'kind', 'skill_key', name='uq_skill_state_user_kind_key'),
    )
    op.create_index(op.f('ix_skill_states_user_id'), 'skill_states', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_skill_states_user_id'), table_name='skill_states')
    op.drop_table('skill_states')
