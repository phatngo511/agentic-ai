"""Tests for multi-agent message contracts."""

from src.ch04_multiagent.contracts import (
    MessageType,
    ReasoningRequest,
    RetrievalRequest,
    RetrievalResult,
    VerificationResult,
)
from src.shared.types import Citation


def test_retrieval_request_defaults():
    req = RetrievalRequest(query="test query")
    assert req.sender == "orchestrator"
    assert req.recipient == "retriever"
    assert req.message_type == MessageType.TASK
    assert req.query == "test query"


def test_retrieval_result_with_citations():
    citations = [Citation(source="test.txt", text="hello", relevance_score=0.9)]
    result = RetrievalResult(citations=citations, chunks_searched=5)
    assert result.sender == "retriever"
    assert len(result.citations) == 1


def test_reasoning_request_includes_citations():
    citations = [Citation(source="a.txt", text="data", relevance_score=0.8)]
    req = ReasoningRequest(query="what?", citations=citations)
    assert req.recipient == "reasoner"
    assert len(req.citations) == 1


def test_verification_result_verified():
    result = VerificationResult(verified=True, issues=[])
    assert result.verified is True
    assert result.content == "verified"


def test_verification_result_issues():
    result = VerificationResult(verified=False, issues=["Unsupported claim"])
    assert result.verified is False
    assert len(result.issues) == 1
