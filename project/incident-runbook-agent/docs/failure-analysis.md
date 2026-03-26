# Incident Runbook Agent -- Failure Analysis

## Known failure surfaces

### Matching failures
- **Semantic gap**: Alert uses different terminology than runbook symptoms
- **No matching runbook**: Incident type has no predefined procedure
- **Wrong match**: Alert matches a runbook for a different issue (e.g., disk alert matches memory runbook)

### Escalation failures
- **Over-escalation**: Agent escalates routine issues that could be auto-resolved
- **Under-escalation**: Agent proceeds autonomously on high-risk actions
- **Threshold misconfiguration**: Escalation policy thresholds do not match organizational risk appetite

### Approval failures
- **Approval fatigue**: Too many approval requests cause reviewers to rubber-stamp
- **Timeout handling**: Human does not respond within timeout window
- **Stale context**: By the time human reviews, the situation has changed

### Audit failures
- **Incomplete trail**: Not all decisions are logged (code path skips audit)
- **Missing context**: Audit entries lack enough context to reconstruct the decision

## Mitigation strategies

| Failure | Mitigation | Implemented? |
|---------|-----------|--------------|
| Semantic gap | Multiple retrieval strategies, query expansion | Partial (single query) |
| No matching runbook | Explicit "no match" handling with escalation | Yes |
| Wrong match | Confidence threshold + escalation policy | Yes |
| Over-escalation | Tunable per-tier thresholds | Yes |
| Under-escalation | Critical tier always escalates | Yes |
| Approval fatigue | Auto-approve for high-confidence, low-risk | Yes |
| Timeout | Configurable timeout with reject-on-timeout | Yes |
| Incomplete trail | Audit calls at every decision point | Yes |
