---
description: "Human-in-the-loop as a first-class architectural decision. Approval gates, escalation policies, audit logging, and the Incident Runbook Agent."
---

# Chapter 5: Human-in-the-Loop as Architecture

## Why this matters

Chapter 4 ended with a question: "If agents can be wrong and multi-agent systems are expensive, how do you keep a human in the loop without killing the automation value?"

Most teams answer this question wrong. They bolt on an approval step at the end of their pipeline, ask someone to click "Approve" in Slack, and call it human oversight. This is not architecture. This is an afterthought wearing the disguise of governance.

Human-in-the-loop (HITL) done poorly is worse than no human at all. It creates the appearance of oversight without the substance. A reviewer who rubber-stamps 200 agent decisions per day is not providing oversight -- they are providing liability cover. The agent runs unchecked, but now the organization believes it is supervised. When something goes wrong, the audit trail shows a human "approved" it, and the real cause -- a system designed to exhaust human attention -- goes unexamined.

HITL done well is a first-class architectural concern. It shapes the agent's action space, defines the boundaries between autonomous and supervised behavior, and creates a decision trail that is useful for debugging, compliance, and continuous improvement. The human is not a rubber stamp at the end. The human is a structural component with defined responsibilities, clear escalation paths, and bounded cognitive load.

This chapter builds the machinery for that kind of oversight. We define three primitives -- approval gates, escalation policies, and audit logs -- and wire them into a working agent that handles production incidents. The goal is not to slow the agent down. The goal is to make the agent's autonomy proportional to the risk of its actions, with human judgment applied precisely where it matters and removed precisely where it does not.

## The three primitives

HITL architecture rests on three components. Each solves a distinct problem, and together they form the control surface between autonomous agent behavior and human oversight.

### Approval gates

An approval gate sits between the agent's decision and the action. The agent proposes. The gate decides whether to proceed, route to a human, or auto-approve based on policy. This is defined in `src/ch05_hitl/approval.py`.

The critical design decision: the gate is in code, not in the prompt. The module's docstring states this explicitly:

> Prompts can be manipulated. Code-level gates cannot. The model does not get to decide whether it needs approval -- the policy does.

This distinction matters. If you tell the model "ask for approval before taking high-risk actions," you are relying on the model's judgment about what constitutes high risk. That judgment is inconsistent, manipulable through prompt injection, and impossible to audit. A code-level gate evaluates a deterministic policy against structured data. It does not matter what the model thinks about risk -- the policy decides.

The `ApprovalGate` class implements this:

```python
class ApprovalGate:
    def __init__(self, policy: ApprovalPolicy, provider: ApprovalProvider):
        self._policy = policy
        self._provider = provider

    async def check(self, request: ApprovalRequest) -> ApprovalResponse:
        # Always require for high-risk actions
        if request.risk_level in self._policy.always_require_for:
            return await self._provider.request_approval(request)

        # Auto-approve if confidence exceeds threshold
        if request.confidence >= self._policy.auto_approve_threshold:
            return ApprovalResponse(
                decision=ApprovalDecision.APPROVED,
                reviewer="auto",
                reason=f"Auto-approved: confidence {request.confidence:.2f} >= ...",
            )

        # Otherwise, require human review
        return await self._provider.request_approval(request)
```

Three paths through the gate. High-risk actions always go to a human, regardless of confidence. High-confidence, lower-risk actions auto-approve. Everything else goes to a human. No ambiguity, no model interpretation, no prompt gymnastics.

The `ApprovalPolicy` is a configuration object, not embedded logic:

```python
class ApprovalPolicy(BaseModel):
    auto_approve_threshold: float = 0.9
    always_require_for: list[str] = Field(
        default_factory=lambda: ["high", "critical"]
    )
    timeout_seconds: float = 300.0
    timeout_action: str = "reject"
```

This is tunable per deployment. A conservative organization sets `auto_approve_threshold` to 1.0 (nothing auto-approves). A mature deployment with established trust in the agent lowers it to 0.85. The threshold is not a philosophical question -- it is a knob you turn based on observed accuracy and organizational risk appetite.

