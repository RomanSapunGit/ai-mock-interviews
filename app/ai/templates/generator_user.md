Generate $count interview questions for a $role role at $difficulty difficulty.
PRIMARY CONSTRAINT: $topic_section
(All questions must strictly follow this type/category).

$context_section

Return a JSON object with key "questions" — an array of objects each with:
- "text": the question (string)
- "category": one of [algorithms, system-design, behavioral, coding, database, networking, language-specific]
- "difficulty": one of [easy, medium, hard]

Example: {"questions": [{"text": "...", "category": "coding", "difficulty": "medium"}]}
