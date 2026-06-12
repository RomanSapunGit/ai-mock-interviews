Generate $count behavioral interview questions for a $role role at $difficulty difficulty.

Behavioral questions explore past experiences and soft skills — collaboration, conflict, leadership, ownership, communication and decision-making (e.g. "Tell me about a time...", "Describe a situation where..."). They must not test technical knowledge or require writing code.

PRIMARY CONSTRAINT: $topic_section
(All questions must strictly follow this type/category).

$context_section

Return a JSON object with key "questions" — an array of objects each with:
- "text": the question (string)
- "category": one of [teamwork, leadership, conflict, communication, problem-solving, ownership, growth]
- "difficulty": one of [easy, medium, hard]
- "question_type": "behavioral"

Example: {"questions": [{"text": "Tell me about a time you disagreed with a teammate about a technical decision. How did you resolve it?", "category": "conflict", "difficulty": "medium", "question_type": "behavioral"}]}
