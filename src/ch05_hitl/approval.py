"""Approval gate middleware for agent systems.

An approval gate sits between the agent's decision and the action.
The agent proposes. The gate decides whether to proceed, escalate to a human,
or auto-approve based on policy.

Why this is not in the system prompt:
Prompts can be manipulated. Code-level gates cannot. The model does not get
to decide whether it needs approval -- the policy does.
"""

from __future__ import annotations

import time
from enum import Enum
from typing import Any, Protocol

from pydantic import BaseModel, Field


class ApprovalDecision(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    MODIFIED = "modified"
    TIMED_OUT = "timed_out"


class ApprovalRequest(BaseModel):
    """A request for approval of a proposed action."""
    action: str
    description: str
    confidence: float
    risk_level: str = "medium"
    context: dict[str, Any] = Field(default_factory=dict)
    timestamp: float = Field(default_factory=time.time)


class ApprovalResponse(BaseModel):
    """The result of an approval request."""
    decision: ApprovalDecision
    reviewer: str = ""
    reason: str = ""
    modifications: dict[str, Any] = Field(default_factory=dict)
    response_time_ms: float = 0.0


class ApprovalPolicy(BaseModel):
    """Configurable policy for when to auto-approve vs require human review.

    auto_approve_threshold: actions with confidence above this skip human review
    always_require_for: risk levels that always need human review
    timeout_seconds: how long to wait for human response before timing out
    timeout_action: what to do on timeout (reject or escalate)
    """
    auto_approve_threshold: float = 0.9
    always_require_for: list[str] = Field(default_factory=lambda: ["high", "critical"])
    timeout_seconds: float = 300.0
    timeout_action: str = "reject"


class ApprovalProvider(Protocol):
    """Interface for approval providers (human, mock, queue-based)."""
    async def request_approval(self, request: ApprovalRequest) -> ApprovalResponse: ...


class MockApprovalProvider:
    """Mock provider for testing. Returns configured decisions."""

    def __init__(self, default_decision: ApprovalDecision = ApprovalDecision.APPROVED):
        self._default = default_decision
        self._decisions: list[ApprovalDecision] = []
        self._call_count = 0
        self.requests: list[ApprovalRequest] = []

    def queue_decision(self, decision: ApprovalDecision) -> None:
        self._decisions.append(decision)

    async def request_approval(self, request: ApprovalRequest) -> ApprovalResponse:
        self.requests.append(request)
        if self._call_count < len(self._decisions):
            decision = self._decisions[self._call_count]
        else:
            decision = self._default
        self._call_count += 1
        return ApprovalResponse(decision=decision, reviewer="mock", reason="Mock decision")


class ConsoleApprovalProvider:
    """Interactive provider that prompts the user on stdin."""

    async def request_approval(self, request: ApprovalRequest) -> ApprovalResponse:
        start = time.monotonic()
        print(f"\n{'='*60}")
        print(f"APPROVAL REQUIRED")
        print(f"Action: {request.action}")
        print(f"Description: {request.description}")
        print(f"Confidence: {request.confidence:.2f}")
        print(f"Risk Level: {request.risk_level}")
        print(f"{'='*60}")

        while True:
            choice = input("Approve? [y]es / [n]o / [m]odify: ").strip().lower()
            if choice in ("y", "yes"):
                elapsed = (time.monotonic() - start) * 1000
                return ApprovalResponse(
                    decision=ApprovalDecision.APPROVED, reviewer="human",
                    reason="Manually approved", response_time_ms=elapsed,
                )
            elif choice in ("n", "no"):
                reason = input("Reason for rejection: ").strip()
                elapsed = (time.monotonic() - start) * 1000
                return ApprovalResponse(
                    decision=ApprovalDecision.REJECTED, reviewer="human",
                    reason=reason or "Rejected by reviewer", response_time_ms=elapsed,
                )
            elif choice in ("m", "modify"):
                modification = input("Describe modification: ").strip()
                elapsed = (time.monotonic() - start) * 1000
                return ApprovalResponse(
                    decision=ApprovalDecision.MODIFIED, reviewer="human",
                    reason="Modified by reviewer",
                    modifications={"description": modification}, response_time_ms=elapsed,
                )


class ApprovalGate:
    """The gate that sits between agent decisions and actions.

    Evaluates the policy, decides whether to auto-approve or escalate
    to the approval provider.
    """

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
                reason=f"Auto-approved: confidence {request.confidence:.2f} >= threshold {self._policy.auto_approve_threshold}",
            )

        # Otherwise, require human review
        return await self._provider.request_approval(request)
