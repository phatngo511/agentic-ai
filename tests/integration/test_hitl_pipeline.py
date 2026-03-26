"""Integration test for the Incident Runbook Agent pipeline."""

import sys
from pathlib import Path

import pytest

# Add project root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Add incident runbook agent src
sys.path.insert(
    0, str(Path(__file__).parent.parent.parent / "project" / "incident-runbook-agent" / "src")
)

from agent import IncidentRunbookAgent
from runbook_search import RunbookIndex, get_default_runbooks
from signals import Alert, Severity

from src.ch05_hitl.approval import (
    ApprovalDecision,
    ApprovalGate,
    ApprovalPolicy,
    MockApprovalProvider,
)
from src.ch05_hitl.audit import AuditLog
from src.ch05_hitl.escalation import EscalationPolicy


@pytest.mark.asyncio
async def test_agent_matches_runbook_and_logs_audit():
    """Full pipeline: alert -> search -> propose -> approve -> audit."""
    index = RunbookIndex(collection_name="test_hitl")
    index.add_runbooks(get_default_runbooks())

    provider = MockApprovalProvider(default_decision=ApprovalDecision.APPROVED)
    gate = ApprovalGate(
        policy=ApprovalPolicy(auto_approve_threshold=0.85, always_require_for=["high", "critical"]),
        provider=provider,
    )
    audit = AuditLog()

    agent = IncidentRunbookAgent(
        runbook_index=index,
        approval_gate=gate,
        escalation_policy=EscalationPolicy(),
        audit_log=audit,
        dry_run=True,
    )

    alert = Alert(
        severity=Severity.CRITICAL,
        source="test",
        message="CPU usage above 95% on api-server-01 for 10 minutes",
    )
    response = await agent.process_alert(alert)

    assert response.runbook_matched != "none"
    assert response.confidence > 0.0
    assert audit.entry_count >= 2  # at least match + execute
    assert response.dry_run is True

    index.clear()


@pytest.mark.asyncio
async def test_agent_handles_no_matching_runbook():
    """When no runbook matches, agent should log and return gracefully."""
    index = RunbookIndex(collection_name="test_hitl_empty")
    # Don't add any runbooks

    provider = MockApprovalProvider()
    gate = ApprovalGate(policy=ApprovalPolicy(), provider=provider)
    audit = AuditLog()

    agent = IncidentRunbookAgent(
        runbook_index=index,
        approval_gate=gate,
        escalation_policy=EscalationPolicy(),
        audit_log=audit,
        dry_run=True,
    )

    alert = Alert(
        severity=Severity.ERROR, source="test", message="Unknown failure in unknown service"
    )
    response = await agent.process_alert(alert)

    assert response.runbook_matched == "none"
    assert response.confidence == 0.0
    assert audit.entry_count >= 1


@pytest.mark.asyncio
async def test_agent_rejects_when_approval_denied():
    """When human rejects, agent should not execute."""
    index = RunbookIndex(collection_name="test_hitl_reject")
    index.add_runbooks(get_default_runbooks())

    provider = MockApprovalProvider(default_decision=ApprovalDecision.REJECTED)
    gate = ApprovalGate(
        policy=ApprovalPolicy(auto_approve_threshold=0.99, always_require_for=["high", "critical"]),
        provider=provider,
    )
    audit = AuditLog()

    agent = IncidentRunbookAgent(
        runbook_index=index,
        approval_gate=gate,
        escalation_policy=EscalationPolicy(),
        audit_log=audit,
        dry_run=True,
    )

    alert = Alert(
        severity=Severity.CRITICAL, source="test", message="Memory at 98%, OOM killer active"
    )
    response = await agent.process_alert(alert)

    assert response.approval_decision == "rejected"
    assert response.executed is False

    index.clear()
