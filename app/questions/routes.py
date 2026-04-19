import os
import shutil
import tempfile
from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.schemas.questions import QuestionDocument
from app.schemas.utils import MessageResponseSchema
from app.questions import service

router = APIRouter()

@router.post("", response_model=MessageResponseSchema, status_code=status.HTTP_201_CREATED)
async def create_questions(
    interview_id: UUID = Form(...),
    text: str | None = Form(None),
    files: list[UploadFile] = File(default=[]),
    count: int = Form(5),
    topic: str | None = Form(None),
):
    """
    Accepts optional text and/or multiple files, then fires indexing + LLM question
    generation as a background task. Returns immediately.
    """
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
async def get_question(question_id: str):
    doc = await service.get_question(question_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Question not found")
    return QuestionDocument(
        page_content=doc.page_content,
        metadata=doc.metadata,
        id=question_id,
    )

@router.delete("/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_question(question_id: str):
    success = await service.delete_question(question_id)
    if not success:
        raise HTTPException(status_code=404, detail="Question not found")
    return None
