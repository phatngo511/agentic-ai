"""Reliability engineering for agent systems."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)


def with_retry(
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 30.0,
    retry_on: tuple[type[Exception], ...] = (Exception,),
):
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=min_wait, max=max_wait),
        retry=retry_if_exception_type(retry_on),
        reraise=True,
    )


class Checkpoint:
    """Saves and restores agent state to/from disk."""

    def __init__(self, checkpoint_dir: str | Path):
        self._dir = Path(checkpoint_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def save(self, task_id: str, state: dict[str, Any]) -> Path:
        path = self._dir / f"{task_id}.json"
        state["_checkpoint_time"] = time.time()
        path.write_text(json.dumps(state, default=str, indent=2))
        return path

    def load(self, task_id: str) -> dict[str, Any] | None:
        path = self._dir / f"{task_id}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text())

    def exists(self, task_id: str) -> bool:
        return (self._dir / f"{task_id}.json").exists()

    def delete(self, task_id: str) -> None:
        path = self._dir / f"{task_id}.json"
        if path.exists():
            path.unlink()


class IdempotencyTracker:
    """Tracks which tool calls have already been executed."""

    def __init__(self):
        self._executed: dict[str, str] = {}

    def _key(self, tool_name: str, arguments: dict[str, Any]) -> str:
        return f"{tool_name}:{json.dumps(arguments, sort_keys=True)}"

    def has_executed(self, tool_name: str, arguments: dict[str, Any]) -> bool:
        return self._key(tool_name, arguments) in self._executed

    def get_result(self, tool_name: str, arguments: dict[str, Any]) -> str | None:
        return self._executed.get(self._key(tool_name, arguments))

    def record(self, tool_name: str, arguments: dict[str, Any], result: str) -> None:
        self._executed[self._key(tool_name, arguments)] = result
