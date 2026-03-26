"""Remediation proposal engine.

Matches alerts to runbooks and proposes specific remediation steps.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class RemediationProposal(BaseModel):
    """A proposed remediation for an incident."""

    alert_id: str
    runbook_id: str
    runbook_title: str
    confidence: float
    risk_level: str
    proposed_steps: list[dict[str, Any]]
    requires_approval: bool = False
    reasoning: str = ""
