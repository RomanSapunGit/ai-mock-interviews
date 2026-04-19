from uuid import UUID
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Interview
from app.schemas.interviews import InterviewCreate, InterviewUpdate
from app.questions.service import delete_all_interview_questions

async def create_interview(db: AsyncSession, interview_in: InterviewCreate) -> Interview:
    db_interview = Interview(**interview_in.model_dump())
    db.add(db_interview)
    await db.commit()
    await db.refresh(db_interview)
    return db_interview

async def get_interview(db: AsyncSession, interview_id: UUID) -> Interview | None:
    result = await db.execute(select(Interview).where(Interview.id == interview_id))
    return result.scalar_one_or_none()

async def list_user_interviews(db: AsyncSession, user_id: UUID) -> list[Interview]:
    result = await db.execute(
        select(Interview).where(Interview.user_id == user_id).order_by(Interview.created_at.desc())
    )
    interviews = list(result.scalars().all())

    from app.db.models import Question
    for interview in interviews:
        if interview.status != 'completed':
            q_res = await db.execute(select(Question).where(Question.interview_id == interview.id, Question.status == 'active'))
            if not q_res.scalars().first():
                q_all_res = await db.execute(select(Question.id).where(Question.interview_id == interview.id))
                if q_all_res.scalars().first():
                    interview.status = 'completed'
                    db.add(interview)

    await db.commit()
    return interviews

async def update_interview(
    db: AsyncSession, db_interview: Interview, interview_in: InterviewUpdate
) -> Interview:
    update_data = interview_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_interview, key, value)

    await db.commit()
    await db.refresh(db_interview)
    return db_interview

async def delete_interview(db: AsyncSession, interview_id: UUID) -> bool:
    await delete_all_interview_questions(db, interview_id)

    result = await db.execute(delete(Interview).where(Interview.id == interview_id))
    await db.commit()
    return result.rowcount > 0
