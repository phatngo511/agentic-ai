"""Tests for the multi-agent orchestrator."""

import pytest

from src.ch02.tools.chunker import chunk_document
from src.ch02.tools.retriever import DocumentIndex
from src.ch04_multiagent.orchestrator import MultiAgentOrchestrator
from src.shared.model_client import MockClient
from src.shared.types import CompletionResponse


@pytest.mark.asyncio
async def test_orchestrator_returns_answer():
    index = DocumentIndex(collection_name="test_orchestrator")
    chunks = chunk_document(
        text="Python was created by Guido van Rossum in 1991.", source="python.txt"
    )
    index.add_chunks(chunks)

    mock = MockClient(
        responses=[
            # Reasoner response
            CompletionResponse(
                content="Python was created by Guido van Rossum. [Source: python.txt]"
            ),
            # Verifier response
            CompletionResponse(content='{"verified": true, "issues": []}'),
        ]
    )

    orchestrator = MultiAgentOrchestrator(client=mock, index=index)
    response = await orchestrator.run("Who created Python?")

    assert response.answer is not None
    assert "Guido" in response.answer
    assert response.steps_taken >= 3  # retrieve + reason + verify
    index.clear()


@pytest.mark.asyncio
async def test_orchestrator_retries_on_verification_failure():
    index = DocumentIndex(collection_name="test_orch_retry")
    chunks = chunk_document(text="The sky is blue.", source="facts.txt")
    index.add_chunks(chunks)

    mock = MockClient(
        responses=[
            # First reasoning
            CompletionResponse(content="The sky is green."),
            # First verification (fails)
            CompletionResponse(content='{"verified": false, "issues": ["Sky color is wrong"]}'),
            # Second reasoning (corrected)
            CompletionResponse(content="The sky is blue. [Source: facts.txt]"),
            # Second verification (passes)
            CompletionResponse(content='{"verified": true, "issues": []}'),
        ]
    )

    orchestrator = MultiAgentOrchestrator(client=mock, index=index, max_verification_rounds=2)
    response = await orchestrator.run("What color is the sky?")

    assert response.steps_taken >= 5  # retrieve + reason + verify + re-reason + re-verify
    index.clear()
