"""Add hidden spec, timing, probe dialogue and clarifications

Revision ID: b1d4e7f2a9c3
Revises: a9b8c7d6e5f4
Create Date: 2026-07-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b1d4e7f2a9c3'
down_revision: Union[str, Sequence[str], None] = 'a9b8c7d6e5f4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('questions', sa.Column('hidden_spec', sa.Text(), nullable=True))
    op.add_column('questions', sa.Column('time_limit_seconds', sa.Integer(), nullable=True))
    op.add_column('answers', sa.Column('time_taken_seconds', sa.Integer(), nullable=True))
    op.add_column('answers', sa.Column('probe_dialogue', sa.Text(), nullable=True))

    op.create_table(
        'clarifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('question_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('asked_text', sa.Text(), nullable=False),
        sa.Column('answer_text', sa.Text(), nullable=False),
        sa.Column('resolved_points', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['question_id'], ['questions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_clarifications_session_id'), 'clarifications', ['session_id'])
    op.create_index(op.f('ix_clarifications_question_id'), 'clarifications', ['question_id'])

    op.create_table(
        'question_timings',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('question_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('served_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['question_id'], ['questions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id', 'question_id', name='uq_question_timings_session_question'),
    )
    op.create_index(op.f('ix_question_timings_session_id'), 'question_timings', ['session_id'])
    op.create_index(op.f('ix_question_timings_question_id'), 'question_timings', ['question_id'])


def downgrade() -> None:
    op.drop_index(op.f('ix_question_timings_question_id'), table_name='question_timings')
    op.drop_index(op.f('ix_question_timings_session_id'), table_name='question_timings')
    op.drop_table('question_timings')
    op.drop_index(op.f('ix_clarifications_question_id'), table_name='clarifications')
    op.drop_index(op.f('ix_clarifications_session_id'), table_name='clarifications')
    op.drop_table('clarifications')
    op.drop_column('answers', 'probe_dialogue')
    op.drop_column('answers', 'time_taken_seconds')
    op.drop_column('questions', 'time_limit_seconds')
    op.drop_column('questions', 'hidden_spec')
