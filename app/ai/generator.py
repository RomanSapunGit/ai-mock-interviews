import json
import logging
from app.config.settings import settings
from app.ai.prompts import render

logger = logging.getLogger(__name__)

_TIME_LIMIT_DEFAULTS = {"easy": 900, "medium": 1500, "hard": 2100}


def _resolve_time_limit_seconds(q: dict, difficulty: str | None) -> int:
    try:
        minutes = int(q["time_limit_minutes"])
    except (KeyError, TypeError, ValueError):
        return _TIME_LIMIT_DEFAULTS.get(difficulty or "medium", 1500)
    return max(5, min(60, minutes)) * 60


def _normalize_examples(examples) -> str | None:
    # The template asks for a string, but some models return structured JSON anyway.
    if examples is None or isinstance(examples, str):
        return examples
    return json.dumps(examples, indent=2)


async def generate_questions(
    context_chunks: list[str],
    role: str | None,
    difficulty: str | None,
    topic: str | None,
    count: int = 5,
    interview_type: str = "behavioral",
) -> list[dict]:
    """
    Generate interview questions via Groq LLM using RAG context chunks.

    Returns a list of dicts with keys: text, category, difficulty.
    Raises on API or parsing failure.
    """
    context = "\n\n---\n\n".join(context_chunks) if context_chunks else ""

    system_prompt = render("generator_system")
    generator_templates = {
        "coding": "generator_coding_user",
        "technical": "generator_technical_user",
    }
    template_name = generator_templates.get(interview_type, "generator_user")
    user_prompt = render(
        template_name,
        count=str(count),
        role=role or "software engineer",
        difficulty=difficulty or "medium",
        topic_section=f"Focus on: {topic}" if topic else "",
        context_section=f"Candidate material (base your questions on this):\n{context}" if context else "",
    )

    response = await settings.evaluator.client.chat.completions.create(
        model=settings.app.LLM_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.7,
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content or "{}"
    data = json.loads(raw)

    questions = data.get("questions", [])
    if not isinstance(questions, list):
        raise ValueError(f"Unexpected LLM response shape: {data}")

    result: list[dict] = []
    for q in questions:
        if isinstance(q, dict) and q.get("text"):
            entry = {
                "text": str(q["text"]),
                "category": str(q.get("category", interview_type)),
                "difficulty": str(q.get("difficulty", difficulty or "medium")),
                "question_type": str(q.get("question_type", interview_type)),
                "starter_code": q.get("starter_code"),
                "examples": _normalize_examples(q.get("examples")),
            }
            if entry["question_type"] == "coding":
                hidden_spec = q.get("hidden_spec")
                entry["hidden_spec"] = json.dumps(hidden_spec) if isinstance(hidden_spec, list) else None
                entry["time_limit_seconds"] = _resolve_time_limit_seconds(q, difficulty)
            result.append(entry)

    return result[:count]
