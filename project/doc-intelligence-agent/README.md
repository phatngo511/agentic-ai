# Document Intelligence Agent

A document question-answering system that retrieves evidence from ingested documents and answers with citations. Built incrementally across Chapters 2-5 of "Agentic AI for Serious Engineers."

## What it does

- Ingests PDF, markdown, and text documents
- Chunks and indexes content using vector similarity
- Retrieves relevant passages for a query
- Answers with source citations
- Escalates when evidence is insufficient (does not hallucinate)

## Two implementations

1. **Workflow** (`src/ch03/workflow.py`): Fixed pipeline. Retrieve, build context, answer. One model call. Deterministic.
2. **Agent** (`src/ch03/agent.py`): Bounded autonomy. Can refine its search, plan steps, and escalate. Multiple model calls. Adaptive.

## Running

```bash
make install
python -m code.ch02.run --docs path/to/your/documents/
python -m code.ch03.compare
make eval
```

## Evaluation

The eval harness tests 30 cases across categories: simple retrieval, technical detail, comparison, design reasoning, error handling, and no-answer (should escalate).

See `evals/rubric.yaml` for scoring criteria.

## Architecture

See `docs/architecture.md` for the system design and `docs/failure-analysis.md` for known failure surfaces.
