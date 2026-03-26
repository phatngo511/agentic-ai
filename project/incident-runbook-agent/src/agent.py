"""Incident Runbook Agent with HITL architecture.

Loop: receive alert -> search runbooks -> propose remediation ->
      check escalation policy -> request approval (if needed) ->
      execute or skip -> log audit trail
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

# Add project root to sys.path for imports
project_root = str(Path(__file__).parent.parent.parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.ch05_hitl.approval import (
    ApprovalDecision,
    ApprovalGate,
    ApprovalPolicy,
    ApprovalRequest,
    MockApprovalProvider,
)
from src.ch05_hitl.escalation import EscalationDecision, EscalationPolicy
from src.ch05_hitl.audit import AuditLog

from pydantic import BaseModel
from typing import Any


class IncidentResponse(BaseModel):
    """Response from processing a single incident."""
    alert_id: str
    alert_message: str
    runbook_matched: str
    confidence: float
    steps_proposed: int
    approval_decision: str
    executed: bool
    dry_run: bool
    processing_time_ms: float


class IncidentRunbookAgent:
    """An operational agent with HITL architecture."""

    def __init__(
        self,
        runbook_index: Any,  # RunbookIndex
        approval_gate: ApprovalGate,
        escalation_policy: EscalationPolicy,
        audit_log: AuditLog,
        dry_run: bool = True,
    ):
        self._runbook_index = runbook_index
        self._approval_gate = approval_gate
        self._escalation_policy = escalation_policy
        self._audit = audit_log
        self._dry_run = dry_run

    async def process_alert(self, alert: Any) -> IncidentResponse:
        """Process a single alert through the full pipeline."""
        start = time.monotonic()

        # Step 1: Search for matching runbook
        matches = self._runbook_index.search(alert.message, top_k=1)

        if not matches:
            self._audit.record(
                actor="agent", action="search_runbook", decision="no_match",
                confidence=0.0, risk_level=alert.severity.value,
                context={"alert_id": alert.alert_id, "message": alert.message},
            )
            elapsed = (time.monotonic() - start) * 1000
            return IncidentResponse(
                alert_id=alert.alert_id, alert_message=alert.message,
                runbook_matched="none", confidence=0.0, steps_proposed=0,
                approval_decision="skipped", executed=False, dry_run=self._dry_run,
                processing_time_ms=elapsed,
            )

        best_match = matches[0]
        runbook = best_match.runbook
        confidence = best_match.relevance_score

        self._audit.record(
            actor="agent", action="match_runbook", decision=runbook.id,
            confidence=confidence, risk_level=runbook.risk_level,
            context={"alert_id": alert.alert_id, "runbook_title": runbook.title},
        )

        # Step 2: Check escalation policy
        escalation = self._escalation_policy.evaluate(
            confidence=confidence, risk_tier=runbook.risk_level,
        )

        if escalation == EscalationDecision.HALT:
            self._audit.record(
                actor="system", action="escalation_check", decision="halt",
                confidence=confidence, risk_level=runbook.risk_level,
                notes="Escalation policy halted execution",
            )
            elapsed = (time.monotonic() - start) * 1000
            return IncidentResponse(
                alert_id=alert.alert_id, alert_message=alert.message,
                runbook_matched=runbook.title, confidence=confidence,
                steps_proposed=len(runbook.steps), approval_decision="halted",
                executed=False, dry_run=self._dry_run, processing_time_ms=elapsed,
            )

        # Step 3: Request approval if needed
        needs_approval = (
            escalation == EscalationDecision.ESCALATE
            or any(s.requires_approval for s in runbook.steps)
        )

        approval_decision = "auto_approved"
        if needs_approval:
            approval_req = ApprovalRequest(
                action=f"Execute runbook: {runbook.title}",
                description=f"Alert: {alert.message}\nRunbook: {runbook.title}\nSteps: {len(runbook.steps)}",
                confidence=confidence,
                risk_level=runbook.risk_level,
            )
            approval_resp = await self._approval_gate.check(approval_req)
            approval_decision = approval_resp.decision.value

            self._audit.record(
                actor=approval_resp.reviewer or "system",
                action="approval_check",
                decision=approval_decision,
                confidence=confidence,
                risk_level=runbook.risk_level,
                approval_status=approval_decision,
                context={"reason": approval_resp.reason},
            )

            if approval_resp.decision == ApprovalDecision.REJECTED:
                elapsed = (time.monotonic() - start) * 1000
                return IncidentResponse(
                    alert_id=alert.alert_id, alert_message=alert.message,
                    runbook_matched=runbook.title, confidence=confidence,
                    steps_proposed=len(runbook.steps), approval_decision="rejected",
                    executed=False, dry_run=self._dry_run, processing_time_ms=elapsed,
                )

        # Step 4: Execute (or dry-run)
        executed = not self._dry_run
        self._audit.record(
            actor="agent", action="execute_runbook",
            decision="dry_run" if self._dry_run else "executed",
            confidence=confidence, risk_level=runbook.risk_level,
            context={"runbook_id": runbook.id, "steps": len(runbook.steps), "dry_run": self._dry_run},
        )

        elapsed = (time.monotonic() - start) * 1000
        return IncidentResponse(
            alert_id=alert.alert_id, alert_message=alert.message,
            runbook_matched=runbook.title, confidence=confidence,
            steps_proposed=len(runbook.steps), approval_decision=approval_decision,
            executed=executed, dry_run=self._dry_run, processing_time_ms=elapsed,
        )
