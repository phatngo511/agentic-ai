"""Tests for the evaluation harness."""

import pytest

from code.ch04.eval_harness import EvalCase, EvalResult, EvalRunner, Rubric, RubricCriterion


@pytest.fixture
def sample_rubric() -> Rubric:
    return Rubric(
        criteria=[
            RubricCriterion(name="correctness", description="Is the answer factually correct?", weight=0.4),
            RubricCriterion(name="grounded", description="Does the answer cite sources?", weight=0.3),
            RubricCriterion(name="completeness", description="Does the answer address the full question?", weight=0.3),
        ]
    )


@pytest.fixture
def sample_cases() -> list[EvalCase]:
    return [
        EvalCase(
            id="tc1",
            query="What is the capital of France?",
            expected_answer="Paris",
            expected_sources=["geography.txt"],
        ),
        EvalCase(
            id="tc2",
            query="When was Python created?",
            expected_answer="1991",
            expected_sources=["python.txt"],
        ),
    ]


def test_eval_result_pass_rate():
    results = [
        EvalResult(case_id="tc1", passed=True, score=0.9, scores={}),
        EvalResult(case_id="tc2", passed=False, score=0.3, scores={}),
        EvalResult(case_id="tc3", passed=True, score=0.8, scores={}),
    ]
    pass_rate = sum(1 for r in results if r.passed) / len(results)
    assert pass_rate == pytest.approx(2 / 3)


def test_rubric_total_weight(sample_rubric: Rubric):
    total = sum(c.weight for c in sample_rubric.criteria)
    assert total == pytest.approx(1.0)


def test_eval_case_has_required_fields(sample_cases: list[EvalCase]):
    for case in sample_cases:
        assert case.id
        assert case.query
        assert case.expected_answer
