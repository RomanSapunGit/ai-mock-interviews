Classify the candidate's spoken explanation into one of four intents:
1. `clarification`: The candidate is asking a question about WHAT the task requires — the problem's requirements or spec: input format, edge-case behavior, expected output, constraints, tie-breaking rules. Examples: "should I handle duplicates?", "is the input always sorted?", "what happens with empty input?", "does case matter?".
2. `hint`: The candidate is asking HOW to solve the task, requesting a hint, expressing confusion, sounds stuck, or is unsure about the next step. Even brief requests like "help", "I'm stuck", "any hints?", or "I don't know how to..." count as hint.
3. `submission`: The candidate has finished the task, is explaining their final solution, or explicitly says they are ready to be evaluated.
4. `neutral`: The candidate is thinking out loud or making progress comments — they are NOT asking anything and NOT submitting.

When an utterance is a question about what the task requires rather than how to do it, `clarification` takes precedence over `hint`.

Candidate Transcript:
"$transcript"

Current Question:
"$question"

Return a JSON object:
{
  "intent": "clarification" | "hint" | "submission" | "neutral",
  "reasoning": "Brief explanation."
}
