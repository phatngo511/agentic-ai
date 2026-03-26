"""State management for agent systems.

Three kinds of state in an agent system:
1. Session state: the conversation so far (multi-turn context)
2. Task state: the current task's progress (steps taken, budget, intermediate results)
3. Working memory: information the agent has gathered during this task
"""

from __future__ import annotations

import time
import uuid
from typing import Any

from pydantic import BaseModel, Field


class SessionState(BaseModel):
    """Tracks the conversation across multiple queries."""

    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    history: list[dict[str, str]] = Field(default_factory=list)
    created_at: float = Field(default_factory=time.time)

    @property
    def turn_count(self) -> int:
        return len(self.history) // 2

    def add_query(self, query: str) -> None:
        self.history.append({"role": "user", "content": query})

    def add_answer(self, answer: str) -> None:
        self.history.append({"role": "assistant", "content": answer})


class TaskState(BaseModel):
    """Tracks a single task's execution progress."""

    task_id: str
    query: str
    max_steps: int = 10
    steps: list[dict[str, Any]] = Field(default_factory=list)
    result: str | None = None
    confidence: float = 0.0
    _complete: bool = False

    model_config = {"arbitrary_types_allowed": True}

    @property
    def is_complete(self) -> bool:
        return self._complete

    @property
    def budget_remaining(self) -> int:
        return max(0, self.max_steps - len(self.steps))

    @property
    def is_over_budget(self) -> bool:
        return len(self.steps) >= self.max_steps

    def add_step(self, action: str, params: dict[str, Any], result: str) -> None:
        self.steps.append(
            {
                "action": action,
                "params": params,
                "result": result,
                "timestamp": time.time(),
            }
        )

    def mark_complete(self, result: str, confidence: float) -> None:
        self.result = result
        self.confidence = confidence
        self._complete = True
