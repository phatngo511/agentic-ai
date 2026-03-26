"""Integration test for the workflow pipeline."""

import pytest

from src.ch02.tools.chunker import chunk_document
from src.ch02.tools.retriever import DocumentIndex
from src.ch03.workflow import DocumentWorkflow
from src.shared.model_client import MockClient
from src.shared.types import CompletionResponse


@pytest.mark.asyncio
async def test_workflow_single_model_call():
    index = DocumentIndex(collection_name="test_workflow")
    chunks = chunk_document(
        text="Python was created by Guido van Rossum and first released in 1991.",
        source="python.txt",
    )
    index.add_chunks(chunks)

    mock = MockClient(responses=[
        CompletionResponse(content="Python was created by Guido van Rossum. [Source: python.txt]"),
    ])

    workflow = DocumentWorkflow(client=mock, index=index)
    response = await workflow.run("Who created Python?")

    assert response.steps_taken == 1
    assert "Guido" in response.answer
    assert mock._call_count == 1

    index.clear()
