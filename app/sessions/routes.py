from uuid import UUID

import io
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, WebSocket, status
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Answer, Question
from app.db.session import get_db_session
from app.schemas.sessions import (
    AnswerRead,
    NextQuestionResponse,
    SessionCreate,
    SessionRead,
)
from app.schemas.questions import QuestionRead
from app.sessions import service
from app.questions import service as questions_service

router = APIRouter()

@router.get("", response_model=list[SessionRead])
async def list_sessions(
    user_id: UUID | None = None,
    db: AsyncSession = Depends(get_db_session)
):
    if user_id:
        return await service.list_user_sessions(db, user_id)
    return []

@router.post("", response_model=SessionRead, status_code=status.HTTP_201_CREATED)
async def start_session(
    session_in: SessionCreate,
    db: AsyncSession = Depends(get_db_session),
):
    return await service.start_session(db, session_in.user_id, session_in.interview_id)

@router.get("/{session_id}", response_model=SessionRead)
async def get_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db_session),
):
    session = await service.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

@router.post("/{session_id}/end", response_model=SessionRead)
async def end_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db_session),
):
    session = await service.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.ended_at is not None:
        raise HTTPException(status_code=409, detail="Session already ended")
    return await service.end_session(db, session)

@router.get("/{session_id}/next-question", response_model=NextQuestionResponse)
async def next_question(
    session_id: UUID,
    tts: bool = False,
    db: AsyncSession = Depends(get_db_session),
):
    session = await service.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.ended_at is not None:
        raise HTTPException(status_code=409, detail="Session already ended")

    question = await questions_service.get_next_question(db, session)

    if tts:
        if not question:
            raise HTTPException(status_code=404, detail="No more questions")
        from app.ai.tts import speak
        audio = await speak(question.text)
        return StreamingResponse(io.BytesIO(audio), media_type="audio/mpeg")

    return NextQuestionResponse(
        question=QuestionRead.model_validate(question) if question else None,
        completed=question is None,
    )

@router.post(
    "/{session_id}/answers",
    response_model=AnswerRead,
    status_code=status.HTTP_201_CREATED,
)
async def submit_answer(
    session_id: UUID,
    question_id: UUID = Form(...),
    text: str | None = Form(None),
    audio: UploadFile | None = File(None),
    db: AsyncSession = Depends(get_db_session),
):
    if not text and not audio:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either text or audio must be provided.",
        )

    session = await service.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.ended_at is not None:
        raise HTTPException(status_code=409, detail="Session already ended")

    q_result = await db.execute(
        select(Question).where(
            Question.id == question_id,
            Question.interview_id == session.interview_id,
        )
    )
    question = q_result.scalar_one_or_none()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found in this interview")

    dup_result = await db.execute(
        select(Answer).where(
            Answer.session_id == session_id,
            Answer.question_id == question_id,
        )
    )
    if dup_result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Question already answered in this session")

    if audio:
        from app.ai.transcriber import transcribe_audio
        audio_bytes = await audio.read()
        text = await transcribe_audio(audio_bytes, audio.filename or "audio")

    answer = await service.create_answer(db, session_id, question_id, text)
    if session and question:
        await service.evaluate_and_maybe_followup(
            db=db,
            session=session,
            question=question,
            answer_id=answer.id,
            answer_text=text,
        )
    return answer

@router.get("/{session_id}/answers", response_model=list[AnswerRead])
async def list_answers(
    session_id: UUID,
    db: AsyncSession = Depends(get_db_session),
):
    session = await service.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return await service.list_answers(db, session_id)

@router.post("/transcribe", response_model=dict)
async def transcribe_audio_endpoint(
    audio: UploadFile = File(...),
):
    """
    Standalone endpoint to transcribe audio without persisting an answer.
    """
    from app.ai.transcriber import transcribe_audio
    audio_bytes = await audio.read()
    text = await transcribe_audio(audio_bytes, audio.filename or "audio")
    return {"text": text}
