"""Escalation policy engine.

Decides whether an agent should proceed, escalate to a human, or halt.
Based on confidence scores, risk tiers, and action counts.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class EscalationDecision(str, Enum):
    PROCEED = "proceed"
    ESCALATE = "escalate"
    HALT = "halt"


class RiskTier(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EscalationRule(BaseModel):
    """A single escalation rule for a risk tier."""
    risk_tier: RiskTier
    min_confidence_to_proceed: float
    max_autonomous_actions: int
    halt_on_failure: bool = False


class EscalationPolicy(BaseModel):
    """Configurable escalation policy with per-tier rules."""

    rules: list[EscalationRule] = Field(default_factory=lambda: [
        EscalationRule(risk_tier=RiskTier.LOW, min_confidence_to_proceed=0.3, max_autonomous_actions=10),
        EscalationRule(risk_tier=RiskTier.MEDIUM, min_confidence_to_proceed=0.6, max_autonomous_actions=5),
        EscalationRule(risk_tier=RiskTier.HIGH, min_confidence_to_proceed=0.8, max_autonomous_actions=2, halt_on_failure=True),
        EscalationRule(risk_tier=RiskTier.CRITICAL, min_confidence_to_proceed=1.0, max_autonomous_actions=0, halt_on_failure=True),
    ])

    def evaluate(
        self,
        confidence: float,
        risk_tier: str,
        autonomous_actions_taken: int = 0,
    ) -> EscalationDecision:
        """Evaluate whether to proceed, escalate, or halt."""
        rule = self._get_rule(risk_tier)

        # Critical always escalates (min_confidence is 1.0, which is unreachable)
        if rule.risk_tier == RiskTier.CRITICAL:
            return EscalationDecision.ESCALATE

        # Too many autonomous actions
        if autonomous_actions_taken >= rule.max_autonomous_actions:
            return EscalationDecision.HALT if rule.halt_on_failure else EscalationDecision.ESCALATE

        # Confidence check
        if confidence >= rule.min_confidence_to_proceed:
            return EscalationDecision.PROCEED
        else:
            return EscalationDecision.ESCALATE

    def _get_rule(self, risk_tier: str) -> EscalationRule:
        for rule in self.rules:
            if rule.risk_tier.value == risk_tier:
                return rule
        # Default to medium if tier not found
        return EscalationRule(
            risk_tier=RiskTier.MEDIUM,
            min_confidence_to_proceed=0.6,
            max_autonomous_actions=5,
        )