### Escalation policies

Approval gates answer "should a human review this specific action?" Escalation policies answer a broader question: "given the risk tier and the agent's confidence and behavior so far, should the agent proceed, escalate, or halt entirely?"

The `EscalationPolicy` in `src/ch05_hitl/escalation.py` defines per-tier rules:

```python
rules: list[EscalationRule] = Field(default_factory=lambda: [
    EscalationRule(risk_tier=RiskTier.LOW,
                   min_confidence_to_proceed=0.3,
                   max_autonomous_actions=10),
    EscalationRule(risk_tier=RiskTier.MEDIUM,
                   min_confidence_to_proceed=0.6,
                   max_autonomous_actions=5),
    EscalationRule(risk_tier=RiskTier.HIGH,
                   min_confidence_to_proceed=0.8,
                   max_autonomous_actions=2,
                   halt_on_failure=True),
    EscalationRule(risk_tier=RiskTier.CRITICAL,
                   min_confidence_to_proceed=1.0,
                   max_autonomous_actions=0,
                   halt_on_failure=True),
])
```

Read these rules as a contract between the agent and the organization. Low-risk tasks: the agent can proceed with 30% confidence and take up to 10 autonomous actions before anyone checks in. Critical tasks: the agent never proceeds autonomously (min confidence is 1.0, which is unreachable), and it halts on any failure. The escalation tiers are not suggestions -- they are hard boundaries on autonomous behavior.

The `evaluate` method implements a three-outcome decision:

```python
def evaluate(self, confidence, risk_tier, autonomous_actions_taken=0):
    rule = self._get_rule(risk_tier)

    if rule.risk_tier == RiskTier.CRITICAL:
        return EscalationDecision.ESCALATE

    if autonomous_actions_taken >= rule.max_autonomous_actions:
        return EscalationDecision.HALT if rule.halt_on_failure \
            else EscalationDecision.ESCALATE

    if confidence >= rule.min_confidence_to_proceed:
        return EscalationDecision.PROCEED
    else:
        return EscalationDecision.ESCALATE
```

Notice the `max_autonomous_actions` check. This is the escalation policy's version of the step budget from Chapters 3 and 4. Even if the agent is confident and the risk is low, after enough autonomous actions, a human must check in. This prevents drift -- an agent that takes 50 correct actions in a row might take a 51st that is subtly wrong, and nobody has looked at the trajectory in hours.

The three decisions -- PROCEED, ESCALATE, HALT -- are deliberately distinct from the approval gate's APPROVED/REJECTED/MODIFIED. The escalation policy decides whether to ask. The approval gate handles the asking. These are separate concerns, and separating them matters for testing, configuration, and reasoning about the system's behavior.

### Audit logs

Every decision -- human and agent -- gets recorded. The `AuditLog` in `src/ch05_hitl/audit.py` is append-only. Entries cannot be modified or deleted. This is the compliance trail.

```python
class AuditEntry(BaseModel):
    entry_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:12])
    timestamp: float = Field(default_factory=time.time)
    actor: str          # "agent", "human", "system"
    action: str
    decision: str
    confidence: float = 0.0
    risk_level: str = "medium"
    approval_status: str = ""
    context: dict[str, Any] = Field(default_factory=dict)
    notes: str = ""
```

The `actor` field is the most important. It answers "who made this decision?" For every entry in the audit log, you can point to a responsible entity: the agent proposed, the system evaluated the escalation policy, the human approved or rejected. There is no ambiguity about who did what.

The `context` dictionary carries the detail needed to reconstruct the decision. Why did the agent match this runbook? What was the confidence score? What did the human see when they approved? Without this context, the audit log is a list of timestamps and decisions -- technically compliant but operationally useless.

The `AuditLog` class exposes the entries as a copy (`list(self._entries)`), never the internal list. This is a small but important detail. The audit trail should not be modifiable by downstream code that gets a reference to it. The append-only property is enforced by the interface, not by trust.

## Design guidance

### Approval stages

Not all approvals happen at the same point in the pipeline. There are three stages, and choosing the wrong one degrades either safety or speed.

