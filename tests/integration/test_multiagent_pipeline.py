"""Integration test for multi-agent pipeline."""

import pytest

from src.ch02.tools.chunker import chunk_document
from src.ch02.tools.retriever import DocumentIndex
from src.ch04_multiagent.orchestrator import MultiAgentOrchestrator
from src.shared.model_client import MockClient
from src.shared.types import CompletionResponse


@pytest.mark.asyncio
async def test_full_multiagent_pipeline():
    index = DocumentIndex(collection_name="test_multi_integration")
    chunks = chunk_document(
        text="Machine learning is a subset of AI. Deep learning uses neural networks with many layers.",
        source="ml_intro.txt",
    )
    index.add_chunks(chunks)

    mock = MockClient(responses=[
        CompletionResponse(content="Machine learning is a subset of AI. [Source: ml_intro.txt]"),
        CompletionResponse(content='{"verified": true, "issues": []}'),
    ])

    orchestrator = MultiAgentOrchestrator(client=mock, index=index)
    response = await orchestrator.run("What is machine learning?")

    assert response.answer is not None
    assert len(response.citations) > 0
    assert response.steps_taken >= 3
    assert response.token_usage.total_tokens >= 0

    index.clear()
