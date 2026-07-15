import asyncio
import json
import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession as DbSession

from app.db.models import Answer, Clarification, Interview, Question, QuestionTiming, Session

logger = logging.getLogger(__name__)

# Keep references to fire-and-forget tasks so they are not garbage-collected
# mid-flight and their exceptions are logged by the done callback.
_background_tasks: set[asyncio.Task] = set()

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

async def record_question_served(db: DbSession, session_id: UUID, question_id: UUID) -> datetime:
    """Record when a question was first shown in a session (idempotent across reconnects)."""
    await db.execute(
        pg_insert(QuestionTiming)
        .values(session_id=session_id, question_id=question_id, served_at=datetime.now(timezone.utc))
        .on_conflict_do_nothing(constraint="uq_question_timings_session_question")
    )
    await db.commit()
    result = await db.execute(
        select(QuestionTiming.served_at).where(
            QuestionTiming.session_id == session_id,
            QuestionTiming.question_id == question_id,
        )
    )
    return result.scalar_one()

async def create_clarification(
    db: DbSession,
    session_id: UUID,
    question_id: UUID,
    asked_text: str,
    answer_text: str,
    resolved_points: list[int],
) -> Clarification:
    clarification = Clarification(
        session_id=session_id,
        question_id=question_id,
        asked_text=asked_text,
        answer_text=answer_text,
        resolved_points=json.dumps(resolved_points),
    )
    db.add(clarification)
    await db.commit()
    await db.refresh(clarification)
    return clarification

async def list_clarifications(
    db: DbSession, session_id: UUID, question_id: UUID | None = None
) -> list[Clarification]:
    stmt = select(Clarification).where(Clarification.session_id == session_id)
    if question_id is not None:
        stmt = stmt.where(Clarification.question_id == question_id)
    result = await db.execute(stmt.order_by(Clarification.created_at))
    return list(result.scalars().all())

def _format_probe_dialogue(probe_dialogue_json: str | None) -> str | None:
    if not probe_dialogue_json:
        return None
    try:
        exchanges = json.loads(probe_dialogue_json)
    except ValueError:
        return None
    lines = [
        f'Interviewer asked: "{e.get("question")}" — Candidate answered: "{e.get("answer")}"'
        for e in exchanges
        if isinstance(e, dict)
    ]
    return "\n".join(lines) or None

