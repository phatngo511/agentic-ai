"""Run the evaluation harness against the Document Intelligence Agent.

Usage:
    python project/doc-intelligence-agent/evals/run_eval.py
    python project/doc-intelligence-agent/evals/run_eval.py --output report.md
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from src.ch02.agent import DocumentAgent
from src.ch02.context import ContextPipeline
from src.ch02.tool_registry import ToolRegistry
from src.ch02.tools.chunker import chunk_document
from src.ch02.tools.retriever import DocumentIndex
from src.ch04.eval_harness import EvalRunner, load_cases, load_rubric
from src.shared.config import get_model_config
from src.shared.model_client import create_client


EVAL_DIR = Path(__file__).parent
DATASET_PATH = EVAL_DIR / "dataset.jsonl"
RUBRIC_PATH = EVAL_DIR / "rubric.yaml"


async def main(output_path: str | None = None) -> None:
    cases = load_cases(DATASET_PATH)
    rubric = load_rubric(RUBRIC_PATH)
    print(f"Loaded {len(cases)} test cases and rubric ({len(rubric.criteria)} criteria)")

    config = get_model_config()
    client = create_client(
        provider=config.provider,
        api_key=config.api_key,
        model_name=config.model_name,
    )
    index = DocumentIndex(collection_name="eval_docs")
    registry = ToolRegistry()

    code_dir = Path("src")
    for py_file in code_dir.rglob("*.py"):
        text = py_file.read_text()
        chunks = chunk_document(text, source=py_file.name)
        index.add_chunks(chunks)

    agent = DocumentAgent(
        client=client,
        index=index,
        registry=registry,
        context_pipeline=ContextPipeline(),
    )

    runner = EvalRunner(rubric=rubric)
    report = await runner.run(
        cases=cases,
        agent_fn=lambda q: agent.run(q),
        run_id="baseline",
    )

    print(f"\n{report.to_markdown()}")
    if output_path:
        Path(output_path).write_text(report.to_markdown())
        print(f"\nReport saved to {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Document Intelligence Agent evaluation")
    parser.add_argument("--output", help="Output path for markdown report")
    args = parser.parse_args()
    asyncio.run(main(args.output))
