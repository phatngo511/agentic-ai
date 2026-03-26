"""Integration test for the full agent pipeline."""

import pytest

from src.ch02.agent import DocumentAgent
from src.ch02.tool_registry import ToolRegistry
from src.ch02.tools.chunker import chunk_document
from src.ch02.tools.retriever import DocumentIndex
from src.shared.model_client import MockClient
from src.shared.types import CompletionResponse


@pytest.mark.asyncio
async def test_agent_returns_answer_with_citations():
    index = DocumentIndex(collection_name="test_integration")
    chunks = chunk_document(
        text="The capital of France is Paris. It has been the capital since the 10th century.",
        source="geography.txt",
    )
    index.add_chunks(chunks)

    mock = MockClient(
        responses=[
            CompletionResponse(
                content="The capital of France is Paris. [Source: geography.txt]",
                model="mock",
            ),
        ]
    )

    agent = DocumentAgent(
        client=mock,
        index=index,
        registry=ToolRegistry(),
    )

    response = await agent.run("What is the capital of France?")
    assert response.answer is not None
    assert "Paris" in response.answer
    assert len(response.citations) > 0
    assert response.steps_taken >= 1

    index.clear()


@pytest.mark.asyncio
async def test_agent_escalates_on_no_evidence():
    index = DocumentIndex(collection_name="test_empty")

    mock = MockClient(
        responses=[
            CompletionResponse(
                content="I don't have enough information to answer this question.",
                model="mock",
            ),
        ]
    )

    agent = DocumentAgent(
        client=mock,
        index=index,
        registry=ToolRegistry(),
    )

    response = await agent.run("What is the meaning of life?")
    assert response.confidence < 0.5

    index.clear()
