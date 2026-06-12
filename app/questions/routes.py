import os
import shutil
import tempfile
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.db.models import Interview, User
from app.db.session import get_db_session
from app.schemas.questions import QuestionDocument
from app.schemas.utils import MessageResponseSchema
from app.questions import service

router = APIRouter()

async def _require_owned_interview(
    db: AsyncSession, interview_id: UUID, current_user: User
) -> Interview:
    interview = await db.get(Interview, interview_id)
    if interview is None or interview.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Interview not found")
    return interview

async def _require_owned_chunk(
    db: AsyncSession, question_id: str, current_user: User
):
    doc = await service.get_question(question_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Question not found")
    try:
        interview_id = UUID(doc.metadata["interview_id"])
    except (KeyError, ValueError, TypeError):
        raise HTTPException(status_code=404, detail="Question not found")
    await _require_owned_interview(db, interview_id, current_user)
    return doc

@router.post("", response_model=MessageResponseSchema, status_code=status.HTTP_201_CREATED)
async def create_questions(
    interview_id: UUID = Form(...),
    text: str | None = Form(None),
    files: list[UploadFile] = File(default=[]),
    count: int = Form(5),
    topic: str | None = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Accepts optional text and/or multiple files, then fires indexing + LLM question
    generation as a background task. Returns immediately.
    """
    await _require_owned_interview(db, interview_id, current_user)

    file_paths: list[str] = []

    for file in files:
        suffix = os.path.splitext(file.filename)[1] if file.filename else ""
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(file.file, tmp)
            file_paths.append(tmp.name)

    service.schedule_generation(
        interview_id=interview_id,
        count=count,
        topic=topic,
        text_content=text,
        file_paths=file_paths,
    )

    return MessageResponseSchema(message="Indexing and question generation started in the background.")

@router.get("/{question_id}", response_model=QuestionDocument)
async def get_question(
    question_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    doc = await _require_owned_chunk(db, question_id, current_user)
    return QuestionDocument(
        page_content=doc.page_content,
        metadata=doc.metadata,
        id=question_id,
    )

@router.delete("/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_question(
    question_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    await _require_owned_chunk(db, question_id, current_user)
    success = await service.delete_question(question_id)
    if not success:
        raise HTTPException(status_code=404, detail="Question not found")
    return None
