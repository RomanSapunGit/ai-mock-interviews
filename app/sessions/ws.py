"""
WebSocket handler for a live interview session.

Protocol
--------
Connection: /sessions/{session_id}/ws?token=<JWT>  (token required; the
session must belong to the token's user).

Server → Client (JSON frames):
  {"type": "question",        "question_id": str, "text": str, "order": int,
                              "time_limit_seconds"?: int, "elapsed_seconds"?: int, ...}
    # elapsed_seconds > 0 when the question was already served earlier in this
    # session (reconnect); the client resumes its countdown from there.
  {"type": "audio_chunk",     "data": str}          # base64-encoded MP3 chunk
  {"type": "audio_done"}
  {"type": "answer_received", "answer_id": str}
  {"type": "evaluation",      "answer_id": str, "score": float, "feedback": str}
  {"type": "hint",            "text": str}
  {"type": "clarification",   "text": str}          # spoken spec answer to a clarifying question
  {"type": "probe_question",  "text": str, "index": int, "total": int}
    # post-submission reasoning check; the client records a spoken answer and
    # streams it back between probe_audio_start / probe_audio_end.
  {"type": "probe_complete"}
  {"type": "evaluating_overall"}
  {"type": "session_complete", "interview_id": str}
  {"type": "error",           "detail": str}

Client → Server (JSON frames):
  {"type": "answer_text",        "question_id": str, "text": str}
  {"type": "answer_code",        "question_id": str, "text"?: str, "code"?: str, "language"?: str, "examples"?: str}
  {"type": "answer_audio_start", "question_id": str, "filename": str}
  {"type": "answer_audio_end",   "code"?: str, "language"?: str, "examples"?: str}
  {"type": "probe_audio_start",  "filename": str}
  {"type": "probe_audio_end"}
  {"type": "request_hint",       "question_id": str, ...}
  {"type": "vad_segment",        "question_id": str, "audio": str, "code"?: str, "language"?: str, "examples"?: str}
    # base64-encoded WAV clip of one voice-activity-detected utterance during
    # a coding question. Classified server-side; a spoken spec answer is sent
    # back for clarifying questions, a spoken hint when the candidate sounds
    # stuck — otherwise the server stays silent.

Client → Server (binary frames):
  Raw audio bytes streamed between answer_audio_start / answer_audio_end or
  probe_audio_start / probe_audio_end.

All outbound frames go through a single queue drained by one sender task, so
concurrent producers (evaluation, TTS streaming, next-question) never write
to the socket simultaneously.
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.ai.evaluator import answer_clarification, classify_intent, generate_hint, generate_probe_questions
from app.ai.transcriber import transcribe_audio
from app.ai.tts import speak_stream
from app.auth.service import user_id_from_token
from app.db.models import Answer, Interview, Question
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
    tts_lock = asyncio.Lock()
    vad_state = {"current_question_id": None, "latest_seq": 0}
    # Connection-local state for the post-submission reasoning probe; only one
    # probe can be active because the next question is not served until the
    # probed answer's evaluation completes.
    probe_state: dict = {
        "active": False,
        "answer_id": None,
        "question_id": None,
        "questions": [],
        "idx": 0,
        "dialogue": [],
        "evaluation_answer": None,
        "evaluation_transcript": None,
        "examples": None,
    }

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
        audio_mode: str = "answer"

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
                            tts_lock,
                            vad_state,
                            probe_state,
                            text=data["text"],
                        )
                    )

                elif msg_type == "answer_code":
                    spawn(
                        _process_answer(
                            send,
                            session_id,
                            UUID(data["question_id"]),
                            tts_lock,
                            vad_state,
                            probe_state,
                            text=data.get("text"),
                            code=data.get("code"),
                            language=data.get("language"),
                            examples=data.get("examples"),
                        )
                    )

                elif msg_type == "answer_audio_start":
                    audio_question_id = UUID(data["question_id"])
                    audio_filename = data.get("filename", "audio.webm")
                    audio_buf = []
                    collecting_audio = True
                    audio_mode = "answer"

                elif msg_type == "answer_audio_end":
                    if not (collecting_audio and audio_mode == "answer" and audio_question_id and audio_buf):
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
                            tts_lock,
                            vad_state,
                            probe_state,
                            code=data.get("code"),
                            language=data.get("language"),
                            examples=data.get("examples"),
                        )
                    )

                elif msg_type == "probe_audio_start":
                    audio_filename = data.get("filename", "probe.webm")
                    audio_buf = []
                    collecting_audio = True
                    audio_mode = "probe"

                elif msg_type == "probe_audio_end":
                    if not (collecting_audio and audio_mode == "probe" and probe_state["active"]):
                        continue
                    collecting_audio = False
                    audio_bytes = b"".join(audio_buf)
                    audio_buf = []

                    spawn(
                        _process_probe_audio(
                            send,
                            session_id,
                            tts_lock,
                            vad_state,
                            probe_state,
                            audio_bytes,
                            audio_filename,
                        )
                    )

                elif msg_type == "request_hint":
                    spawn(
                        _handle_manual_hint(
                            send,
                            tts_lock,
                            interview_id,
                            UUID(data["question_id"]),
                            code=data.get("code"),
                            language=data.get("language"),
                            transcript=data.get("transcript", ""),
                            examples=data.get("examples"),
                        )
                    )

                elif msg_type == "vad_segment":
                    vad_state["latest_seq"] += 1
                    spawn(
                        _process_vad_segment(
                            send,
                            session_id,
                            tts_lock,
                            vad_state,
                            probe_state,
                            interview_id,
                            UUID(data["question_id"]),
                            vad_state["latest_seq"],
                            base64.b64decode(data["audio"]),
                            code=data.get("code"),
                            language=data.get("language"),
                            examples=data.get("examples"),
                        )
                    )
            except (KeyError, ValueError):
                await send({"type": "error", "detail": "Malformed message"})

    send_task = asyncio.create_task(send_loop())
    recv_task = asyncio.create_task(receive_loop())
    spawn(_send_next_question(send, session_id, tts_lock, vad_state))

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


async def _send_next_question(send, session_id: UUID, tts_lock: asyncio.Lock, vad_state: dict) -> None:
    """Queue the next unanswered question (text + TTS audio), or finish the session."""
    await _evaluate_orphan_answers(send, session_id)

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

    await _send_question_with_tts(send, session_id, question, tts_lock, vad_state)


async def _evaluate_orphan_answers(send, session_id: UUID) -> None:
    """Evaluate answers left unscored by a disconnect mid-probe or mid-evaluation.

    Runs before the next question is served, so any follow-up question a
    recovered evaluation creates is picked up by the normal serving query.
    """
    async with async_session_factory() as db:
        session = await service.get_session(db, session_id)
        if not session:
            return
        result = await db.execute(
            select(Answer).where(
                Answer.session_id == session_id,
                Answer.score.is_(None),
                Answer.ai_feedback.is_(None),
            )
        )
        answers = list(result.scalars().all())
        for answer in answers:
            question = await db.get(Question, answer.question_id)
            if question is None:
                continue
            is_coding = question.question_type == "coding"
            try:
                score, feedback, _ = await service.evaluate_and_maybe_followup(
                    db=db,
                    session=session,
                    question=question,
                    answer_id=answer.id,
                    answer_text=(answer.code if is_coding else answer.text) or "",
                    transcript=answer.text if is_coding else None,
                )
                await send(
                    {"answer_id": str(answer.id), "score": score, "feedback": feedback, "type": "evaluation"}
                )
            except Exception:
                logger.exception("Recovery evaluation failed for answer %s", answer.id)


async def _send_question_with_tts(
    send, session_id: UUID, question: Question, tts_lock: asyncio.Lock, vad_state: dict, is_followup: bool = False
) -> None:
    vad_state["current_question_id"] = question.id
    vad_state["latest_seq"] = 0

    frame = {
        "type": "question",
        "question_id": str(question.id),
        "text": question.text,
        "order": question.order,
        "question_type": question.question_type,
        "starter_code": question.starter_code,
        "examples": question.examples,
    }
    if question.time_limit_seconds is not None:
        async with async_session_factory() as db:
            served_at = await service.record_question_served(db, session_id, question.id)
        elapsed = int((datetime.now(timezone.utc) - served_at).total_seconds())
        frame["time_limit_seconds"] = question.time_limit_seconds
        frame["elapsed_seconds"] = max(0, elapsed)
    if is_followup:
        frame["is_followup"] = True
    await send(frame)

    await _speak_text(send, tts_lock, question.text)


async def _speak_text(send, tts_lock: asyncio.Lock, text: str) -> None:
    """Stream `text` as audio_chunk/audio_done TTS frames.

    Shared by the question/follow-up, manual-hint, and auto-hint paths so
    only one place ever talks to speak_stream(), and so TTS from different
    triggers can never interleave into the client's single audio_chunk
    stream at the same time.
    """
    async with tts_lock:
        try:
            async for chunk in speak_stream(text):
                await send({"type": "audio_chunk", "data": base64.b64encode(chunk).decode()})
        except Exception:
            logger.exception("TTS streaming failed")
        finally:
            await send({"type": "audio_done"})


async def _process_audio_answer(
    send,
    session_id: UUID,
    question_id: UUID,
    audio_bytes: bytes,
    filename: str,
    tts_lock: asyncio.Lock,
    vad_state: dict,
    probe_state: dict,
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
        tts_lock,
        vad_state,
        probe_state,
        text=transcript,
        code=code,
        language=language,
        examples=examples,
    )


async def _process_answer(
    send,
    session_id: UUID,
    question_id: UUID,
    tts_lock: asyncio.Lock,
    vad_state: dict,
    probe_state: dict,
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
        question_text = question.text
        hidden_spec = question.hidden_spec
        parent_question_id = question.parent_question_id
        answer_id = answer.id

    await send({"type": "answer_received", "answer_id": str(answer_id)})

    evaluation_answer = code if question_type == "coding" else (text or "")
    evaluation_transcript = text if question_type == "coding" else None

    if question_type == "coding" and parent_question_id is None:
        # Reasoning probe: no more VAD reactions for this question while the
        # candidate answers the interviewer's post-submission questions.
        vad_state["current_question_id"] = None
        async with async_session_factory() as db:
            clarifications = await service.list_clarifications(db, session_id, question_id)
        clar_summary = (
            "\n".join(f'Asked: "{c.asked_text}" → Answered: "{c.answer_text}"' for c in clarifications)
            or None
        )
        probe_questions = await generate_probe_questions(
            question=question_text,
            code=code or "",
            language=language or "python",
            transcript=text or "",
            hidden_spec=hidden_spec,
            clarifications=clar_summary,
        )
        if probe_questions:
            probe_state.update(
                {
                    "active": True,
                    "answer_id": answer_id,
                    "question_id": question_id,
                    "questions": probe_questions,
                    "idx": 0,
                    "dialogue": [],
                    "evaluation_answer": evaluation_answer,
                    "evaluation_transcript": evaluation_transcript,
                    "examples": examples,
                }
            )
            await send(
                {"type": "probe_question", "text": probe_questions[0], "index": 0, "total": len(probe_questions)}
            )
            await _speak_text(send, tts_lock, probe_questions[0])
            return

    await _evaluate_and_continue(
        send,
        session_id,
        question_id,
        answer_id,
        tts_lock,
        vad_state,
        evaluation_answer=evaluation_answer,
        evaluation_transcript=evaluation_transcript,
        examples=examples,
        probe_dialogue=None,
    )


async def _process_probe_audio(
    send,
    session_id: UUID,
    tts_lock: asyncio.Lock,
    vad_state: dict,
    probe_state: dict,
    audio_bytes: bytes,
    filename: str,
) -> None:
    """Record one spoken probe answer, then ask the next probe question or
    finish the probe and run the (now probe-aware) evaluation."""
    if not probe_state["active"]:
        return

    transcript = ""
    try:
        transcript = await transcribe_audio(audio_bytes, filename)
    except Exception:
        logger.exception("Probe answer transcription failed for session %s", session_id)

    idx = probe_state["idx"]
    probe_state["dialogue"].append(
        {"question": probe_state["questions"][idx], "answer": transcript.strip() or "(inaudible)"}
    )
    probe_state["idx"] = idx + 1

    if probe_state["idx"] < len(probe_state["questions"]):
        next_question = probe_state["questions"][probe_state["idx"]]
        await send(
            {
                "type": "probe_question",
                "text": next_question,
                "index": probe_state["idx"],
                "total": len(probe_state["questions"]),
            }
        )
        await _speak_text(send, tts_lock, next_question)
        return

    probe_state["active"] = False
    await send({"type": "probe_complete"})
    await _evaluate_and_continue(
        send,
        session_id,
        probe_state["question_id"],
        probe_state["answer_id"],
        tts_lock,
        vad_state,
        evaluation_answer=probe_state["evaluation_answer"],
        evaluation_transcript=probe_state["evaluation_transcript"],
        examples=probe_state["examples"],
        probe_dialogue=probe_state["dialogue"],
    )


async def _evaluate_and_continue(
    send,
    session_id: UUID,
    question_id: UUID,
    answer_id: UUID,
    tts_lock: asyncio.Lock,
    vad_state: dict,
    evaluation_answer: str | None,
    evaluation_transcript: str | None,
    examples: str | None,
    probe_dialogue: list[dict] | None,
) -> None:
    followup_q = None
    try:
        async with async_session_factory() as db:
            session = await service.get_session(db, session_id)
            question = await db.get(Question, question_id)
            if session is None or question is None:
                return
            if probe_dialogue:
                answer = await db.get(Answer, answer_id)
                if answer:
                    answer.probe_dialogue = json.dumps(probe_dialogue)
                    await db.commit()
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
        await _send_question_with_tts(send, session_id, followup_q, tts_lock, vad_state, is_followup=True)
    else:
        await _send_next_question(send, session_id, tts_lock, vad_state)


async def _handle_manual_hint(
    send,
    tts_lock: asyncio.Lock,
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
    await _speak_text(send, tts_lock, hint_text)


async def _process_vad_segment(
    send,
    session_id: UUID,
    tts_lock: asyncio.Lock,
    vad_state: dict,
    probe_state: dict,
    interview_id: UUID,
    question_id: UUID,
    seq: int,
    audio_bytes: bytes,
    code: str | None = None,
    language: str | None = None,
    examples: str | None = None,
) -> None:
    """Classify one VAD-segmented utterance and speak back only when the
    candidate is asking something: a spec answer for clarifying questions,
    a hint when they sound stuck. Stay silent otherwise.

    Runs under tts_lock end-to-end so overlapping utterances can never speak
    over each other, and re-checks `seq` against vad_state["latest_seq"]
    before transcribing and again before speaking: if a newer utterance has
    arrived while this one waited for the lock or for the LLM round-trips,
    this one is stale and is dropped rather than queued.

    All speech here is inlined via speak_stream — never _speak_text, which
    would deadlock on the already-held (non-reentrant) tts_lock.
    """
    if probe_state["active"]:
        return

    async with tts_lock:
        if seq != vad_state["latest_seq"]:
            return

        try:
            transcript = await transcribe_audio(audio_bytes, "segment.wav")
        except Exception:
            logger.exception("VAD segment transcription failed")
            return
        if not transcript.strip():
            return

        async with async_session_factory() as db:
            q_result = await db.execute(
                select(Question).where(
                    Question.id == question_id,
                    Question.interview_id == interview_id,
                )
            )
            question = q_result.scalar_one_or_none()
        if not question or vad_state["current_question_id"] != question_id:
            return

        intent = await classify_intent(transcript, question.text)

        if intent == "clarification" and question.question_type == "coding" and question.hidden_spec:
            if seq != vad_state["latest_seq"]:
                return
            answer_text, resolved_points = await answer_clarification(
                question=question.text,
                hidden_spec=question.hidden_spec,
                transcript=transcript,
            )
            if seq != vad_state["latest_seq"]:
                return
            async with async_session_factory() as db:
                await service.create_clarification(
                    db, session_id, question_id, transcript, answer_text, resolved_points
                )
            await send({"type": "clarification", "text": answer_text})
            try:
                async for chunk in speak_stream(answer_text):
                    await send({"type": "audio_chunk", "data": base64.b64encode(chunk).decode()})
            except Exception:
                logger.exception("TTS streaming failed for clarification answer")
            finally:
                await send({"type": "audio_done"})
            return

        # A clarification with no hidden spec (legacy questions) still gets a
        # hint rather than silence.
        if intent not in ("hint", "clarification"):
            return

        if seq != vad_state["latest_seq"]:
            return

        hint_text = await generate_hint(
            question=question.text,
            code=code or "",
            language=language or "python",
            transcript=transcript,
            examples=examples,
        )
        await send({"type": "hint", "text": hint_text})
        try:
            async for chunk in speak_stream(hint_text):
                await send({"type": "audio_chunk", "data": base64.b64encode(chunk).decode()})
        except Exception:
            logger.exception("TTS streaming failed for VAD-triggered hint")
        finally:
            await send({"type": "audio_done"})
