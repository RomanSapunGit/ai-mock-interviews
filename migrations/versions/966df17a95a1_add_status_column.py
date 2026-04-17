"""Add status column

Revision ID: 966df17a95a1
Revises: b3f2a1c4d5e6
Create Date: 2026-04-13 19:07:35.847819

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '966df17a95a1'
down_revision: Union[str, Sequence[str], None] = 'b3f2a1c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Remove the drop_table and drop_index calls for langchain_pg tables
    op.add_column('questions', sa.Column('status', sa.String(length=50), nullable=False, server_default='active'))

def downgrade() -> None:
    # Remove the create_table and create_index calls for langchain_pg tables
    op.drop_column('questions', 'status')
