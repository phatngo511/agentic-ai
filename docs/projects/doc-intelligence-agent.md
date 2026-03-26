# Document Intelligence Agent

A document question-answering system that retrieves evidence from ingested documents and answers with citations. Built incrementally across Chapters 2, 3, and 6 of "Agentic AI for Serious Engineers."

## What it does

- Ingests PDF, markdown, and text documents
- Chunks and indexes content using vector similarity
- Retrieves relevant passages for a query
- Answers with source citations
- Escalates when evidence is insufficient (does not hallucinate)

## Two implementations

This project is built twice to demonstrate the core architectural tradeoff:

1. **Workflow** (`src/ch03/workflow.py`): Fixed pipeline. Retrieve, build context, answer. One model call. Deterministic.
2. **Agent** (`src/ch03/agent.py`): Bounded autonomy. Can refine its search, plan steps, and escalate. Multiple model calls. Adaptive.

Running both side by side with `make eval` shows exactly where each approach wins and loses.

## Chapter cross-references

| Chapter | What gets built |
|---------|-----------------|
| [Chapter 2: Tools, Context, and the Agent Loop](../book/02-tools-context-agent-loop.md) | Tool registry, document loader, chunker, retriever, basic agent loop |
| [Chapter 3: Workflow-First, Agent-Second](../book/03-workflow-first-agent-second.md) | Workflow implementation, bounded agent, side-by-side comparison |
| [Chapter 6: Evaluating and Hardening Agent Systems](../book/06-evaluating-and-hardening.md) | Eval harness, tracer, reliability hardening, cost profiler, security hardening |

## Running

```bash
make install
python -m src.ch02.run --docs path/to/your/documents/
python -m src.ch03.compare
make eval
```

## Evaluation

The eval harness tests 30 cases across six categories:

| Category | Cases | What it tests |
|----------|-------|---------------|
| Simple retrieval | 5 | Direct factual questions with clear answers |
| Technical detail | 5 | Specific implementation details in the docs |
| Comparison | 5 | "What is the difference between X and Y" |
| Design reasoning | 5 | Why decisions were made |
| Error handling | 5 | Ambiguous or partially-answerable questions |
| No-answer | 5 | Questions where the system should escalate rather than guess |

See `evals/rubric.yaml` for scoring criteria and `evals/gold.json` for the gold dataset.

## Architecture

The system architecture is documented in `docs/architecture.md`. Known failure surfaces are catalogued in `docs/failure-analysis.md`.

The critical failure surfaces to understand before using this in production:

- **Retrieval miss**: The answer exists in the documents but the query does not match the right chunks
- **Context overflow**: Too many retrieved chunks degrade answer quality by diluting focus
- **Hallucination on sparse evidence**: The model generates plausible-sounding but unsupported answers when retrieval is weak
- **Escalation threshold tuning**: Too conservative means unhelpful escalations; too permissive means hallucinated answers

These are not bugs to fix -- they are architectural constraints to understand and design around.
