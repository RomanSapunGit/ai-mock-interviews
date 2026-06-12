"""Reset vector store for Gemini embeddings

Embeddings moved from the local 384-dim all-MiniLM-L6-v2 model to Google's
768-dim gemini-embedding-001. Vectors from the two models live in different
spaces, so the langchain-managed tables are dropped; PGVector recreates
them on first use and source material can simply be re-uploaded.

Revision ID: f7c2d9e8b3a1
Revises: e4d8b7a2c1f0
Create Date: 2026-06-13

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'f7c2d9e8b3a1'
down_revision: Union[str, Sequence[str], None] = 'e4d8b7a2c1f0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DROP TABLE IF EXISTS langchain_pg_embedding CASCADE")
    op.execute("DROP TABLE IF EXISTS langchain_pg_collection CASCADE")


def downgrade() -> None:
    # The tables are owned and recreated by langchain-postgres on demand;
    # the old 384-dim vectors are not recoverable.
    pass
