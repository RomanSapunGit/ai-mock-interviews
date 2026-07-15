from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.ai.generator import _resolve_time_limit_seconds, generate_questions


def _llm_response(payload: dict) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(payload)))]
    )


def test_resolve_time_limit_from_minutes():
    assert _resolve_time_limit_seconds({"time_limit_minutes": 25}, "medium") == 1500


def test_resolve_time_limit_clamps():
    assert _resolve_time_limit_seconds({"time_limit_minutes": 2}, "medium") == 300
    assert _resolve_time_limit_seconds({"time_limit_minutes": 500}, "medium") == 3600


def test_resolve_time_limit_difficulty_fallback():
    assert _resolve_time_limit_seconds({}, "easy") == 900
    assert _resolve_time_limit_seconds({"time_limit_minutes": "abc"}, "hard") == 2100
    assert _resolve_time_limit_seconds({}, None) == 1500


@pytest.mark.asyncio
async def test_generate_questions_maps_hidden_spec_and_time_limit():
    payload = {
        "questions": [
            {
                "text": "Build a rate limiter for our public API.",
                "category": "coding",
                "difficulty": "medium",
                "question_type": "coding",
                "starter_code": "def limit(): pass",
                "examples": "Input: ... Output: ...",
                "hidden_spec": [{"point": "burst behavior", "answer": "allow bursts up to 2x"}],
                "time_limit_minutes": 30,
            }
        ]
    }
    create = AsyncMock(return_value=_llm_response(payload))
    with patch("app.ai.generator.settings") as settings_mock:
        settings_mock.evaluator.client.chat.completions.create = create
        settings_mock.app.LLM_MODEL = "test-model"
        result = await generate_questions([], "backend engineer", "medium", None, count=1, interview_type="coding")

    assert len(result) == 1
    q = result[0]
    assert json.loads(q["hidden_spec"]) == [{"point": "burst behavior", "answer": "allow bursts up to 2x"}]
    assert q["time_limit_seconds"] == 1800


@pytest.mark.asyncio
async def test_generate_questions_coding_without_hidden_spec():
    payload = {
        "questions": [
            {
                "text": "Parse a log file.",
                "question_type": "coding",
                "hidden_spec": "not a list",
            }
        ]
    }
    create = AsyncMock(return_value=_llm_response(payload))
    with patch("app.ai.generator.settings") as settings_mock:
        settings_mock.evaluator.client.chat.completions.create = create
        settings_mock.app.LLM_MODEL = "test-model"
        result = await generate_questions([], None, "easy", None, count=1, interview_type="coding")

    assert result[0]["hidden_spec"] is None
    assert result[0]["time_limit_seconds"] == 900


@pytest.mark.asyncio
async def test_generate_questions_behavioral_has_no_timing_fields():
    payload = {"questions": [{"text": "Tell me about a conflict.", "question_type": "behavioral"}]}
    create = AsyncMock(return_value=_llm_response(payload))
    with patch("app.ai.generator.settings") as settings_mock:
        settings_mock.evaluator.client.chat.completions.create = create
        settings_mock.app.LLM_MODEL = "test-model"
        result = await generate_questions([], None, None, None, count=1, interview_type="behavioral")

    assert "hidden_spec" not in result[0]
    assert "time_limit_seconds" not in result[0]