async def _coding_context(
    db: DbSession,
    session_id: UUID,
    question: Question,
    time_taken_seconds: int | None,
) -> dict[str, str | None]:
    """Build the clarification/timing context strings fed to the coding evaluators."""
    hidden_points: list[dict] = []
    if question.hidden_spec:
        try:
            hidden_points = [p for p in json.loads(question.hidden_spec) if isinstance(p, dict)]
        except ValueError:
            pass

    clarifications = await list_clarifications(db, session_id, question.id)
    resolved: set[int] = set()
    clar_lines = []
    for c in clarifications:
        points = json.loads(c.resolved_points) if c.resolved_points else []
        resolved.update(int(p) for p in points)
        suffix = f" (resolved spec points: {points})" if points else ""
        clar_lines.append(f'Asked: "{c.asked_text}" → Interviewer answered: "{c.answer_text}"{suffix}')

    missed = [f"[{i}] {p.get('point')}" for i, p in enumerate(hidden_points) if i not in resolved]
    if missed:
        clar_lines.append("MISSED (never asked about): " + "; ".join(missed))

    if question.time_limit_seconds and time_taken_seconds is not None:
        limit_min = round(question.time_limit_seconds / 60)
        taken_min = round(time_taken_seconds / 60)
        if time_taken_seconds > question.time_limit_seconds:
            over_min = max(1, round((time_taken_seconds - question.time_limit_seconds) / 60))
            time_summary = f"Time limit: {limit_min} min. Time used: {taken_min} min — {over_min} min OVER the limit."
        else:
            time_summary = f"Time limit: {limit_min} min. Time used: {taken_min} min — within the limit."
    else:
        time_summary = "No time data."

    return {
        "hidden_spec": question.hidden_spec or "None.",
        "clarifications": "\n".join(clar_lines) if clar_lines else "The candidate asked no clarifying questions.",
        "missed_points": "; ".join(missed) if missed else None,
        "time_summary": time_summary,
    }

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
                pair = {
                    "question": question.text if question else "Unknown question",
                    "answer": ans.text or ans.code or "No answer provided",
                    "score": ans.score or 0.0
                }
                if question is not None and question.question_type == "coding":
                    context = await _coding_context(db, session.id, question, ans.time_taken_seconds)
                    pair["clarifications"] = context["clarifications"]
                    pair["missed_points"] = context["missed_points"]
                    pair["time_summary"] = context["time_summary"]
                    pair["probe_dialogue"] = _format_probe_dialogue(ans.probe_dialogue)
                qa_pairs.append(pair)

            score, feedback = await evaluate_session_overall(
                qa_pairs=qa_pairs,
                role=role,
                difficulty=difficulty
            )
            session.score = score
            session.feedback = feedback
    except Exception:
        logger.exception("Failed to generate overall session feedback")

    interview = await db.get(Interview, session.interview_id)
    if interview:
        total_questions = (
            await db.execute(
                select(func.count())
                .select_from(Question)
                .where(Question.interview_id == session.interview_id)
            )
        ).scalar_one()
        unanswered = (
            await db.execute(
                select(Question.id).where(
                    Question.interview_id == session.interview_id,
                    Question.status == "active",
                ).limit(1)
            )
        ).scalar_one_or_none()
        # Never flag an interview as completed while it has no questions yet
        # (e.g. generation still running in the background).
        if total_questions > 0 and unanswered is None:
            interview.status = "completed"

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
    hidden_spec: str | None = None,
    clarifications: str | None = None,
    time_summary: str | None = None,
    probe_dialogue: str | None = None,
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
        hidden_spec=hidden_spec,
        clarifications=clarifications,
        time_summary=time_summary,
        probe_dialogue=probe_dialogue,
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
    Raises when the evaluation itself fails; follow-up generation failures
    are logged and swallowed (the evaluation result is still returned).
    """
    from app.ai.evaluator import generate_followup_question

    interview = await db.get(Interview, session.interview_id)
    role = interview.role if interview else None
    difficulty = question.difficulty or (interview.difficulty if interview else None)

    coding_context: dict[str, str | None] = {}
    probe_dialogue = None
    if question.question_type == "coding":
        answer = await db.get(Answer, answer_id)
        coding_context = await _coding_context(
            db, session.id, question, answer.time_taken_seconds if answer else None
        )
        probe_dialogue = _format_probe_dialogue(answer.probe_dialogue if answer else None)

    score, feedback = await _evaluate_and_store(
        answer_id=answer_id,
        question_text=question.text,
        answer_text=answer_text,
        role=role,
        difficulty=difficulty,
        question_type=question.question_type,
        transcript=transcript,
        examples=examples,
        hidden_spec=coding_context.get("hidden_spec"),
        clarifications=coding_context.get("clarifications"),
        time_summary=coding_context.get("time_summary"),
        probe_dialogue=probe_dialogue,
    )

    followup_q = None
    # Only first-level questions spawn follow-ups, so a strong candidate
    # cannot trigger an endless chain of generated questions.
    if score >= 7.5 and question.parent_question_id is None:
        followup_text = None
        try:
            followup_text = await generate_followup_question(
                question=question.text,
                answer=answer_text,
                role=role,
                difficulty=difficulty,
            )
        except Exception:
            logger.exception("Follow-up generation failed for question %s", question.id)

        if followup_text:
            max_order = (
                await db.execute(
                    select(func.coalesce(func.max(Question.order), 0)).where(
                        Question.interview_id == session.interview_id
                    )
                )
            ).scalar_one()
            followup_q = Question(
                interview_id=session.interview_id,
                text=followup_text,
                category=question.category,
                difficulty=question.difficulty,
                question_type=question.question_type,
                parent_question_id=question.id,
                order=max_order + 1,
            )
            db.add(followup_q)
            await db.commit()
            await db.refresh(followup_q)

    return score, feedback, followup_q

def schedule_evaluation(
    session_id: UUID,
    question_id: UUID,
    answer_id: UUID,
    answer_text: str,
    transcript: str | None = None,
    examples: str | None = None,
) -> None:
    """Fire-and-forget evaluation for the REST answer flow."""
    task = asyncio.create_task(
        _evaluate_in_background(
            session_id, question_id, answer_id, answer_text, transcript, examples
        )
    )
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)

async def _evaluate_in_background(
    session_id: UUID,
    question_id: UUID,
    answer_id: UUID,
    answer_text: str,
    transcript: str | None,
    examples: str | None,
) -> None:
    from app.db.session import async_session_factory

    try:
        async with async_session_factory() as db:
            session = await db.get(Session, session_id)
            question = await db.get(Question, question_id)
            if session and question:
                await evaluate_and_maybe_followup(
                    db=db,
                    session=session,
                    question=question,
                    answer_id=answer_id,
                    answer_text=answer_text,
                    transcript=transcript,
                    examples=examples,
                )
    except Exception:
        logger.exception("Background evaluation failed for answer %s", answer_id)

async def create_answer(
    db: DbSession,
    session_id: UUID,
    question_id: UUID,
    text: str | None = None,
    code: str | None = None,
    language: str | None = None,
) -> Answer:
    """Persist an answer.

    Raises sqlalchemy.exc.IntegrityError when the question was already
    answered in this session (unique constraint on session_id+question_id);
    callers translate that into their protocol-specific error.
    """
    answer = Answer(
        session_id=session_id,
        question_id=question_id,
        text=text,
        code=code,
        language=language
    )
    served_at = (
        await db.execute(
            select(QuestionTiming.served_at).where(
                QuestionTiming.session_id == session_id,
                QuestionTiming.question_id == question_id,
            )
        )
    ).scalar_one_or_none()
    if served_at is not None:
        answer.time_taken_seconds = int((datetime.now(timezone.utc) - served_at).total_seconds())
    db.add(answer)
    question = await db.get(Question, question_id)
    if question:
        # Display state only ("answered at least once"); session progress is
        # tracked by Answer rows, not by this flag.
        question.status = "completed"
    await db.commit()
    await db.refresh(answer)
    return answer

async def list_answers(db: DbSession, session_id: UUID) -> list[Answer]:
    result = await db.execute(
        select(Answer)
        .options(selectinload(Answer.question))
        .where(Answer.session_id == session_id)
        .order_by(Answer.created_at)
    )
    return list(result.scalars().all())