**Pre-action approval.** The agent proposes an action. A human approves or rejects before anything happens. This is the safest model and the default for high-risk operations. The Incident Runbook Agent uses this for any runbook execution that the escalation policy flags. The cost: latency. The agent is blocked until a human responds. If the human is in a meeting, the incident waits.

**Post-action review.** The agent acts first and a human reviews the result after the fact. This is appropriate for actions that are reversible and low-risk. A content generation agent that drafts an email can send it to a review queue rather than blocking on approval. The cost: you need rollback capabilities. If the human rejects after the fact, the system must undo the action. Not all actions are reversible.

**Time-boxed auto-approve.** The agent proposes, waits a configurable window for human response, and proceeds if no response arrives. This is a middle ground. The `ApprovalPolicy` supports this through `timeout_seconds` and `timeout_action`:

```python
timeout_seconds: float = 300.0
timeout_action: str = "reject"
```

The default timeout action is "reject" -- if no human responds in 5 minutes, the action does not proceed. This is the conservative choice. Setting `timeout_action` to "approve" is appropriate only when the cost of inaction exceeds the cost of a wrong action -- an auto-scaling decision during a traffic spike, for example, where doing nothing is worse than doing something slightly wrong.

Choose the approval stage based on two variables: reversibility of the action and cost of delay. Irreversible actions get pre-action approval. Reversible actions can use post-action review. Time-sensitive actions with bounded downside can use time-boxed auto-approve.

### Escalation patterns

The escalation policy from `src/ch05_hitl/escalation.py` implements confidence-gated escalation. But confidence is only one dimension. There are three escalation patterns worth understanding.

**Confidence-gated.** The agent's self-reported confidence determines whether it proceeds or escalates. This is what our implementation does. The risk: confidence calibration. If the model is overconfident (and large language models frequently are), the gate is too permissive. If it is underconfident, the gate generates too many escalations and humans drown in requests.

Mitigate this by calibrating thresholds against historical accuracy. If the agent claims 0.85 confidence and is correct 60% of the time at that level, your threshold is too low. Raise it until the auto-approve accuracy is acceptable. This requires measurement -- the evaluation framework from Chapter 6 provides the tools.

**Policy-based.** Certain action types always escalate regardless of confidence. In our system, any action with risk level "high" or "critical" always goes to a human. This is not about the agent's confidence in its decision -- it is about the organization's tolerance for that category of action. A financial transaction above a threshold, a change to production infrastructure, a communication to a customer -- these escalate based on what they are, not how sure the agent is.

Policy-based escalation is the most robust pattern because it does not depend on the model's self-assessment. It depends on a taxonomy of actions that humans define and maintain. The taxonomy will need updating as the agent's action space evolves, but it is explicit and auditable.

**Anomaly-based.** The action does not match any expected pattern. This is the hardest to implement because "anomalous" requires a baseline of "normal." A practical approximation: track the distribution of actions over time and escalate when the agent proposes actions in a category that represents less than 1% of historical volume. Our implementation does not include anomaly-based escalation, but the `EscalationPolicy` is extensible.

### Uncertainty thresholds: when to ask vs when to act

The threshold between autonomous action and human escalation is the single most important parameter in a HITL system. There is no universal right answer, but there are principles.

**Start conservative, loosen with evidence.** Deploy with `auto_approve_threshold` at 0.95 or higher. If the human approves 98% of escalations, the threshold is too conservative. Lower it in small increments (0.05 at a time) and observe the rejection rate at each level. Stop when rejections hit your tolerance -- typically 2-5% for low-risk domains, under 1% for high-risk.

**Different thresholds for different action types.** Our `EscalationPolicy` does this with per-tier rules. Low-risk actions auto-proceed at 0.3 confidence. High-risk actions require 0.8. A single global threshold is too blunt.

**Never auto-approve at 1.0 confidence.** Perfect confidence does not exist in systems that interact with the real world. Our critical tier sets `min_confidence_to_proceed` to 1.0, effectively meaning "never auto-proceed." For critical actions, even theoretical perfection is not enough to skip human review.

