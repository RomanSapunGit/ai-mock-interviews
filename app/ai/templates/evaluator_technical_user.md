Evaluate the candidate's answer to a verbal technical interview question.

Role: $role
Difficulty: $difficulty

Question:
$question

Candidate's answer (evaluate this exact text, nothing more):
$answer

Judge the answer on:
- **Accuracy**: are the technical claims correct?
- **Depth**: does it go beyond definitions into trade-offs, edge cases or real-world implications appropriate for $difficulty difficulty?
- **Clarity**: is the explanation structured and easy to follow?

Return a JSON object with:
- "score": a float from 0.0 to 10.0 based solely on what was written
- "feedback": one or two sentences — what was correct, what was missing or wrong

Example: {"score": 6.5, "feedback": "Correct definition with a good example, but you didn't cover the trade-offs that matter at scale."}
