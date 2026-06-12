from uuid import UUID

import io
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user, get_owned_session
from app.db.models import Interview, Question, Session, User
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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    return await service.list_user_sessions(db, current_user.id)

@router.post("", response_model=SessionRead, status_code=status.HTTP_201_CREATED)
async def start_session(
    session_in: SessionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    interview = await db.get(Interview, session_in.interview_id)
    if interview is None or interview.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Interview not found")
    return await service.start_session(db, current_user.id, session_in.interview_id)

@router.get("/{session_id}", response_model=SessionRead)
async def get_session(
    session: Session = Depends(get_owned_session),
):
    return session

@router.post("/{session_id}/end", response_model=SessionRead)
async def end_session(
    session: Session = Depends(get_owned_session),
    db: AsyncSession = Depends(get_db_session),
):
    if session.ended_at is not None:
        raise HTTPException(status_code=409, detail="Session already ended")
    return await service.end_session(db, session)

@router.get("/{session_id}/next-question", response_model=NextQuestionResponse)
async def next_question(
    tts: bool = False,
    session: Session = Depends(get_owned_session),
    db: AsyncSession = Depends(get_db_session),
):
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
    question_id: UUID = Form(...),
    text: str | None = Form(None),
    code: str | None = Form(None),
    language: str | None = Form(None),
    audio: UploadFile | None = File(None),
    session: Session = Depends(get_owned_session),
    db: AsyncSession = Depends(get_db_session),
):
    if not text and not code and not audio:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either text, code or audio must be provided.",
        )
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

    if audio:
        from app.ai.transcriber import transcribe_audio
        audio_bytes = await audio.read()
        text = await transcribe_audio(audio_bytes, audio.filename or "audio")

    try:
        answer = await service.create_answer(
            db, session.id, question_id, text=text, code=code, language=language
        )
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Question already answered in this session")

    evaluation_answer = code if question.question_type == "coding" else (text or "")
    evaluation_transcript = text if question.question_type == "coding" else None
    service.schedule_evaluation(
        session_id=session.id,
        question_id=question_id,
        answer_id=answer.id,
        answer_text=evaluation_answer or "",
        transcript=evaluation_transcript,
    )
    return answer

@router.get("/{session_id}/answers", response_model=list[AnswerRead])
async def list_answers(
    session: Session = Depends(get_owned_session),
    db: AsyncSession = Depends(get_db_session),
):
    return await service.list_answers(db, session.id)

@router.post("/transcribe", response_model=dict)
async def transcribe_audio_endpoint(
    audio: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """
    Standalone endpoint to transcribe audio without persisting an answer.
    """
    from app.ai.transcriber import transcribe_audio
    audio_bytes = await audio.read()
    text = await transcribe_audio(audio_bytes, audio.filename or "audio")
    return {"text": text}
