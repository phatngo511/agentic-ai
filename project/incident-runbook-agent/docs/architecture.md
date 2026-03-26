# Incident Runbook Agent -- Architecture

## System overview

Four components in a linear pipeline with approval gates:

1. **Signal Ingestion**: Receives and normalizes system alerts
2. **Runbook Search**: Vector similarity search over runbook symptoms
3. **Remediation Engine**: Proposes steps based on matched runbook
4. **Approval Loop**: Escalation check + human approval gate + audit logging

## Data flow

```
Alert -> Runbook Search -> Match Found? -> Escalation Policy
                                                |
                                          PROCEED / ESCALATE / HALT
                                                |
                                          Approval Gate
                                                |
                                     APPROVE / REJECT / MODIFY
                                                |
                                          Execute (or Dry-Run)
                                                |
                                          Audit Log
```

## Component responsibilities

| Component | Responsibility | Module |
|-----------|---------------|--------|
| Signal Ingestion | Parse alerts into typed Alert models | `src/signals.py` |
| Runbook Index | Vector search over runbook symptoms | `src/runbook_search.py` |
| Escalation Policy | Decide proceed/escalate/halt per risk tier | `src/ch05_hitl/escalation.py` |
| Approval Gate | Auto-approve or route to human reviewer | `src/ch05_hitl/approval.py` |
| Audit Log | Record every decision immutably | `src/ch05_hitl/audit.py` |
| Agent | Orchestrate the full pipeline | `src/agent.py` |

## Key design decisions

1. **Dry-run by default**: The agent proposes but never executes unless explicitly configured. Safety first.
2. **Approval gates in code, not prompts**: The escalation policy is enforced by code, not by telling the model to "be careful."
3. **Audit everything**: Every decision (agent and human) is logged. This is the compliance trail.
4. **Runbook-driven**: The agent does not invent remediation steps. It matches known procedures. This bounds the action space.
