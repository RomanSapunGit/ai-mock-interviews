Generate $count coding interview questions for the role: $role.
Difficulty level: $difficulty.
$topic_section

$context_section

For each question, provide:
1. 'text': The problem description.
2. 'category': 'coding'.
3. 'difficulty': '$difficulty'.
4. 'question_type': 'coding'.
5. 'starter_code': A Python or relevant language boilerplate for the candidate to start with.
6. 'examples': 2-3 clear input/output examples explaining how the function/algorithm should behave (e.g. "Input: nums = [1,2], target = 3 \nOutput: [0,1]").

Respond in JSON format as follows:
{
  "questions": [
    {
      "text": "...",
      "category": "...",
      "difficulty": "...",
      "question_type": "coding",
      "starter_code": "...",
      "examples": "..."
    }
  ]
}
