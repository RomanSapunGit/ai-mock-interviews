Role: {{ role }}
Difficulty: {{ difficulty }}

Here is the transcript of the interview session:

{% for item in qa_pairs %}
---
Question {{ loop.index }}: {{ item.question }}
Answer: {{ item.answer }}
Individual Score: {{ item.score }}/10
---
{% endfor %}

Please provide the final overall score and comprehensive feedback for the entire session.

Remember:
- Only evaluate the ACTUAL text provided in the answers.
- If the majority of the answers are skipped, irrelevant, or minimal (e.g. "asdf", "idk"), the score MUST be extremely low (0-2) and the feedback MUST point out the lack of substantive answers.
