Generate $count live-coding interview questions for the role: $role.
Difficulty level: $difficulty.
$topic_section

$context_section

Each question must be a PRACTICAL, REAL-WORLD coding task — the kind of work a $role does day to day (e.g. parse and transform messy data, implement a rate limiter or retry policy, deduplicate/merge records, build a small caching or validation utility, process a log or event stream). Do NOT generate abstract algorithm puzzles (no "two sum", "reverse a linked list", array/graph brainteasers).

Each question must be DELIBERATELY UNDERSPECIFIED, like a real ticket: omit 3-5 concrete decisions from the problem description and examples (e.g. how to handle malformed input, tie-breaking rules, case sensitivity, ordering of results, timezone handling, what to do on duplicates or empty input). A strong candidate is expected to notice these gaps and ask clarifying questions. List every omitted decision in 'hidden_spec' together with the canonical answer you, as the interviewer, would give when asked.

For each question, provide:
1. 'text': The task description — realistic, business-framed, and intentionally silent on the hidden_spec points.
2. 'category': 'coding'.
3. 'difficulty': '$difficulty'.
4. 'question_type': 'coding'.
5. 'starter_code': A boilerplate function/class signature in Python or the language most relevant to the role.
6. 'examples': 1-2 happy-path input/output examples ONLY. The examples must NOT reveal or resolve any hidden_spec point.
7. 'hidden_spec': A list of the deliberately omitted decisions, each with the interviewer's canonical answer.
8. 'time_limit_minutes': A realistic time budget for the task (an integer, scaled to the difficulty and scope).

Respond in JSON format as follows:
{
  "questions": [
    {
      "text": "...",
      "category": "coding",
      "difficulty": "...",
      "question_type": "coding",
      "starter_code": "...",
      "examples": "...",
      "hidden_spec": [
        {"point": "What should happen with malformed rows?", "answer": "Skip them but count them; return the count alongside the result."}
      ],
      "time_limit_minutes": 25
    }
  ]
}
