from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.schemas.interviews import InterviewCreate, InterviewRead, InterviewUpdate
from app.schemas.questions import QuestionRead
from app.interviews import service
from app.questions import service as questions_service

router = APIRouter()

@router.post("", response_model=InterviewRead, status_code=status.HTTP_201_CREATED)
async def create_interview(
    interview_in: InterviewCreate,
    db: AsyncSession = Depends(get_db_session)
):
    return await service.create_interview(db, interview_in)

@router.get("/{interview_id}", response_model=InterviewRead)
async def get_interview(
    interview_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    db_interview = await service.get_interview(db, interview_id)
    if not db_interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    return db_interview

@router.patch("/{interview_id}", response_model=InterviewRead)
async def update_interview(
    interview_id: UUID,
    interview_in: InterviewUpdate,
    db: AsyncSession = Depends(get_db_session)
):
    db_interview = await service.get_interview(db, interview_id)
    if not db_interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    return await service.update_interview(db, db_interview, interview_in)

@router.delete("/{interview_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_interview(
    interview_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    success = await service.delete_interview(db, interview_id)
    if not success:
        raise HTTPException(status_code=404, detail="Interview not found")
    return None

@router.get("/{interview_id}/questions", response_model=list[QuestionRead])
async def list_interview_questions(
    interview_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    interview = await service.get_interview(db, interview_id)
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    return await questions_service.list_questions(db, interview_id)

@router.delete("/{interview_id}/questions/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_interview_question(
    interview_id: UUID,
    question_id: UUID,
    db: AsyncSession = Depends(get_db_session),
):
    interview = await service.get_interview(db, interview_id)
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Deleting question {question_id} for interview {interview_id}")

    deleted = await questions_service.delete_question_by_id(db, question_id, interview_id)
    if not deleted:
        logger.warning(f"Delete failed: question {question_id} not found or mismatch for interview {interview_id}")
        raise HTTPException(status_code=404, detail="Question not found")
    return None

@router.post("/{interview_id}/reset-questions", status_code=status.HTTP_200_OK)
async def reset_interview_questions(
    interview_id: UUID,
    db: AsyncSession = Depends(get_db_session),
):
    interview = await service.get_interview(db, interview_id)
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    await questions_service.reset_interview_questions(db, interview_id)
    return {"message": "All questions have been reset to active."}
