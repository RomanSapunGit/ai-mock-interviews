Role: $role
Difficulty: $difficulty

Question:
$question

Candidate's answer (evaluate this exact text, nothing more):
$answer

Return a JSON object with:
- "score": a float from 0.0 to 10.0 based solely on what was written
- "feedback": one or two sentences — what was correct, what was missing or wrong

Example: {"score": 2.0, "feedback": "Your answer doesn't address the question. I'd recommend studying this topic more before the interview."}
