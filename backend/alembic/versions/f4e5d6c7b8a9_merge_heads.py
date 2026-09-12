"""merge heads

Revision ID: f4e5d6c7b8a9
Revises: e6b1c5d4e3a2, c1d2e3f4a5b6
Create Date: 2026-09-12 15:15:00.000000

"""
from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = 'f4e5d6c7b8a9'
down_revision: Union[str, Sequence[str], None] = ('e6b1c5d4e3a2', 'c1d2e3f4a5b6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
