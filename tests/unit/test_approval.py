"""Tests for approval gates."""

import pytest

from src.ch05_hitl.approval import (
    ApprovalDecision,
    ApprovalGate,
    ApprovalPolicy,
    ApprovalRequest,
    MockApprovalProvider,
)


@pytest.fixture
def default_policy() -> ApprovalPolicy:
    return ApprovalPolicy(
        auto_approve_threshold=0.9,
        always_require_for=["high", "critical"],
    )


@pytest.fixture
def mock_provider() -> MockApprovalProvider:
    return MockApprovalProvider(default_decision=ApprovalDecision.APPROVED)


@pytest.mark.asyncio
async def test_auto_approve_high_confidence(default_policy, mock_provider):
    gate = ApprovalGate(policy=default_policy, provider=mock_provider)
    request = ApprovalRequest(
        action="search", description="Search docs", confidence=0.95, risk_level="low"
    )
    response = await gate.check(request)
    assert response.decision == ApprovalDecision.APPROVED
    assert response.reviewer == "auto"
    assert len(mock_provider.requests) == 0  # did not go to provider


@pytest.mark.asyncio
async def test_require_review_low_confidence(default_policy, mock_provider):
    gate = ApprovalGate(policy=default_policy, provider=mock_provider)
    request = ApprovalRequest(
        action="restart", description="Restart service", confidence=0.5, risk_level="low"
    )
    response = await gate.check(request)
    assert response.decision == ApprovalDecision.APPROVED  # mock approves
    assert len(mock_provider.requests) == 1  # went to provider


@pytest.mark.asyncio
async def test_always_require_for_high_risk(default_policy, mock_provider):
    gate = ApprovalGate(policy=default_policy, provider=mock_provider)
    request = ApprovalRequest(
        action="delete", description="Delete data", confidence=0.99, risk_level="high"
    )
    await gate.check(request)
    assert len(mock_provider.requests) == 1  # even with 0.99 confidence, high risk goes to provider


@pytest.mark.asyncio
async def test_rejection():
    provider = MockApprovalProvider(default_decision=ApprovalDecision.REJECTED)
    gate = ApprovalGate(policy=ApprovalPolicy(), provider=provider)
    request = ApprovalRequest(
        action="deploy", description="Deploy change", confidence=0.5, risk_level="medium"
    )
    response = await gate.check(request)
    assert response.decision == ApprovalDecision.REJECTED
