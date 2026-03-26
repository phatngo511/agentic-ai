"""CLI entry point for multi-agent document intelligence.

Usage:
    python -m src.ch04_multiagent.run --docs path/to/docs/ --query "What is X?"
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from src.ch02.tools.chunker import chunk_document
from src.ch02.tools.document_loader import load_document
from src.ch02.tools.retriever import DocumentIndex
from src.ch04_multiagent.orchestrator import MultiAgentOrchestrator
from src.shared.config import get_model_config
from src.shared.model_client import create_client


async def main(docs_path: str, query: str) -> None:
    config = get_model_config()
    client = create_client(provider=config.provider, api_key=config.api_key, model_name=config.model_name)

    index = DocumentIndex(collection_name="multiagent_docs")
    docs_dir = Path(docs_path)

    print(f"Indexing documents from {docs_dir}...")
    for file_path in docs_dir.iterdir():
        if file_path.suffix in (".pdf", ".md", ".txt"):
            try:
                text = await load_document(str(file_path))
                chunks = chunk_document(text, source=file_path.name)
                index.add_chunks(chunks)
                print(f"  Indexed: {file_path.name} ({len(chunks)} chunks)")
            except Exception as e:
                print(f"  Skipped: {file_path.name} ({e})")

    orchestrator = MultiAgentOrchestrator(client=client, index=index)
    response = await orchestrator.run(query)

    print(f"\nAnswer: {response.answer}")
    print(f"Confidence: {response.confidence:.2f}")
    print(f"Steps: {response.steps_taken} | Tokens: {response.token_usage.total_tokens} | Latency: {response.latency_ms:.0f}ms")
    if response.escalated:
        print(f"ESCALATED: {response.escalation_reason}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Multi-Agent Document Intelligence")
    parser.add_argument("--docs", required=True, help="Path to documents directory")
    parser.add_argument("--query", required=True, help="Query to answer")
    args = parser.parse_args()
    asyncio.run(main(args.docs, args.query))
