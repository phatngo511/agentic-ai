# Incident Runbook Agent

An operational agent that inspects system signals, searches runbooks for matching procedures, proposes remediation steps, and requests human approval before executing any action.

Built as the second end-to-end project for "Agentic AI for Serious Engineers," demonstrating human-in-the-loop architecture in practice.

## What it does

- Ingests simulated system alerts (CPU, disk, memory, latency, errors, certificates, etc.)
- Searches a runbook index for matching procedures using vector similarity
- Proposes remediation steps with confidence scores
- Checks escalation policy (proceed / escalate / halt based on risk tier)
- Requests human approval for high-risk or low-confidence actions
- Logs every decision in an immutable audit trail
- Supports dry-run mode (propose only, never execute)

## Running

```bash
# From the repo root
python project/incident-runbook-agent/src/run.py
```

## Evaluation

```bash
python project/incident-runbook-agent/evals/run_eval.py
```

25 incident scenarios across categories: correct triage, no-runbook cases, false alarms, approximate matches, and escalation scenarios.

## Architecture

See `docs/architecture.md` for the system design and `docs/failure-analysis.md` for known failure surfaces.
