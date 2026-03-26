"""Evaluation harness for agent systems.

If you cannot evaluate it, you do not understand it well enough to ship it.
"""

from __future__ import annotations

import json
import time
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Awaitable

from pydantic import BaseModel, Field


class EvalCase(BaseModel):
    """A single evaluation test case."""
    id: str
    query: str
    expected_answer: str
    expected_sources: list[str] = Field(default_factory=list)
    category: str = "general"
    difficulty: str = "medium"
    metadata: dict[str, Any] = Field(default_factory=dict)


class RubricCriterion(BaseModel):
    """A single scoring criterion."""
    name: str
    description: str
    weight: float = 1.0


class Rubric(BaseModel):
    """Scoring rubric for evaluation."""
    criteria: list[RubricCriterion]
    pass_threshold: float = 0.7


class FailureCategory(str, Enum):
    """Categories for why an answer failed."""
    INCORRECT = "incorrect"
    UNSUPPORTED = "unsupported"
    INCOMPLETE = "incomplete"
    HALLUCINATED = "hallucinated"
    WRONG_SOURCE = "wrong_source"
    NO_CITATION = "no_citation"
    ESCALATION_MISSED = "escalation_missed"
    FALSE_ESCALATION = "false_escalation"


class EvalResult(BaseModel):
    """Result of evaluating a single test case."""
    case_id: str
    passed: bool
    score: float
    scores: dict[str, float] = Field(default_factory=dict)
    answer: str = ""
    failure_categories: list[FailureCategory] = Field(default_factory=list)
    latency_ms: float = 0.0
    tokens_used: int = 0
    notes: str = ""


class EvalReport(BaseModel):
    """Aggregate report from an evaluation run."""
    run_id: str
    timestamp: float
    total_cases: int
    passed: int
    failed: int
    pass_rate: float
    avg_score: float
    avg_latency_ms: float
    total_tokens: int
    results: list[EvalResult]
    failure_distribution: dict[str, int] = Field(default_factory=dict)

    def to_markdown(self) -> str:
        lines = [
            f"# Evaluation Report: {self.run_id}",
            f"",
            f"**Date:** {time.strftime('%Y-%m-%d %H:%M', time.localtime(self.timestamp))}",
            f"**Cases:** {self.total_cases} | **Passed:** {self.passed} | **Failed:** {self.failed}",
            f"**Pass rate:** {self.pass_rate:.1%}",
            f"**Avg score:** {self.avg_score:.2f}",
            f"**Avg latency:** {self.avg_latency_ms:.0f}ms",
            f"**Total tokens:** {self.total_tokens}",
            f"",
            f"## Failure Distribution",
            f"",
        ]
        for cat, count in sorted(self.failure_distribution.items(), key=lambda x: -x[1]):
            lines.append(f"- {cat}: {count}")
        lines.extend([
            f"",
            f"## Results Detail",
            f"",
            f"| Case | Score | Pass | Failures | Latency |",
            f"|------|-------|------|----------|---------|",
        ])
        for r in self.results:
            failures = ", ".join(f.value for f in r.failure_categories) or "none"
            lines.append(f"| {r.case_id} | {r.score:.2f} | {'Y' if r.passed else 'N'} | {failures} | {r.latency_ms:.0f}ms |")
        return "\n".join(lines)


class EvalRunner:
    """Runs evaluation cases through an agent and scores them."""

    def __init__(self, rubric: Rubric):
        self.rubric = rubric

    async def run(
        self,
        cases: list[EvalCase],
        agent_fn: Callable[[str], Awaitable[Any]],
        run_id: str = "",
    ) -> EvalReport:
        if not run_id:
            run_id = f"eval_{int(time.time())}"

        results: list[EvalResult] = []
        for case in cases:
            start = time.monotonic()
            try:
                response = await agent_fn(case.query)
                elapsed = (time.monotonic() - start) * 1000
                scores = self._score(case, response)
                weighted_score = sum(
                    scores.get(c.name, 0.0) * c.weight
                    for c in self.rubric.criteria
                )
                passed = weighted_score >= self.rubric.pass_threshold
                failures = self._categorize_failures(case, response, scores)
                results.append(EvalResult(
                    case_id=case.id,
                    passed=passed,
                    score=weighted_score,
                    scores=scores,
                    answer=getattr(response, "answer", str(response)),
                    failure_categories=failures,
                    latency_ms=elapsed,
                    tokens_used=getattr(getattr(response, "token_usage", None), "total_tokens", 0),
                ))
            except Exception as e:
                elapsed = (time.monotonic() - start) * 1000
                results.append(EvalResult(
                    case_id=case.id,
                    passed=False,
                    score=0.0,
                    answer=f"ERROR: {e}",
                    failure_categories=[FailureCategory.INCORRECT],
                    latency_ms=elapsed,
                    notes=str(e),
                ))

        passed_count = sum(1 for r in results if r.passed)
        failure_dist: dict[str, int] = {}
        for r in results:
            for f in r.failure_categories:
                failure_dist[f.value] = failure_dist.get(f.value, 0) + 1

        return EvalReport(
            run_id=run_id,
            timestamp=time.time(),
            total_cases=len(results),
            passed=passed_count,
            failed=len(results) - passed_count,
            pass_rate=passed_count / len(results) if results else 0.0,
            avg_score=sum(r.score for r in results) / len(results) if results else 0.0,
            avg_latency_ms=sum(r.latency_ms for r in results) / len(results) if results else 0.0,
            total_tokens=sum(r.tokens_used for r in results),
            results=results,
            failure_distribution=failure_dist,
        )

    def _score(self, case: EvalCase, response: Any) -> dict[str, float]:
        answer = getattr(response, "answer", str(response)).lower()
        citations = getattr(response, "citations", [])
        expected = case.expected_answer.lower()

        scores: dict[str, float] = {}

        if expected in answer:
            scores["correctness"] = 1.0
        elif any(word in answer for word in expected.split()):
            scores["correctness"] = 0.5
        else:
            scores["correctness"] = 0.0

        if citations or "[source:" in answer:
            source_names = [c.source for c in citations] if citations else []
            if any(s in case.expected_sources for s in source_names):
                scores["grounded"] = 1.0
            elif citations:
                scores["grounded"] = 0.5
            else:
                scores["grounded"] = 0.3
        else:
            scores["grounded"] = 0.0

        if len(answer) > 20:
            scores["completeness"] = 1.0
        elif len(answer) > 5:
            scores["completeness"] = 0.5
        else:
            scores["completeness"] = 0.0

        return scores

    def _categorize_failures(
        self, case: EvalCase, response: Any, scores: dict[str, float]
    ) -> list[FailureCategory]:
        failures = []
        if scores.get("correctness", 1.0) < 0.5:
            failures.append(FailureCategory.INCORRECT)
        if scores.get("grounded", 1.0) < 0.5:
            failures.append(FailureCategory.NO_CITATION)
        escalated = getattr(response, "escalated", False)
        confidence = getattr(response, "confidence", 1.0)
        if confidence < 0.3 and not escalated:
            failures.append(FailureCategory.ESCALATION_MISSED)
        return failures


def load_cases(path: str | Path) -> list[EvalCase]:
    cases = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(EvalCase(**json.loads(line)))
    return cases


def load_rubric(path: str | Path) -> Rubric:
    import yaml
    with open(path) as f:
        data = yaml.safe_load(f)
    criteria = [RubricCriterion(**c) for c in data["criteria"]]
    return Rubric(criteria=criteria, pass_threshold=data.get("pass_threshold", 0.7))
