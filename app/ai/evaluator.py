import json
import logging
from app.config.settings import settings
from app.ai.prompts import render

logger = logging.getLogger(__name__)


async def evaluate_answer(
    question: str,
    answer: str,
    role: str | None = None,
    difficulty: str | None = None,
) -> tuple[float, str]:
    """
    Evaluate a candidate's answer using the LLM.

    Returns (score, feedback) where score is 0.0–10.0.
    Raises on API or parsing failure.
    """
    system_prompt = render("evaluator_system")
    user_prompt = render(
        "evaluator_user",
        role=role or "software engineer",
        difficulty=difficulty or "medium",
        question=question,
        answer=answer,
    )

    response = await settings.evaluator.client.chat.completions.create(
        model=settings.app.GROQ_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content or "{}"
    data = json.loads(raw)

    score = float(data["score"])
    feedback = str(data["feedback"])

    if not 0.0 <= score <= 10.0:
        raise ValueError(f"Score out of range: {score}")

    return score, feedback


async def generate_followup_question(
    question: str,
    answer: str,
    role: str | None = None,
    difficulty: str | None = None,
) -> str:
    """
    Generate a follow-up question based on the original question and the candidate's answer.
    """
    system_prompt = render("followup_system")
    user_prompt = render(
        "followup_user",
        role=role or "software engineer",
        difficulty=difficulty or "medium",
        question=question,
        answer=answer,
    )

    response = await settings.evaluator.client.chat.completions.create(
        model=settings.app.GROQ_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.7,
    )

    return (response.choices[0].message.content or "").strip()


async def evaluate_session_overall(
    qa_pairs: list[dict],
    role: str | None = None,
    difficulty: str | None = None,
) -> tuple[float, str]:
    """
    Evaluate an entire interview session to provide final score and feedback.
    qa_pairs should be a list of dicts: {"question": str, "answer": str, "score": float}
    """
    system_prompt = render("overall_evaluator_system")
    user_prompt = render(
        "overall_evaluator_user",
        role=role or "software engineer",
        difficulty=difficulty or "medium",
        qa_pairs=qa_pairs,
    )

    try:
        response = await settings.evaluator.client.chat.completions.create(
            model=settings.app.GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.4,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content or "{}"
        data = json.loads(raw)
        
        score = float(data.get("score", 0.0))
        feedback = str(data.get("feedback", ""))
        
        if not 0.0 <= score <= 10.0:
            score = max(0.0, min(10.0, score))
            
        return score, feedback
    except Exception as e:
        logger.error(f"Failed to evaluate session overall: {e}")
        # Fallback to simple average
        avg = sum(p.get("score", 0.0) for p in qa_pairs) / len(qa_pairs) if qa_pairs else 0.0
        return avg, "Overall evaluation failed to generate."
