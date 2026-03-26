"""Run evaluation for the Incident Runbook Agent."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

project_root = str(Path(__file__).parent.parent.parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.ch05_hitl.approval import ApprovalGate, ApprovalPolicy, MockApprovalProvider, ApprovalDecision
from src.ch05_hitl.escalation import EscalationPolicy
from src.ch05_hitl.audit import AuditLog

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from runbook_search import RunbookIndex, get_default_runbooks
from signals import Alert, Severity
from agent import IncidentRunbookAgent


async def main(output_path: str | None = None) -> None:
    # Load eval cases
    dataset_path = Path(__file__).parent / "dataset.jsonl"
    cases = []
    with open(dataset_path) as f:
        for line in f:
            if line.strip():
                cases.append(json.loads(line))

    print(f"Loaded {len(cases)} eval cases")

    # Setup agent with mock approval (auto-approve all)
    index = RunbookIndex(collection_name="eval_runbooks")
    index.add_runbooks(get_default_runbooks())

    provider = MockApprovalProvider(default_decision=ApprovalDecision.APPROVED)
    policy = ApprovalPolicy(auto_approve_threshold=0.85, always_require_for=["high", "critical"])
    gate = ApprovalGate(policy=policy, provider=provider)
    escalation = EscalationPolicy()
    audit = AuditLog()

    agent = IncidentRunbookAgent(
        runbook_index=index, approval_gate=gate,
        escalation_policy=escalation, audit_log=audit, dry_run=True,
    )

    # Run eval
    passed = 0
    failed = 0
    results = []

    for case in cases:
        alert = Alert(
            severity=Severity.ERROR,
            source="eval",
            message=case["query"],
        )
        response = await agent.process_alert(alert)

        # Score: did it match the expected runbook?
        expected = case.get("expected_runbook", "none")
        if expected == "none":
            correct = response.runbook_matched == "none"
        else:
            # Check if the matched runbook title contains key words from the expected ID
            correct = expected.replace("rb-", "").replace("-", " ") in response.runbook_matched.lower().replace("-", " ")

        if correct:
            passed += 1
            status = "PASS"
        else:
            failed += 1
            status = "FAIL"

        results.append({"case": case["id"], "status": status, "expected": expected, "got": response.runbook_matched, "confidence": response.confidence})
        print(f"  [{status}] {case['id']}: expected={expected}, got={response.runbook_matched} (conf={response.confidence:.2f})")

    print(f"\nResults: {passed}/{len(cases)} passed ({passed/len(cases)*100:.0f}%)")

    if output_path:
        Path(output_path).write_text(json.dumps(results, indent=2))
        print(f"Saved to {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", help="Output JSON path")
    args = parser.parse_args()
    asyncio.run(main(args.output))