### Reviewer interaction models

How the human receives and responds to escalation requests matters as much as when they receive them.

**Async queues.** Requests go into a queue (Slack channel, ticketing system, email). The human reviews when available. The failure mode is queue buildup -- if escalations arrive faster than humans process them, response times grow and the system degrades. Monitor queue depth and alert when it exceeds a threshold.

**Real-time.** The request surfaces immediately via a pager or notification. Appropriate for time-sensitive actions where delay has material cost. The failure mode is alert fatigue -- humans paged too frequently stop responding with care. Reserve real-time for genuinely critical decisions. The Incident Runbook Agent might use real-time for P1 incidents and async queues for P3s.

**Batch review.** Collect decisions and present them as a batch. Efficient for the human -- context-switching is minimized, and patterns across multiple decisions become visible. Particularly valuable during calibration of a new deployment, where a human reviewing 50 decisions in context can identify systematic errors that one-at-a-time review would miss.

## The working example: Incident Runbook Agent

The Incident Runbook Agent in `project/incident-runbook-agent/` ties these primitives together in a real pipeline. It receives system alerts, searches a runbook index for matching procedures, and proposes remediation -- with approval gates, escalation checks, and audit logging at every step.

### Architecture

The architecture document (`project/incident-runbook-agent/docs/architecture.md`) describes four components in a linear pipeline:

1. **Signal Ingestion** -- receives and normalizes alerts
2. **Runbook Search** -- vector similarity search over runbook symptoms
3. **Remediation Engine** -- proposes steps based on matched runbook
4. **Approval Loop** -- escalation check, then approval gate, then audit logging

The data flow is clean and traceable:

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

Every step records to the audit log. Not just the final decision -- every intermediate step. When you reconstruct an incident response after the fact, you can trace the full reasoning: which runbook matched, at what confidence, what the escalation policy decided, whether a human reviewed it, and what they decided.

### The agent pipeline

The `IncidentRunbookAgent` class in `project/incident-runbook-agent/src/agent.py` is constructed with all three HITL primitives as dependencies:

```python
class IncidentRunbookAgent:
    def __init__(
        self,
        runbook_index: Any,
        approval_gate: ApprovalGate,
        escalation_policy: EscalationPolicy,
        audit_log: AuditLog,
        dry_run: bool = True,
    ):
```

Notice `dry_run: bool = True`. The agent defaults to proposing without executing. This is a safety posture: you must explicitly opt into live execution. In the early days of deployment, the agent runs in dry-run mode, generating proposals and audit trails without taking any action. Humans review the proposals. When the accuracy is sufficient, you flip the switch. But even then, the approval gate still governs which actions auto-proceed and which require human sign-off.

### Step-by-step walkthrough

The `process_alert` method implements the full pipeline. Each step records to the audit log.

**Step 1: Search for a matching runbook.** If no match is found, the agent logs the miss and returns. It does not improvise. This is a deliberate constraint: the agent operates within the bounds of known procedures. Even "I found nothing" is recorded -- the audit log captures the full decision trajectory, including decisions not to act.

**Step 2: Check escalation policy.** The policy evaluates match confidence against the runbook's risk tier. If it returns HALT, execution stops immediately -- no approval request, no negotiation. This is the safety valve for situations where the risk is too high and the confidence is too low. The agent should not even ask a human whether to proceed. It should stop and surface the situation for investigation from scratch.

**Step 3: Request approval if needed.** If the escalation policy returns ESCALATE, or if any runbook step has `requires_approval` set, the agent constructs an `ApprovalRequest` with structured context -- the alert message, matched runbook, confidence score, and risk level -- and passes it through the `ApprovalGate`. The reviewer is not approving a black box. They have the information they need for an informed decision. If rejected (by the human or by timeout), the agent records the rejection and returns without executing.

**Step 4: Execute or dry-run.** Only after clearing both the escalation policy and the approval gate does the agent reach execution. The `dry_run` flag provides a final safeguard -- in dry-run mode, the audit trail shows exactly what the agent would have done, letting you validate decisions at scale before enabling live execution.

