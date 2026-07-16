import json
import logging
from app.config.settings import settings
from app.ai.prompts import render

logger = logging.getLogger(__name__)

def _fast_llm_kwargs() -> dict:
    model = settings.app.LLM_FAST_MODEL
    # Gemini models think by default and bill the reasoning tokens as output;
    # lightweight calls don't need them. Other providers reject the param.
    if model.startswith("gemini"):
        return {"model": model, "reasoning_effort": "none"}
    return {"model": model}

async def evaluate_answer(
    question: str,
    answer: str,
    role: str | None = None,
    difficulty: str | None = None,
    question_type: str = "behavioral",
    transcript: str | None = None,
    examples: str | None = None,
    hidden_spec: str | None = None,
    clarifications: str | None = None,
    time_summary: str | None = None,
    probe_dialogue: str | None = None,
) -> tuple[float, str]:
    """
    Evaluate a candidate's answer using the LLM.

    Returns (score, feedback) where score is 0.0–10.0.
    Raises on API or parsing failure.
    """
    evaluator_templates = {
        "coding": "evaluator_coding_user",
        "technical": "evaluator_technical_user",
    }
    template_name = evaluator_templates.get(question_type, "evaluator_user")
    system_prompt = render("evaluator_system")
    user_prompt = render(
        template_name,
        role=role or "software engineer",
        difficulty=difficulty or "medium",
        question=question,
        answer=answer,
        transcript=transcript or "No verbal explanation provided.",
        examples=examples or "No specific examples provided.",
        hidden_spec=hidden_spec or "Not applicable.",
        clarifications=clarifications or "Not applicable.",
        time_summary=time_summary or "No time data.",
        probe_dialogue=probe_dialogue or "Not applicable.",
    )

    response = await settings.evaluator.client.chat.completions.create(
        model=settings.app.LLM_MODEL,
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

    response = await settings.evaluator.fast_client.chat.completions.create(
        **_fast_llm_kwargs(),
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
    qa_pairs should be a list of dicts: {"question": str, "answer": str, "score": float},
    optionally extended with "clarifications", "missed_points", "time_summary", "probe_dialogue".
    """
    blocks = []
    for i, item in enumerate(qa_pairs, start=1):
        lines = [
            "---",
            f"Question {i}: {item['question']}",
            f"Answer: {item['answer']}",
            f"Individual Score: {item['score']}/10",
        ]
        if item.get("clarifications"):
            lines.append(f"Clarifying questions asked: {item['clarifications']}")
        if item.get("missed_points"):
            lines.append(f"Ambiguities MISSED (never asked about): {item['missed_points']}")
        if item.get("time_summary"):
            lines.append(f"Time: {item['time_summary']}")
        if item.get("probe_dialogue"):
            lines.append(f"Post-submission reasoning probe: {item['probe_dialogue']}")
        lines.append("---")
        blocks.append("\n".join(lines))

    system_prompt = render("overall_evaluator_system")
    user_prompt = render(
        "overall_evaluator_user",
        role=role or "software engineer",
        difficulty=difficulty or "medium",
        qa_block="\n".join(blocks),
    )

    try:
        response = await settings.evaluator.client.chat.completions.create(
            model=settings.app.LLM_MODEL,
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

        avg = sum(p.get("score", 0.0) for p in qa_pairs) / len(qa_pairs) if qa_pairs else 0.0
        return avg, "Overall evaluation failed to generate."

async def classify_intent(transcript: str, question: str) -> str:
    """
    Classify the candidate's intent:
    - 'clarification': Asking what the task requires (spec/requirements question).
    - 'hint': Asking for help or sounds stuck.
    - 'submission': Providing a final answer or ready to evaluate.
    - 'neutral': Thinking out loud, acknowledging, or small talk.
    """
    system_prompt = (
        "You are an expert technical interviewer. Classify the candidate's spoken intent. "
        "If the candidate asks a question about WHAT the task requires — input format, edge cases, "
        "expected output, constraints — classify as 'clarification'; it takes precedence over 'hint'. "
        "If the candidate asks HOW to solve it, requests a hint, or expresses confusion/being stuck, classify as 'hint'. "
        "Err on the side of 'hint' when the candidate sounds uncertain — it's better to offer help than to stay silent. "
        "Only classify as 'submission' if they sound finished or explicitly submit. "
        "Only classify as 'neutral' if they are clearly just thinking out loud without needing assistance."
    )
    user_prompt = render(
        "intent_classifier_user",
        transcript=transcript,
        question=question,
    )

    try:
        response = await settings.evaluator.fast_client.chat.completions.create(
            **_fast_llm_kwargs(),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        data = json.loads(response.choices[0].message.content or "{}")
        return data.get("intent", "neutral")
    except Exception as e:
        logger.error(f"Intent classification failed: {e}")
        return "neutral"

async def generate_hint(question: str, code: str, language: str, transcript: str, examples: str | None = None) -> str:
    """
    Generate a helpful hint based on current code and spoken approach.
    """
    system_prompt = "You are a helpful interviewer providing subtle hints."
    user_prompt = render(
        "hint_user",
        question=question,
        code=code,
        language=language,
        transcript=transcript,
        examples=examples or "No specific examples provided.",
    )

    try:
        response = await settings.evaluator.fast_client.chat.completions.create(
            **_fast_llm_kwargs(),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.5,
            response_format={"type": "json_object"},
        )
        data = json.loads(response.choices[0].message.content or "{}")
        return data.get("hint", "Try to think about the problem step by step.")
    except Exception as e:
        logger.error(f"Hint generation failed: {e}")
        return "Keep going, you're on the right track."

async def answer_clarification(question: str, hidden_spec: str, transcript: str) -> tuple[str, list[int]]:
    """
    Answer a candidate's clarifying question from the hidden spec.
    Returns (spoken answer, zero-based hidden_spec indices the answer resolved).
    """
    system_prompt = (
        "You are a technical interviewer answering a candidate's clarifying question about the task. "
        "Be precise, brief, and never give away more than what was asked."
    )
    user_prompt = render(
        "clarification_user",
        question=question,
        hidden_spec=hidden_spec,
        transcript=transcript,
    )

    try:
        response = await settings.evaluator.fast_client.chat.completions.create(
            **_fast_llm_kwargs(),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        data = json.loads(response.choices[0].message.content or "{}")
        answer = str(data.get("answer", "")).strip()
        resolved = [int(i) for i in data.get("resolved_points", []) if isinstance(i, (int, float))]
        if not answer:
            raise ValueError("Empty clarification answer")
        return answer, resolved
    except Exception as e:
        logger.error(f"Clarification answering failed: {e}")
        return "Good question — make a reasonable assumption and mention it in your solution.", []

async def generate_probe_questions(
    question: str,
    code: str,
    language: str,
    transcript: str,
    hidden_spec: str | None = None,
    clarifications: str | None = None,
) -> list[str]:
    """
    Generate 1-2 short spoken questions probing the candidate's reasoning about
    their submitted code. Returns [] on failure so the probe is silently skipped.
    """
    system_prompt = (
        "You are a technical interviewer doing a short reasoning check after a code submission. "
        "Ask about the candidate's own code and decisions; never reveal the intended solution."
    )
    user_prompt = render(
        "probe_user",
        question=question,
        code=code,
        language=language,
        transcript=transcript,
        hidden_spec=hidden_spec or "Not applicable.",
        clarifications=clarifications or "None.",
    )

    try:
        response = await settings.evaluator.fast_client.chat.completions.create(
            **_fast_llm_kwargs(),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.5,
            response_format={"type": "json_object"},
        )
        data = json.loads(response.choices[0].message.content or "{}")
        questions = data.get("questions", [])
        if not isinstance(questions, list):
            return []
        return [str(q).strip() for q in questions if str(q).strip()][:2]
    except Exception as e:
        logger.error(f"Probe question generation failed: {e}")
        return []
