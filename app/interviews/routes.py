from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user, get_owned_interview
from app.db.models import Interview, User
from app.db.session import get_db_session
from app.schemas.interviews import InterviewCreate, InterviewRead, InterviewUpdate
from app.schemas.questions import QuestionRead
from app.interviews import service
from app.questions import service as questions_service

router = APIRouter()

@router.post("", response_model=InterviewRead, status_code=status.HTTP_201_CREATED)
async def create_interview(
    interview_in: InterviewCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    # The owner always comes from the token, never from the request body.
    interview_in.user_id = current_user.id
    return await service.create_interview(db, interview_in)

@router.get("/{interview_id}", response_model=InterviewRead)
async def get_interview(
    interview: Interview = Depends(get_owned_interview),
):
    return interview

@router.patch("/{interview_id}", response_model=InterviewRead)
async def update_interview(
    interview_in: InterviewUpdate,
    interview: Interview = Depends(get_owned_interview),
    db: AsyncSession = Depends(get_db_session)
):
    return await service.update_interview(db, interview, interview_in)

@router.delete("/{interview_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_interview(
    interview: Interview = Depends(get_owned_interview),
    db: AsyncSession = Depends(get_db_session)
):
    await service.delete_interview(db, interview.id)
    return None

@router.get("/{interview_id}/questions", response_model=list[QuestionRead])
async def list_interview_questions(
    interview: Interview = Depends(get_owned_interview),
    db: AsyncSession = Depends(get_db_session)
):
    return await questions_service.list_questions(db, interview.id)

@router.delete("/{interview_id}/questions/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_interview_question(
    question_id: UUID,
    interview: Interview = Depends(get_owned_interview),
    db: AsyncSession = Depends(get_db_session),
):
    deleted = await questions_service.delete_question_by_id(db, question_id, interview.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Question not found")
    return None

@router.post("/{interview_id}/reset-questions", status_code=status.HTTP_200_OK)
async def reset_interview_questions(
    interview: Interview = Depends(get_owned_interview),
    db: AsyncSession = Depends(get_db_session),
):
    await questions_service.reset_interview_questions(db, interview.id)
    return {"message": "All questions have been reset to active."}
