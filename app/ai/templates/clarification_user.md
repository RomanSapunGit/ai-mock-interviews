The candidate is working on this coding task and just asked the interviewer a clarifying question.

Task:
"$question"

Hidden Specification (deliberately underspecified points; the index of each entry matters):
$hidden_spec

Candidate's Spoken Question:
"$transcript"

Answer as the interviewer would, following these rules:
- Answer ONLY what was asked, in 1-2 short spoken-style sentences, using the canonical answers from the hidden specification.
- NEVER volunteer other hidden points and never read the specification aloud.
- If the question is not covered by the hidden specification, respond like a reasonable interviewer: tell them it is their call, to pick something sensible and state their assumption — and return an empty resolved_points list.
- `resolved_points` must contain the zero-based indices of the hidden specification entries your answer resolves.

Return a JSON object:
{
  "answer": "...",
  "resolved_points": [0]
}