### Key design decisions

Four design decisions in the Incident Runbook Agent are worth calling out because they apply broadly to any HITL system.

**The agent does not decide what needs approval.** The agent proposes actions. The escalation policy and approval gate decide whether those actions need human review. The agent has no code path where it evaluates "should I ask a human about this?" That evaluation is external to the agent, enforced by the gate. This separation is fundamental. If the agent could bypass the gate, the gate provides no guarantee.

**Approval gates are in the code path, not at the boundary.** The approval check happens between the agent's decision and the execution, not at the API boundary or the UI layer. This means every code path through the agent -- including internal retries, fallback logic, and error handlers -- passes through the gate. There is no back door.

**Structured context flows to the reviewer.** The `ApprovalRequest` carries the alert message, the matched runbook, the confidence score, and the risk level. The reviewer does not need to open a separate dashboard or look up the alert to understand what they are approving. Everything needed for the decision is in the request. This reduces review time and improves review quality.

**Failure defaults to safety.** No runbook match? Log and return, do not improvise. Escalation check returns HALT? Stop, do not negotiate. Approval times out? Reject (by default), do not auto-proceed. The agent is biased toward inaction when uncertain. This is correct for operational systems where the cost of a wrong action typically exceeds the cost of a delayed action.

## When HITL is security theater

Not all human oversight is genuine oversight. There are patterns that create the appearance of human control without the substance.

### Approval fatigue

If the agent escalates 50 decisions per hour and the reviewer approves 49 of them, the reviewer stops reading the details. They start approving on reflex. The approval step is technically present, but cognitively absent. The human is not reviewing -- they are clicking a button.

This is not a human failure. It is a system design failure. The system generates too many escalations relative to the rate of genuinely uncertain decisions. The fix is to raise the auto-approve threshold so that routine decisions never reach the human. The human should see only the decisions where their judgment genuinely matters -- the edge cases, the anomalies, the actions with real downside.

Our `ApprovalPolicy` addresses this with `auto_approve_threshold`. But the threshold needs calibration based on actual review data. If your reviewer approves 95% of escalations without modification, your threshold is too conservative. Move it up until the approval rate drops to 70-80% -- a range where the human is exercising genuine judgment, not performing a ritual.

### Checkbox compliance

"Our agent system has human approval for all high-risk actions." This satisfies an audit checklist. But if the approval process is a notification that gets buried in a Slack channel, reviewed hours later by someone who has no context about the original alert, and approved because the situation has already been resolved by other means -- that is not oversight. It is paperwork.

Genuine oversight requires three things: the reviewer has the information to evaluate the decision, the review happens within a time window where the decision is still actionable, and the reviewer has the authority and mechanism to reject or modify the action. If any of these is missing, the approval process is theater.

### Opaque review context

A reviewer who sees "Approve action: execute runbook-47?" has no basis for judgment. They will either approve everything or reject everything. The `ApprovalRequest` in our implementation carries action description, alert context, confidence, and risk level. In production, add the specific remediation steps, expected impact, and rollback procedure. The quality of human oversight scales with the quality of information presented to the human.

## Cost of HITL vs value of HITL

Human oversight has real costs: latency (minutes to hours per escalation), reviewer attention (a senior SRE reviewing 50 escalations per day is not doing other work), and infrastructure overhead (queues, notifications, dashboards, timeout handlers). The question is whether the value justifies these costs.

The value comes from four sources. Error prevention -- a single caught mistake (restarting the wrong database cluster) can pay for months of review overhead. Calibration data -- every human approval or rejection is a signal for improving the agent's thresholds. Compliance -- regulated domains require a human decision trail regardless of agent accuracy. Trust building -- HITL is a ramp from pilot to production, loosening as the agent proves itself.

Think of escalation as a detection problem. True positives are escalations where the human catches a genuine error. False positives are escalations where the human approves without adding value. The optimal threshold minimizes both false positives (wasted reviewer time) and false negatives (missed errors that slip through). You can only find this threshold empirically, by measuring both rates over time and adjusting. The escalation policy and approval gate give you the knobs. The audit log gives you the measurement data.

