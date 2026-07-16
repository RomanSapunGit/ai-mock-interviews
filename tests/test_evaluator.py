from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.ai.evaluator import answer_clarification, evaluate_session_overall, generate_probe_questions


def _llm_response(payload: dict) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(payload)))]
    )


@pytest.mark.asyncio
async def test_evaluate_session_overall_prompt_contains_session_data():
    qa_pairs = [
        {
            "question": "Build a rate limiter.",
            "answer": "def limit(): pass",
            "score": 6.5,
            "clarifications": 'Asked: "bursts?" → Interviewer answered: "up to 2x"',
            "missed_points": "[1] malformed input handling",
            "time_summary": "Time limit: 25 min. Time used: 31 min — 6 min OVER the limit.",
            "probe_dialogue": 'Interviewer asked: "why a deque?" — Candidate answered: "O(1) pops."',
        }
    ]
    create = AsyncMock(return_value=_llm_response({"score": 6.0, "feedback": "ok"}))
    with patch("app.ai.evaluator.settings") as settings_mock:
        settings_mock.evaluator.client.chat.completions.create = create
        settings_mock.app.LLM_MODEL = "test-model"
        score, feedback = await evaluate_session_overall(qa_pairs, role="backend engineer", difficulty="medium")

    assert score == 6.0
    user_prompt = create.call_args.kwargs["messages"][1]["content"]
    # Regression for the Jinja-syntax bug: the LLM used to receive the raw
    # unexpanded template instead of the actual session data.
    assert "{{" not in user_prompt and "{%" not in user_prompt
    assert "Build a rate limiter." in user_prompt
    assert "def limit(): pass" in user_prompt
    assert "6.5/10" in user_prompt
    assert "malformed input handling" in user_prompt
    assert "OVER the limit" in user_prompt
    assert "why a deque?" in user_prompt


@pytest.mark.asyncio
async def test_answer_clarification_parses_answer_and_points():
    create = AsyncMock(
        return_value=_llm_response({"answer": "Yes, allow bursts up to 2x.", "resolved_points": [0, 2]})
    )
    with patch("app.ai.evaluator.settings") as settings_mock:
        settings_mock.evaluator.fast_client.chat.completions.create = create
        settings_mock.app.LLM_FAST_MODEL = "test-model"
        answer, resolved = await answer_clarification(
            question="Build a rate limiter.",
            hidden_spec='[{"point": "bursts", "answer": "up to 2x"}]',
            transcript="should bursts be allowed?",
        )

    assert answer == "Yes, allow bursts up to 2x."
    assert resolved == [0, 2]


@pytest.mark.asyncio
async def test_answer_clarification_falls_back_on_failure():
    create = AsyncMock(side_effect=RuntimeError("boom"))
    with patch("app.ai.evaluator.settings") as settings_mock:
        settings_mock.evaluator.fast_client.chat.completions.create = create
        settings_mock.app.LLM_FAST_MODEL = "test-model"
        answer, resolved = await answer_clarification("q", "[]", "t")

    assert resolved == []
    assert "assumption" in answer


@pytest.mark.asyncio
async def test_generate_probe_questions_caps_at_two_and_drops_blanks():
    create = AsyncMock(return_value=_llm_response({"questions": ["Why a deque?", "  ", "What breaks at scale?", "Extra?"]}))
    with patch("app.ai.evaluator.settings") as settings_mock:
        settings_mock.evaluator.fast_client.chat.completions.create = create
        settings_mock.app.LLM_FAST_MODEL = "test-model"
        questions = await generate_probe_questions("q", "code", "python", "t")

    assert questions == ["Why a deque?", "What breaks at scale?"]


@pytest.mark.asyncio
async def test_generate_probe_questions_empty_on_failure():
    create = AsyncMock(side_effect=RuntimeError("boom"))
    with patch("app.ai.evaluator.settings") as settings_mock:
        settings_mock.evaluator.fast_client.chat.completions.create = create
        settings_mock.app.LLM_FAST_MODEL = "test-model"
        assert await generate_probe_questions("q", "code", "python", "t") == []
