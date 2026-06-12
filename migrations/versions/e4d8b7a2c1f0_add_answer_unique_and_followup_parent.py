"""Add unique answer constraint and follow-up parent column

Revision ID: e4d8b7a2c1f0
Revises: c7f12a3e98b0
Create Date: 2026-06-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e4d8b7a2c1f0'
down_revision: Union[str, Sequence[str], None] = 'c7f12a3e98b0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Remove duplicate answers (keep the earliest per session/question)
    # before the unique constraint can be created.
    op.execute(
        """
        DELETE FROM answers
        WHERE id NOT IN (
            SELECT DISTINCT ON (session_id, question_id) id
            FROM answers
            ORDER BY session_id, question_id, created_at
        )
        """
    )
    op.create_unique_constraint(
        "uq_answers_session_question", "answers", ["session_id", "question_id"]
    )

    op.add_column(
        "questions",
        sa.Column("parent_question_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_questions_parent_question_id",
        "questions",
        "questions",
        ["parent_question_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_questions_parent_question_id", "questions", type_="foreignkey")
    op.drop_column("questions", "parent_question_id")
    op.drop_constraint("uq_answers_session_question", "answers", type_="unique")