## Failure modes

The failure analysis for the Incident Runbook Agent (`project/incident-runbook-agent/docs/failure-analysis.md`) catalogs the known failure surfaces. Let me contextualize the most important ones.

### Matching failures

A wrong runbook match is worse than no match -- no match escalates by default, but a wrong match proceeds with false confidence. Confidence scores from embedding similarity are not calibrated probabilities. Treat them as ordinal rankings and set thresholds based on observed accuracy at each score level.

### Over-escalation and under-escalation

Two sides of the same calibration problem. The `EscalationPolicy` addresses this with per-tier rules, but the boundary between risk tiers is a classification problem that policy alone does not solve. You need a risk taxonomy built with domain expertise and maintained through ongoing review.

### Stale context

By the time a human reviews an escalation, the situation may have changed. Mitigation: set a staleness threshold. If the review happens more than N minutes after the request (the `ApprovalRequest` carries a `timestamp` field), re-evaluate conditions before executing.

### Incomplete audit trails and timeout handling

If a code path skips the audit log, the compliance trail has a gap. The audit log records what it is told to record -- it cannot detect decisions that were not recorded. Mitigation: automated tests should assert that every response type has a corresponding audit trail. Review code paths to ensure no route from input to output bypasses the log.

Timeouts are a related concern. The `ApprovalPolicy` defaults to reject-on-timeout, which is conservative. The real failure mode is not the timeout itself but the lack of monitoring around it. If escalations routinely time out, reviewers are overloaded or the notification channel is broken. Track timeout rates as a system health metric.

## Building for auditability

A good audit trail answers three questions for every decision: what happened (the sequence of entries), why it happened (confidence scores, risk levels, context), and who was responsible (agent, system policy, or human). If your trail cannot answer all three, it is incomplete.

The Incident Runbook Agent creates entries at every decision point -- search, escalation, approval, execution, and errors. The `AuditLog.to_markdown()` method renders this as a human-readable table. The `to_json()` method exports for programmatic analysis. In production, you would stream entries to a centralized logging system for querying and correlation with other telemetry. But the fundamental structure -- append-only, immutable, with structured entries -- remains the same regardless of the backend.

The audit log is not just for compliance. It is a debugging tool. When the agent makes a bad decision, the trail shows you exactly where the pipeline went wrong: bad runbook match, miscalibrated escalation policy, or a human who approved something they should not have.

## Production notes

### Deploying HITL incrementally

Do not deploy with full autonomy on day one. The sequence: (1) observe mode -- the agent generates proposals without acting, humans review in batch; (2) approval-for-everything -- threshold at 1.0, validating the approval pipeline works end to end; (3) tiered autonomy -- lower thresholds for low-risk actions, monitor error rates; (4) steady state -- thresholds calibrated from observed performance, humans review only edge cases. Each stage should run long enough for statistical confidence in error rates -- dozens of decisions for rough estimates, hundreds for meaningful calibration.

### Monitoring HITL health

Track these metrics:

- **Escalation rate.** The fraction of decisions that escalate to a human. High and increasing? The agent or the policy needs recalibration. Low and decreasing? Good, or the agent is becoming too autonomous.
- **Approval rate.** The fraction of escalations that humans approve. Above 95%? The threshold is too conservative. Below 70%? The agent is proposing too many bad actions.
- **Response time.** How long humans take to respond to escalations. Increasing response times signal reviewer overload.
- **Timeout rate.** The fraction of escalations that time out without a response. A leading indicator of reviewer availability problems.
- **Override rate.** How often humans modify (not just approve or reject) agent proposals. High modification rates suggest the agent is on the right track but needs fine-tuning.

### Scaling reviewers

A single reviewer is a single point of failure. Production HITL systems need reviewer pools with load-balanced assignment. The `ApprovalProvider` protocol in `src/ch05_hitl/approval.py` abstracts the review mechanism -- replacing the `ConsoleApprovalProvider` with a queue-based provider is a configuration change, not an architectural change. The gate does not care who reviews, only that someone does.

