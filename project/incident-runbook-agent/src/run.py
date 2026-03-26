"""CLI entry point for the Incident Runbook Agent."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

project_root = str(Path(__file__).parent.parent.parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.ch05_hitl.approval import ApprovalGate, ApprovalPolicy, ConsoleApprovalProvider
from src.ch05_hitl.audit import AuditLog
from src.ch05_hitl.escalation import EscalationPolicy

# These are in the same project directory
sys.path.insert(0, str(Path(__file__).parent))

from agent import IncidentRunbookAgent
from runbook_search import RunbookIndex, get_default_runbooks
from signals import generate_incidents


async def main() -> None:
    # Setup
    index = RunbookIndex()
    index.add_runbooks(get_default_runbooks())

    policy = ApprovalPolicy(auto_approve_threshold=0.85, always_require_for=["high", "critical"])
    provider = ConsoleApprovalProvider()
    gate = ApprovalGate(policy=policy, provider=provider)
    escalation = EscalationPolicy()
    audit = AuditLog()

    agent = IncidentRunbookAgent(
        runbook_index=index,
        approval_gate=gate,
        escalation_policy=escalation,
        audit_log=audit,
        dry_run=True,
    )

    print("Incident Runbook Agent (dry-run mode)")
    print("=" * 60)

    incidents = generate_incidents()
    for alert in incidents[:5]:  # Process first 5 incidents
        print(f"\nAlert [{alert.severity.value.upper()}]: {alert.message}")
        response = await agent.process_alert(alert)
        print(f"  Runbook: {response.runbook_matched}")
        print(f"  Confidence: {response.confidence:.2f}")
        print(f"  Approval: {response.approval_decision}")
        print(f"  Executed: {response.executed} (dry_run={response.dry_run})")

    print(f"\n{'=' * 60}")
    print(audit.to_markdown())


if __name__ == "__main__":
    asyncio.run(main())
