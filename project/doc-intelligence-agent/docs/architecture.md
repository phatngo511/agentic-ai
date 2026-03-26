# Document Intelligence Agent -- Architecture

## System overview

The agent has four layers:

1. **Document layer**: Ingestion, chunking, and indexing
2. **Retrieval layer**: Vector similarity search over indexed chunks
3. **Reasoning layer**: LLM-based question answering with tool use
4. **Evaluation layer**: Automated testing and quality measurement

## Data flow

```
Documents -> Loader -> Chunker -> Vector Index
                                       |
User Query -> Retriever (query index) -> Context Pipeline -> Model -> Answer
                                                              |
                                                         Tool Registry (optional tool calls)
```

## Component responsibilities

| Component | Responsibility | Module |
|-----------|---------------|--------|
| Document Loader | Parse PDF/MD/TXT to text | `code/ch02/tools/document_loader.py` |
| Chunker | Split text into retrieval-friendly chunks | `code/ch02/tools/chunker.py` |
| Document Index | Vector storage and similarity search | `code/ch02/tools/retriever.py` |
| Context Pipeline | Assemble system prompt + evidence + query | `code/ch02/context.py` |
| Tool Registry | Validate and execute tool calls | `code/ch02/tool_registry.py` |
| Agent | Observe-think-act loop with bounded autonomy | `code/ch03/agent.py` |
| Workflow | Fixed retrieve-context-answer pipeline | `code/ch03/workflow.py` |
| Eval Harness | Run test cases and score responses | `code/ch04/eval_harness.py` |
| Tracer | Structured execution logging | `code/ch04/tracer.py` |

## Key design decisions

1. **Provider-neutral model client**: No direct OpenAI or Anthropic imports in agent code.
2. **Tools as contracts**: Every tool has a typed schema. The registry validates before execution.
3. **Permissions outside the model**: Side-effect classification and approval gates are in code, not in the system prompt.
4. **Evaluation as first-class**: The eval harness ships with the project, not as an afterthought.
