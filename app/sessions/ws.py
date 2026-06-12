"""
WebSocket handler for a live interview session.

Protocol
--------
Connection: /sessions/{session_id}/ws?token=<JWT>  (token required; the
session must belong to the token's user).

Server → Client (JSON frames):
  {"type": "question",        "question_id": str, "text": str, "order": int, ...}
  {"type": "audio_chunk",     "data": str}          # base64-encoded MP3 chunk
  {"type": "audio_done"}
  {"type": "answer_received", "answer_id": str}
  {"type": "evaluation",      "answer_id": str, "score": float, "feedback": str}
  {"type": "hint",            "text": str}
  {"type": "evaluating_overall"}
  {"type": "session_complete", "interview_id": str}
  {"type": "error",           "detail": str}

Client → Server (JSON frames):
  {"type": "answer_text",        "question_id": str, "text": str}
  {"type": "answer_code",        "question_id": str, "text"?: str, "code"?: str, "language"?: str}
  {"type": "answer_audio_start", "question_id": str, "filename": str}
  {"type": "answer_audio_end",   "code"?: str, "language"?: str, "examples"?: str}
  {"type": "request_hint",       "question_id": str, ...}

Client → Server (binary frames):
  Raw audio bytes streamed between answer_audio_start / answer_audio_end.

All outbound frames go through a single queue drained by one sender task, so
concurrent producers (evaluation, TTS streaming, next-question) never write
to the socket simultaneously.
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.ai.evaluator import generate_hint
from app.ai.transcriber import transcribe_audio
from app.ai.tts import speak_stream
from app.auth.service import user_id_from_token
from app.db.models import Interview, Question
from app.db.session import async_session_factory
from app.questions import service as questions_service
from app.sessions import service

logger = logging.getLogger(__name__)


async def handle_session_ws(websocket: WebSocket, session_id: UUID) -> None:
    await websocket.accept()

    token = websocket.query_params.get("token")
    user_id = user_id_from_token(token) if token else None
    if user_id is None:
        await websocket.send_json({"type": "error", "detail": "Authentication required"})
        await websocket.close(code=1008)
        return

    async with async_session_factory() as db:
        session = await service.get_session(db, session_id)
        if not session or session.user_id != user_id:
            await websocket.send_json({"type": "error", "detail": "Session not found"})
            await websocket.close(code=1008)
            return
        if session.ended_at is not None:
            await websocket.send_json({"type": "error", "detail": "Session already ended"})
            await websocket.close(code=1008)
            return
        interview_id = session.interview_id

    out_queue: asyncio.Queue[dict] = asyncio.Queue()
    tasks: set[asyncio.Task] = set()

    async def send(frame: dict) -> None:
        await out_queue.put(frame)

    def _on_task_done(task: asyncio.Task) -> None:
        tasks.discard(task)
        if task.cancelled():
            return
        exc = task.exception()
        if exc is not None:
            logger.error("WS task failed for session %s", session_id, exc_info=exc)
            out_queue.put_nowait(
                {"type": "error", "detail": "Internal server error while processing your request"}
            )

    def spawn(coro) -> None:
        task = asyncio.create_task(coro)
        tasks.add(task)
        task.add_done_callback(_on_task_done)

    async def send_loop() -> None:
        while True:
            frame = await out_queue.get()
            await websocket.send_json(frame)

    async def receive_loop() -> None:
        audio_buf: list[bytes] = []
        audio_question_id: UUID | None = None
        audio_filename: str = "audio.webm"
        collecting_audio: bool = False

        while True:
            msg = await websocket.receive()

            if msg["type"] == "websocket.disconnect":
                return

            if msg.get("bytes") is not None:
                if collecting_audio:
                    audio_buf.append(msg["bytes"])
                continue

            if msg.get("text") is None:
                continue

            try:
                data = json.loads(msg["text"])
            except json.JSONDecodeError:
                await send({"type": "error", "detail": "Invalid JSON"})
                continue

            msg_type = data.get("type")

            try:
                if msg_type == "answer_text":
                    spawn(
                        _process_answer(
                            send,
                            session_id,
                            UUID(data["question_id"]),
                            text=data["text"],
                        )
                    )

                elif msg_type == "answer_code":
                    spawn(
                        _process_answer(
                            send,
                            session_id,
                            UUID(data["question_id"]),
                            text=data.get("text"),
                            code=data.get("code"),
                            language=data.get("language"),
                        )
                    )

                elif msg_type == "answer_audio_start":
                    audio_question_id = UUID(data["question_id"])
                    audio_filename = data.get("filename", "audio.webm")
                    audio_buf = []
                    collecting_audio = True

                elif msg_type == "answer_audio_end":
                    if not (collecting_audio and audio_question_id and audio_buf):
                        continue
                    collecting_audio = False
                    audio_bytes = b"".join(audio_buf)
                    audio_buf = []
                    qid = audio_question_id
                    audio_question_id = None

                    spawn(
                        _process_audio_answer(
                            send,
                            session_id,
                            qid,
                            audio_bytes,
                            audio_filename,
                            code=data.get("code"),
                            language=data.get("language"),
                            examples=data.get("examples"),
                        )
                    )

                elif msg_type == "request_hint":
                    spawn(
                        _handle_manual_hint(
                            send,
                            interview_id,
                            UUID(data["question_id"]),
                            code=data.get("code"),
                            language=data.get("language"),
                            transcript=data.get("transcript", ""),
                            examples=data.get("examples"),
                        )
                    )
            except (KeyError, ValueError):
                await send({"type": "error", "detail": "Malformed message"})

    send_task = asyncio.create_task(send_loop())
    recv_task = asyncio.create_task(receive_loop())
    spawn(_send_next_question(send, session_id))

    try:
        done, _ = await asyncio.wait(
            [recv_task, send_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in done:
            if not task.cancelled():
                exc = task.exception()
                if exc is not None and not isinstance(exc, WebSocketDisconnect):
                    raise exc
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("WebSocket error for session %s", session_id)
        try:
            await websocket.send_json({"type": "error", "detail": "Internal server error"})
        except Exception:
            pass
    finally:
        for task in (recv_task, send_task, *tasks):
            task.cancel()


async def _send_next_question(send, session_id: UUID) -> None:
    """Queue the next unanswered question (text + TTS audio), or finish the session."""
    async with async_session_factory() as db:
        session = await service.get_session(db, session_id)
        if not session:
            return
        interview_id = session.interview_id
        question = await questions_service.get_next_question(db, session)

        if question is None:
            total_questions = (
                await db.execute(
                    select(func.count())
                    .select_from(Question)
                    .where(Question.interview_id == interview_id)
                )
            ).scalar_one()
            interview = await db.get(Interview, interview_id)

    if question is None:
        # No questions at all: generation hasn't finished (or failed) — do
        # not end the session, or the interview would be marked completed
        # before it ever had questions.
        if total_questions == 0:
            if interview and interview.status == "failed":
                detail = "Question generation failed for this interview. Please regenerate the questions."
            else:
                detail = "Questions are still being generated. Please try again in a moment."
            await send({"type": "error", "detail": detail})
            return

        await send({"type": "evaluating_overall"})
        async with async_session_factory() as db:
            session = await service.get_session(db, session_id)
            if session and not session.ended_at:
                await service.end_session(db, session)
        await send({"type": "session_complete", "interview_id": str(interview_id)})
        return

    await _send_question_with_tts(send, question)


async def _send_question_with_tts(send, question: Question, is_followup: bool = False) -> None:
    frame = {
        "type": "question",
        "question_id": str(question.id),
        "text": question.text,
        "order": question.order,
        "question_type": question.question_type,
        "starter_code": question.starter_code,
        "examples": question.examples,
    }
    if is_followup:
        frame["is_followup"] = True
    await send(frame)

    try:
        async for chunk in speak_stream(question.text):
            await send({"type": "audio_chunk", "data": base64.b64encode(chunk).decode()})
    except Exception:
        logger.exception("TTS streaming failed for question %s", question.id)
    finally:
        await send({"type": "audio_done"})


async def _process_audio_answer(
    send,
    session_id: UUID,
    question_id: UUID,
    audio_bytes: bytes,
    filename: str,
    code: str | None,
    language: str | None,
    examples: str | None,
) -> None:
    try:
        transcript = await transcribe_audio(audio_bytes, filename)
    except Exception as exc:
        logger.exception("Transcription failed for session %s", session_id)
        await send({"type": "error", "detail": f"Transcription failed: {exc}"})
        return

    await _process_answer(
        send,
        session_id,
        question_id,
        text=transcript,
        code=code,
        language=language,
        examples=examples,
    )


async def _process_answer(
    send,
    session_id: UUID,
    question_id: UUID,
    text: str | None = None,
    code: str | None = None,
    language: str | None = None,
    examples: str | None = None,
) -> None:
    """Persist an answer, ACK the client, evaluate, send follow-up or next question."""
    async with async_session_factory() as db:
        session = await service.get_session(db, session_id)
        if not session:
            await send({"type": "error", "detail": "Session not found"})
            return

        q_result = await db.execute(
            select(Question).where(
                Question.id == question_id,
                Question.interview_id == session.interview_id,
            )
        )
        question = q_result.scalar_one_or_none()
        if not question:
            await send({"type": "error", "detail": "Question not found"})
            return

        try:
            answer = await service.create_answer(
                db, session_id, question_id, text=text, code=code, language=language
            )
        except IntegrityError:
            await send({"type": "error", "detail": "Question already answered"})
            return

        question_type = question.question_type
        answer_id = answer.id

    await send({"type": "answer_received", "answer_id": str(answer_id)})

    evaluation_answer = code if question_type == "coding" else (text or "")
    evaluation_transcript = text if question_type == "coding" else None

    followup_q = None
    try:
        async with async_session_factory() as db:
            session = await service.get_session(db, session_id)
            question = await db.get(Question, question_id)
            if session is None or question is None:
                return
            score, feedback, followup_q = await service.evaluate_and_maybe_followup(
                db=db,
                session=session,
                question=question,
                answer_id=answer_id,
                answer_text=evaluation_answer or "",
                transcript=evaluation_transcript,
                examples=examples,
            )
        await send(
            {"answer_id": str(answer_id), "score": score, "feedback": feedback, "type": "evaluation"}
        )
    except Exception:
        # The answer is saved; don't kill the interview because the LLM
        # returned garbage — tell the client and move on.
        logger.exception("Evaluation failed for answer %s", answer_id)
        await send(
            {"type": "error", "detail": "Evaluation failed for this answer; continuing with the next question."}
        )

    if followup_q is not None:
        await _send_question_with_tts(send, followup_q, is_followup=True)
    else:
        await _send_next_question(send, session_id)


async def _handle_manual_hint(
    send,
    interview_id: UUID,
    question_id: UUID,
    code: str | None = None,
    language: str | None = None,
    transcript: str | None = None,
    examples: str | None = None,
) -> None:
    """Generate and send a hint upon explicit user request."""
    async with async_session_factory() as db:
        q_result = await db.execute(
            select(Question).where(
                Question.id == question_id,
                Question.interview_id == interview_id,
            )
        )
        question = q_result.scalar_one_or_none()
        if not question:
            await send({"type": "error", "detail": "Question not found"})
            return
        question_text = question.text

    hint_text = await generate_hint(
        question=question_text,
        code=code or "",
        language=language or "python",
        transcript=transcript or "",
        examples=examples,
    )

    await send({"type": "hint", "text": hint_text})
