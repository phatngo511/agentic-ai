"""Tests for escalation policies."""

from src.ch05_hitl.escalation import EscalationDecision, EscalationPolicy


def test_low_risk_high_confidence_proceeds():
    policy = EscalationPolicy()
    decision = policy.evaluate(confidence=0.8, risk_tier="low")
    assert decision == EscalationDecision.PROCEED


def test_low_risk_low_confidence_escalates():
    policy = EscalationPolicy()
    decision = policy.evaluate(confidence=0.1, risk_tier="low")
    assert decision == EscalationDecision.ESCALATE


def test_medium_risk_requires_higher_confidence():
    policy = EscalationPolicy()
    assert policy.evaluate(confidence=0.5, risk_tier="medium") == EscalationDecision.ESCALATE
    assert policy.evaluate(confidence=0.7, risk_tier="medium") == EscalationDecision.PROCEED


def test_high_risk_requires_very_high_confidence():
    policy = EscalationPolicy()
    assert policy.evaluate(confidence=0.7, risk_tier="high") == EscalationDecision.ESCALATE
    assert policy.evaluate(confidence=0.85, risk_tier="high") == EscalationDecision.PROCEED


def test_critical_always_escalates():
    policy = EscalationPolicy()
    assert policy.evaluate(confidence=1.0, risk_tier="critical") == EscalationDecision.ESCALATE


def test_too_many_autonomous_actions_halts():
    policy = EscalationPolicy()
    decision = policy.evaluate(confidence=0.9, risk_tier="high", autonomous_actions_taken=3)
    assert decision in (EscalationDecision.HALT, EscalationDecision.ESCALATE)
