Classify the candidate's spoken explanation into one of three intents:
1. `hint`: The candidate is asking for help, requesting a hint, expressing confusion, sounds stuck, or is unsure about the next step. Even brief requests like "help", "I'm stuck", "any hints?", or "I don't know how to..." count as hint.
2. `submission`: The candidate has finished the task, is explaining their final solution, or explicitly says they are ready to be evaluated.
3. `neutral`: The candidate is thinking out loud or making progress comments — they are NOT asking for help and NOT submitting.

Candidate Transcript:
"{{transcript}}"

Current Question:
"{{question}}"

Return a JSON object:
{
  "intent": "hint" | "submission" | "neutral",
  "reasoning": "Brief explanation."
}
