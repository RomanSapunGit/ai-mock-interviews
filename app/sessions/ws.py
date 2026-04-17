"""
WebSocket handler for a live interview session.

Protocol
--------
Server → Client (JSON frames):
  {"type": "question",        "question_id": str, "text": str, "order": int}
  {"type": "audio_chunk",     "data": str}          # base64-encoded MP3 chunk
  {"type": "audio_done"}
  {"type": "answer_received", "answer_id": str}
  {"type": "evaluation",      "answer_id": str, "score": float, "feedback": str}
  {"type": "session_complete"}
  {"type": "error",           "detail": str}

Client → Server (JSON frames):
  {"type": "answer_text",        "question_id": str, "text": str}
  {"type": "answer_audio_start", "question_id": str, "filename": str}
  {"type": "answer_audio_end"}

Client → Server (binary frames):
  Raw audio bytes streamed between answer_audio_start / answer_audio_end.
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.ai.evaluator import evaluate_answer, generate_followup_question
from app.ai.transcriber import transcribe_audio
from app.ai.tts import speak_stream
from app.db.models import Answer, Interview, Question
from app.db.session import async_session_factory
from app.questions import service as questions_service
from app.sessions import service

logger = logging.getLogger(__name__)


async def handle_session_ws(websocket: WebSocket, session_id: UUID) -> None:
    await websocket.accept()

    # Validate session before entering the main loop.
    async with async_session_factory() as db:
        session = await service.get_session(db, session_id)
        if not session:
            await websocket.send_json({"type": "error", "detail": "Session not found"})
            await websocket.close(code=1008)
            return
        if session.ended_at is not None:
            await websocket.send_json({"type": "error", "detail": "Session already ended"})
            await websocket.close(code=1008)
            return

    # Queue through which background eval tasks push their results.
    eval_queue: asyncio.Queue[dict] = asyncio.Queue()

    # Audio collection state (mutated by receive_loop).
    audio_buf: list[bytes] = []
    audio_question_id: UUID | None = None
    audio_filename: str = "audio.webm"
    collecting_audio: bool = False

    # Send the first question right away.
    await _send_next_question(websocket, session_id)

    # ------------------------------------------------------------------ #
    # Two concurrent tasks:                                                 #
    #   receive_loop  – reads client messages, dispatches answer handling   #
    #   eval_push_loop – pushes AI evaluation results as they complete      #
    # ------------------------------------------------------------------ #

    async def receive_loop() -> None:
        nonlocal audio_buf, audio_question_id, audio_filename, collecting_audio

        while True:
            msg = await websocket.receive()

            if msg["type"] == "websocket.disconnect":
                return

            # Binary frame: accumulate audio chunks.
            if msg.get("bytes") is not None:
                if collecting_audio:
                    audio_buf.append(msg["bytes"])
                continue

            # Text frame: JSON control message.
            if msg.get("text") is None:
                continue

            try:
                data = json.loads(msg["text"])
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "detail": "Invalid JSON"})
                continue

            msg_type = data.get("type")

            if msg_type == "answer_text":
                question_id = UUID(data["question_id"])
                await _handle_answer(
                    websocket, session_id, question_id, data["text"], eval_queue
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
                try:
                    text = await transcribe_audio(audio_bytes, audio_filename)
                except Exception as exc:
                    await websocket.send_json(
                        {"type": "error", "detail": f"Transcription failed: {exc}"}
                    )
                    continue
                await _handle_answer(websocket, session_id, qid, text, eval_queue)

    async def eval_push_loop() -> None:
        while True:
            result = await eval_queue.get()
            try:
                await websocket.send_json({"type": "evaluation", **result})
            except Exception:
                logger.info("Client disconnected before evaluation push")
                break

    recv_task = asyncio.create_task(receive_loop())
    eval_task = asyncio.create_task(eval_push_loop())

    try:
        done, pending = await asyncio.wait(
            [recv_task, eval_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
        # Propagate any unexpected exception.
        for task in done:
            if not task.cancelled():
                task.result()
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("WebSocket error for session %s", session_id)
        try:
            await websocket.send_json({"type": "error", "detail": "Internal server error"})
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _send_next_question(websocket: WebSocket, session_id: UUID) -> None:
    """Fetch the next unanswered question and stream it (text + TTS audio)."""
    async with async_session_factory() as db:
        session = await service.get_session(db, session_id)
        if not session:
            return
        question = await questions_service.get_next_question(db, session)

    if question is None:
        try:
            await websocket.send_json({"type": "evaluating_overall"})
        except Exception:
            pass
        async with async_session_factory() as db:
            session = await service.get_session(db, session_id)
            if session and not session.ended_at:
                await service.end_session(db, session)
        await websocket.send_json({"type": "session_complete", "interview_id": str(session.interview_id)})
        return

    try:
        await websocket.send_json(
            {
                "type": "question",
                "question_id": str(question.id),
                "text": question.text,
                "order": question.order,
            }
        )

        # Stream TTS audio chunks.
        try:
            async for chunk in speak_stream(question.text):
                await websocket.send_json(
                    {"type": "audio_chunk", "data": base64.b64encode(chunk).decode()}
                )
            await websocket.send_json({"type": "audio_done"})
        except Exception as e:
            if "close" in str(e).lower() or "disconnected" in str(e).lower():
                logger.info("Client disconnected during TTS streaming for question %s", question.id)
            else:
                logger.exception("TTS streaming failed for question %s", question.id)
                try:
                    await websocket.send_json({"type": "audio_done"})
                except Exception:
                    pass
    except Exception as e:
        if "close" in str(e).lower() or "disconnected" in str(e).lower():
            logger.info("Client disconnected before sending question %s", question.id)
        else:
            logger.exception("Failed to send question %s", question.id)


async def _handle_answer(
    websocket: WebSocket,
    session_id: UUID,
    question_id: UUID,
    text: str,
    eval_queue: asyncio.Queue,
) -> None:
    """Persist an answer, ACK the client, fire background evaluation, send next question."""
    async with async_session_factory() as db:
        session = await service.get_session(db, session_id)
        if not session:
            await websocket.send_json({"type": "error", "detail": "Session not found"})
            return

        q_result = await db.execute(
            select(Question).where(
                Question.id == question_id,
                Question.interview_id == session.interview_id,
            )
        )
        question = q_result.scalar_one_or_none()
        if not question:
            await websocket.send_json({"type": "error", "detail": "Question not found"})
            return

        dup_result = await db.execute(
            select(Answer).where(
                Answer.session_id == session_id,
                Answer.question_id == question_id,
            )
        )
        if dup_result.scalar_one_or_none():
            await websocket.send_json({"type": "error", "detail": "Question already answered"})
            return

        answer = await service.create_answer(db, session_id, question_id, text)

        interview = await db.get(Interview, session.interview_id)
        role = interview.role if interview else None
        difficulty = question.difficulty or (interview.difficulty if interview else None)
        question_text = question.text
        answer_id = answer.id

    try:
        await websocket.send_json({"type": "answer_received", "answer_id": str(answer_id)})
    except Exception:
        logger.info("Client disconnected before ACK for answer %s", answer_id)
        return

    # Wait for evaluation and potential follow-up before proceeding.
    async with async_session_factory() as db:
        score, feedback, followup_q = await service.evaluate_and_maybe_followup(
            db=db,
            session=session,
            question=question,
            answer_id=answer_id,
            answer_text=text,
        )

    # Push evaluation to client.
    await eval_queue.put(
        {"answer_id": str(answer_id), "score": score, "feedback": feedback}
    )

    if followup_q:
        # Send follow-up to client.
        await websocket.send_json(
            {
                "type": "question",
                "question_id": str(followup_q.id),
                "text": followup_q.text,
                "order": followup_q.order,
                "is_followup": True,
            }
        )

        # Stream TTS for follow-up.
        try:
            async for chunk in speak_stream(followup_q.text):
                await websocket.send_json(
                    {"type": "audio_chunk", "data": base64.b64encode(chunk).decode()}
                )
            await websocket.send_json({"type": "audio_done"})
        except Exception:
            logger.exception("TTS streaming failed for follow-up %s", followup_q.id)
            await websocket.send_json({"type": "audio_done"})

    else:
        # Send the next pre-generated question.
        await _send_next_question(websocket, session_id)