### Testing HITL systems

The `MockApprovalProvider` in `src/ch05_hitl/approval.py` enables deterministic testing of approval flows. You can queue specific decisions and verify that the agent behaves correctly for each:

```python
mock = MockApprovalProvider()
mock.queue_decision(ApprovalDecision.REJECTED)
# Run the agent and assert it does not execute
```

Test these scenarios:

- High confidence, low risk: auto-approved, no human involved
- Low confidence, medium risk: escalated, human approves
- Any confidence, critical risk: always escalated
- Human rejects: agent does not execute
- Human modifies: agent adjusts and re-evaluates
- Timeout: agent rejects (or escalates, depending on policy)
- No runbook match: agent does not improvise
- Maximum autonomous actions exceeded: agent halts or escalates

Each scenario should assert both the behavioral outcome (did the agent execute or not?) and the audit trail (does the log contain the expected entries?).

## Evaluation

Evaluating HITL is evaluating the system's ability to make the right handoff decisions. The question is not "does the agent get the right answer?" (that is Chapter 6) but "does the agent ask a human at the right times?"

### Measuring escalation quality

Build a labeled dataset of decisions where you know whether escalation was appropriate. For each decision, label it:

- **Should escalate.** High risk, low confidence, anomalous context, or action outside the agent's demonstrated competence.
- **Should auto-proceed.** Low risk, high confidence, well-understood context, action within demonstrated competence.

Run the agent on these labeled decisions and measure precision and recall of the escalation decision. Precision: of the decisions the agent escalated, what fraction genuinely needed human review? Recall: of the decisions that needed human review, what fraction did the agent actually escalate?

Low precision means the agent wastes reviewer time. Low recall means errors slip through. Tune the escalation policy to optimize both, accepting that they trade off against each other.

### Measuring review quality and end-to-end accuracy

Not all human reviews are equal. Track decision consistency across reviewers (disagreement signals ambiguous context), decision time vs. outcome (quick approvals may indicate rubber-stamping), and decision reversal rate (how often post-hoc review concludes the human was wrong).

The ultimate metric is end-to-end accuracy of the combined system. If the human-agent system is not better than the fully autonomous alternative, the HITL overhead is pure cost. If it is not better than the fully manual alternative, the agent is not adding value. The system must outperform both endpoints to justify its complexity.

## Further reading

- **"Building Effective Agents"** -- Anthropic's engineering guide. The section on human-in-the-loop patterns provides practical guidance on approval flows and escalation design.
- **"Practices for Governing Agentic AI Systems"** -- OpenAI's whitepaper on governance of autonomous AI systems. Covers the spectrum from fully autonomous to fully supervised and the organizational structures around each.
- **"The OODA Loop and Decision Support"** -- Boyd's Observe-Orient-Decide-Act framework applied to AI systems. Useful for thinking about where human judgment adds value in the decision cycle.
- **"Ironies of Automation"** by Lisanne Bainbridge (1983) -- The classic paper on how automation changes the human's role and often makes the human's remaining tasks harder. Required reading for anyone designing HITL systems.
- **"Alert Design for Human-AI Teaming"** -- Research on how to present AI decisions to human reviewers in ways that support genuine oversight rather than reflexive approval.

## What comes next

You now have the primitives for human-agent collaboration: approval gates that enforce policy in code, escalation rules that bound autonomous behavior by risk, and audit logs that make every decision traceable. The Incident Runbook Agent shows how these primitives compose into a working system where human oversight is proportional to risk and the agent's demonstrated competence.

But there is a question we have been deferring since Chapter 3. Every chapter has mentioned confidence scores, accuracy rates, and error detection. We have built agents that propose, verify, escalate, and defer. We have assumed that we can measure their quality. But how, exactly?

How do you evaluate an agent system that makes different decisions each time it runs? How do you write tests for behavior that is stochastic? How do you detect degradation before your users do? And once you find problems, how do you harden the system against regression?

You can build, extend, and govern agent systems. But how do you know they actually work? And how do you keep them working? That is Chapter 6: Evaluating and Hardening.
