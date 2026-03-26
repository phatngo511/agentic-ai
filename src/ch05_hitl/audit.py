"""Structured audit logging for agent decisions.

Every decision -- human and agent -- gets recorded. No exceptions.
This is not optional logging. This is the compliance trail.
"""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class AuditEntry(BaseModel):
    """A single audit log entry. Immutable after creation."""
    entry_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:12])
    timestamp: float = Field(default_factory=time.time)
    actor: str  # "agent", "human", "system"
    action: str
    decision: str
    confidence: float = 0.0
    risk_level: str = "medium"
    approval_status: str = ""
    context: dict[str, Any] = Field(default_factory=dict)
    notes: str = ""


class AuditLog:
    """Append-only audit log. Entries cannot be modified or deleted."""

    def __init__(self):
        self._entries: list[AuditEntry] = []

    def record(
        self,
        actor: str,
        action: str,
        decision: str,
        confidence: float = 0.0,
        risk_level: str = "medium",
        approval_status: str = "",
        context: dict[str, Any] | None = None,
        notes: str = "",
    ) -> AuditEntry:
        """Record a new audit entry. Returns the created entry."""
        entry = AuditEntry(
            actor=actor,
            action=action,
            decision=decision,
            confidence=confidence,
            risk_level=risk_level,
            approval_status=approval_status,
            context=context or {},
            notes=notes,
        )
        self._entries.append(entry)
        return entry

    @property
    def entries(self) -> list[AuditEntry]:
        """Return a copy of all entries. The original list is not exposed."""
        return list(self._entries)

    @property
    def entry_count(self) -> int:
        return len(self._entries)

    def to_json(self) -> str:
        """Export the full log as JSON."""
        return json.dumps(
            [e.model_dump() for e in self._entries],
            indent=2,
            default=str,
        )

    def to_markdown(self) -> str:
        """Export the log as a markdown table."""
        lines = [
            "# Audit Log",
            "",
            f"**Entries:** {len(self._entries)}",
            "",
            "| Time | Actor | Action | Decision | Confidence | Risk | Approval |",
            "|------|-------|--------|----------|------------|------|----------|",
        ]
        for e in self._entries:
            ts = time.strftime("%H:%M:%S", time.localtime(e.timestamp))
            lines.append(
                f"| {ts} | {e.actor} | {e.action} | {e.decision} | "
                f"{e.confidence:.2f} | {e.risk_level} | {e.approval_status} |"
            )
        return "\n".join(lines)

    def save(self, path: str | Path) -> None:
        """Save the log to a JSON file."""
        Path(path).write_text(self.to_json())
