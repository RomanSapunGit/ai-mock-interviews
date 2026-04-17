"""drop_embedding_columns

Revision ID: b3f2a1c4d5e6
Revises: 8a9641cee57e
Create Date: 2026-04-12 00:00:00.000000

Embeddings are owned by LangChain's PGVector tables (langchain_pg_embedding).
The embedding columns on questions and answers were never populated and are
redundant with that storage. Drop them.
"""
from typing import Sequence, Union

import pgvector
import sqlalchemy as sa
from alembic import op


revision: str = 'b3f2a1c4d5e6'
down_revision: Union[str, Sequence[str], None] = '8a9641cee57e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column('questions', 'embedding')
    op.drop_column('answers', 'embedding')


def downgrade() -> None:
    op.add_column('answers', sa.Column(
        'embedding',
        pgvector.sqlalchemy.vector.VECTOR(dim=384),
        nullable=True,
    ))
    op.add_column('questions', sa.Column(
        'embedding',
        pgvector.sqlalchemy.vector.VECTOR(dim=384),
        nullable=True,
    ))
