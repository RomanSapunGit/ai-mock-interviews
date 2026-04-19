import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession as DbSession

from app.db.models import Answer, Interview, Question, Session

logger = logging.getLogger(__name__)

async def start_session(db: DbSession, user_id: UUID, interview_id: UUID) -> Session:
    session = Session(
        user_id=user_id,
        interview_id=interview_id,
        started_at=datetime.now(timezone.utc),
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session

async def get_session(db: DbSession, session_id: UUID) -> Session | None:
    result = await db.execute(select(Session).where(Session.id == session_id))
    return result.scalar_one_or_none()

async def list_user_sessions(db: DbSession, user_id: UUID) -> list[Session]:
    result = await db.execute(
        select(Session)
        .where(Session.user_id == user_id)
        .order_by(Session.created_at.desc())
    )
    return list(result.scalars().all())

async def end_session(db: DbSession, session: Session) -> Session:
    session.ended_at = datetime.now(timezone.utc)

    try:
        answers = await list_answers(db, session.id)
        if answers:
            from app.ai.evaluator import evaluate_session_overall
            interview = await db.get(Interview, session.interview_id)
            role = interview.role if interview else "software engineer"
            difficulty = interview.difficulty if interview else "medium"

            qa_pairs = []
            for ans in answers:
                question = await db.get(Question, ans.question_id)
                qa_pairs.append({
                    "question": question.text if question else "Unknown question",
                    "answer": ans.text or "No answer provided",
                    "score": ans.score or 0.0
                })

            score, feedback = await evaluate_session_overall(
                qa_pairs=qa_pairs,
                role=role,
                difficulty=difficulty
            )
            session.score = score
            session.feedback = feedback
    except Exception as e:
        logger.error(f"Failed to generate overall session feedback: {e}")

    if session.interview_id:
        from sqlalchemy import select
        from app.db.models import Question, Interview
        interview = await db.get(Interview, session.interview_id)
        if interview:
            unanswered_query = select(Question).where(
                Question.interview_id == session.interview_id,
                Question.status == 'active'
            )
            unanswered = (await db.execute(unanswered_query)).scalars().first()
            if not unanswered:
                interview.status = 'completed'

    await db.commit()
    await db.refresh(session)
    return session

async def _evaluate_and_store(
    answer_id: UUID,
    question_text: str,
    answer_text: str,
    role: str | None,
    difficulty: str | None,
    question_type: str = "behavioral",
    transcript: str | None = None,
    examples: str | None = None,
) -> tuple[float, str]:
    from app.ai.evaluator import evaluate_answer
    from app.db.session import async_session_factory

    score, feedback = await evaluate_answer(
        question=question_text,
        answer=answer_text,
        role=role,
        difficulty=difficulty,
        question_type=question_type,
        transcript=transcript,
        examples=examples,
    )
    async with async_session_factory() as db:
        answer = await db.get(Answer, answer_id)
        if answer:
            answer.score = score
            answer.ai_feedback = feedback
            await db.commit()
    return score, feedback

async def evaluate_and_maybe_followup(
    db: DbSession,
    session: Session,
    question: Question,
    answer_id: UUID,
    answer_text: str,
    transcript: str | None = None,
    examples: str | None = None,
) -> tuple[float, str, Question | None]:
    """
    Evaluate an answer and potentially generate a follow-up question.
    Returns (score, feedback, followup_question_or_none).
    """
    from app.ai.evaluator import generate_followup_question

    interview = await db.get(Interview, session.interview_id)
    role = interview.role if interview else None
    difficulty = question.difficulty or (interview.difficulty if interview else None)

    score, feedback = await _evaluate_and_store(
        answer_id=answer_id,
        question_text=question.text,
        answer_text=answer_text,
        role=role,
        difficulty=difficulty,
        question_type=question.question_type,
        transcript=transcript,
        examples=examples,
    )

    followup_q = None
    if score >= 7.5:
        followup_text = await generate_followup_question(
            question=question.text,
            answer=answer_text,
            role=role,
            difficulty=difficulty,
        )

        followup_q = Question(
            interview_id=session.interview_id,
            text=followup_text,
            category=question.category,
            difficulty=question.difficulty,
            order=question.order + 1,
        )
        db.add(followup_q)
        await db.commit()
        await db.refresh(followup_q)

    return score, feedback, followup_q

async def create_answer(
    db: DbSession,
    session_id: UUID,
    question_id: UUID,
    text: str | None = None,
    code: str | None = None,
    language: str | None = None,
) -> Answer:
    answer = Answer(
        session_id=session_id,
        question_id=question_id,
        text=text,
        code=code,
        language=language
    )
    db.add(answer)
    await db.commit()
    await db.refresh(answer)

    question = await db.get(Question, question_id)
    if question:
        question.status = "completed"
        await db.commit()
    return answer

async def list_answers(db: DbSession, session_id: UUID) -> list[Answer]:
    result = await db.execute(
        select(Answer)
        .where(Answer.session_id == session_id)
        .order_by(Answer.created_at)
    )
    return list(result.scalars().all())
