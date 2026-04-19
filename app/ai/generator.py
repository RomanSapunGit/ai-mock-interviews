import json
import logging
from openai import AsyncOpenAI
from app.config.settings import settings
from app.ai.prompts import render

logger = logging.getLogger(__name__)

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
    template_name = "generator_coding_user" if interview_type == "coding" else "generator_user"
    user_prompt = render(
        template_name,
        count=str(count),
        role=role or "software engineer",
        difficulty=difficulty or "medium",
        topic_section=f"Focus on: {topic}" if topic else "",
        context_section=f"Candidate material (base your questions on this):\n{context}" if context else "",
    )

    response = await settings.evaluator.client.chat.completions.create(
        model=settings.app.GROQ_MODEL,
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
            result.append(
                {
                    "text": str(q["text"]),
                    "category": str(q.get("category", "coding")),
                    "difficulty": str(q.get("difficulty", difficulty or "medium")),
                    "question_type": str(q.get("question_type", interview_type)),
                    "starter_code": q.get("starter_code"),
                    "examples": q.get("examples"),
                }
            )

    return result[:count]
