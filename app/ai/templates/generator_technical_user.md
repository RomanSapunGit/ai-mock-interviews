Generate $count technical interview questions for a $role role at $difficulty difficulty.

These are verbal knowledge questions — the candidate answers by speaking or writing prose, NOT by writing code. Never ask the candidate to implement or write code. Ask about concepts, trade-offs, debugging scenarios, architecture and tooling relevant to the role (e.g. "Explain...", "Compare X and Y...", "What happens when...", "How would you investigate...").

PRIMARY CONSTRAINT: $topic_section
(All questions must strictly follow this type/category).

$context_section

Return a JSON object with key "questions" — an array of objects each with:
- "text": the question (string)
- "category": one of [algorithms, system-design, database, networking, language-specific, architecture, tooling, security]
- "difficulty": one of [easy, medium, hard]
- "question_type": "technical"

Example: {"questions": [{"text": "Explain the difference between optimistic and pessimistic locking, and when you would choose each.", "category": "database", "difficulty": "medium", "question_type": "technical"}]}
