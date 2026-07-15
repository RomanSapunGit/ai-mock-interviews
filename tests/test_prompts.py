from __future__ import annotations

import pytest

from app.ai.prompts import render

TEMPLATE_VARS = {
    "generator_coding_user": {
        "count": "2",
        "role": "backend engineer",
        "difficulty": "medium",
        "topic_section": "",
        "context_section": "",
    },
    "evaluator_coding_user": {
        "role": "backend engineer",
        "difficulty": "medium",
        "question": "Build a rate limiter.",
        "answer": "def limit(): pass",
        "transcript": "I used a sliding window.",
        "examples": "Input: ... Output: ...",
        "hidden_spec": '[{"point": "burst behavior", "answer": "allow bursts up to 2x"}]',
        "clarifications": 'Asked: "bursts?" → Interviewer answered: "up to 2x"',
        "time_summary": "Time limit: 25 min. Time used: 20 min — within the limit.",
        "probe_dialogue": 'Interviewer asked: "why a deque?" — Candidate answered: "O(1) pops."',
    },
    "overall_evaluator_user": {
        "role": "backend engineer",
        "difficulty": "medium",
        "qa_block": "---\nQuestion 1: q\nAnswer: a\nIndividual Score: 7.0/10\n---",
    },
    "intent_classifier_user": {
        "transcript": "should I handle empty input?",
        "question": "Build a rate limiter.",
    },
    "clarification_user": {
        "question": "Build a rate limiter.",
        "hidden_spec": '[{"point": "burst behavior", "answer": "allow bursts up to 2x"}]',
        "transcript": "should bursts be allowed?",
    },
    "probe_user": {
        "question": "Build a rate limiter.",
        "code": "def limit(): pass",
        "language": "python",
        "transcript": "I used a sliding window.",
        "hidden_spec": '[{"point": "burst behavior", "answer": "allow bursts up to 2x"}]',
        "clarifications": "None.",
    },
    "hint_user": {
        "question": "Build a rate limiter.",
        "code": "def limit(): pass",
        "language": "python",
        "transcript": "I'm stuck.",
        "examples": "None.",
    },
}


@pytest.mark.parametrize("template_name", TEMPLATE_VARS)
def test_template_renders_with_all_vars(template_name):
    # Template.substitute is strict: a missing variable or stray `$` raises,
    # so a successful render proves the template/kwargs contract.
    rendered = render(template_name, **TEMPLATE_VARS[template_name])
    assert rendered


def test_no_jinja_syntax_left_in_templates():
    for template_name, variables in TEMPLATE_VARS.items():
        rendered = render(template_name, **variables)
        assert "{{" not in rendered, f"{template_name} contains unrendered Jinja syntax"
        assert "{%" not in rendered, f"{template_name} contains unrendered Jinja syntax"
