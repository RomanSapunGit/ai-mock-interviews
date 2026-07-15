The candidate just submitted their solution to this coding task. Generate the interviewer's post-submission reasoning check.

Task:
"$question"

Candidate's Submitted Code ($language):
```
$code
```

Candidate's Spoken Approach (Transcript):
"$transcript"

Hidden Specification (deliberately underspecified points with canonical answers):
$hidden_spec

Clarifying Questions the Candidate Asked:
$clarifications

Generate 1-2 SHORT questions, phrased for speech, that probe the candidate's reasoning about THEIR code:
- Why they chose a specific structure, approach, or trade-off visible in the code.
- What breaks at scale or on tricky input.
- Prioritize hidden-specification points they never clarified: ask what their code assumes there.
- Never reveal the canonical answers; ask, don't tell.

Return a JSON object:
{
  "questions": ["...", "..."]
}
