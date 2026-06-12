"""Backfill user_id into vector chunk metadata

Chunks were tagged only with interview_id; cross-interview reuse of
uploaded material needs them scoped to their owner. New chunks get
user_id at indexing time; this backfills existing ones via the owning
interview.

Revision ID: a9b8c7d6e5f4
Revises: f7c2d9e8b3a1
Create Date: 2026-06-13

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a9b8c7d6e5f4'
down_revision: Union[str, Sequence[str], None] = 'f7c2d9e8b3a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # The langchain tables are created lazily by PGVector and may not exist.
    op.execute(
        """
        DO $$
        BEGIN
            IF to_regclass('langchain_pg_embedding') IS NOT NULL THEN
                UPDATE langchain_pg_embedding e
                SET cmetadata = jsonb_set(e.cmetadata, '{user_id}', to_jsonb(i.user_id::text))
                FROM interviews i
                WHERE e.cmetadata ? 'interview_id'
                  AND NOT (e.cmetadata ? 'user_id')
                  AND (e.cmetadata->>'interview_id') ~ '^[0-9a-fA-F-]{36}$'
                  AND i.id = (e.cmetadata->>'interview_id')::uuid;
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF to_regclass('langchain_pg_embedding') IS NOT NULL THEN
                UPDATE langchain_pg_embedding
                SET cmetadata = cmetadata - 'user_id'
                WHERE cmetadata ? 'user_id';
            END IF;
        END $$;
        """
    )
