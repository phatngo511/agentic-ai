"""CLI entry point for the Chapter 2 document intelligence agent.

Usage:
    python -m code.ch02.run --docs path/to/docs/ --query "What is X?"
    python -m code.ch02.run --docs path/to/docs/  # interactive mode
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from code.ch02.agent import DocumentAgent
from code.ch02.context import ContextPipeline
from code.ch02.tool_registry import ToolRegistry
from code.ch02.tools.chunker import chunk_document
from code.ch02.tools.document_loader import load_document
from code.ch02.tools.retriever import DocumentIndex
from code.shared.config import get_model_config
from code.shared.model_client import create_client


async def main(docs_path: str, query: str | None = None) -> None:
    config = get_model_config()
    client = create_client(
        provider=config.provider,
        api_key=config.api_key,
        model_name=config.model_name,
    )

    index = DocumentIndex()
    registry = ToolRegistry()
    docs_dir = Path(docs_path)

    print(f"Indexing documents from {docs_dir}...")
    for file_path in docs_dir.iterdir():
        if file_path.suffix in (".pdf", ".md", ".txt", ".markdown"):
            try:
                text = await load_document(str(file_path))
                chunks = chunk_document(text, source=file_path.name)
                index.add_chunks(chunks)
                print(f"  Indexed: {file_path.name} ({len(chunks)} chunks)")
            except Exception as e:
                print(f"  Skipped: {file_path.name} ({e})")

    agent = DocumentAgent(
        client=client,
        index=index,
        registry=registry,
        context_pipeline=ContextPipeline(),
    )

    if query:
        response = await agent.run(query)
        _print_response(response)
    else:
        print("\nDocument Intelligence Agent ready. Type 'quit' to exit.\n")
        while True:
            try:
                user_query = input("Query: ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if user_query.lower() in ("quit", "exit", "q"):
                break
            if not user_query:
                continue
            response = await agent.run(user_query)
            _print_response(response)
            print()


def _print_response(response) -> None:
    print(f"\nAnswer: {response.answer}")
    print(f"\nConfidence: {response.confidence:.2f}")
    if response.escalated:
        print(f"ESCALATED: {response.escalation_reason}")
    if response.citations:
        print(f"\nSources ({len(response.citations)}):")
        for c in response.citations[:3]:
            print(f"  - {c.source} (relevance: {c.relevance_score:.2f})")
    print(f"\nSteps: {response.steps_taken} | Tokens: {response.token_usage.total_tokens} | Latency: {response.latency_ms:.0f}ms")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Document Intelligence Agent")
    parser.add_argument("--docs", required=True, help="Path to documents directory")
    parser.add_argument("--query", help="Single query (omit for interactive mode)")
    args = parser.parse_args()
    asyncio.run(main(args.docs, args.query))
