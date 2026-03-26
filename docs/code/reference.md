# Code Reference

Source code for all examples and projects. [View on GitHub](https://github.com/sunilp/agentic-ai-for-serious-engineers/tree/master/src)

## Shared (`src/shared/`)

Utilities used across all chapters and projects.

| Module | Description |
|--------|-------------|
| `model_client.py` | Thin wrapper over the LLM API: handles retries, timeouts, and response parsing |
| `types.py` | Shared data types: Message, ToolCall, ToolResult, AgentState |
| `config.py` | Environment configuration: model names, API keys, default parameters |

## Chapter 2 (`src/ch02/`)

Building blocks: tool registry, context engineering, the agent loop.

| Module | Description |
|--------|-------------|
| `tool_registry.py` | Tool registration, schema generation, dispatch, and permission checking |
| `tools/` | Individual tools: document_loader, chunker, retriever, extractor |
| `context.py` | Context window management: budget tracking, trimming, priority ordering |
| `agent.py` | Observe-think-act loop implementation |
| `run.py` | CLI entry point for Chapter 2 examples |

## Chapter 3 (`src/ch03/`)

Workflow-first architecture: fixed pipeline vs bounded agent.

| Module | Description |
|--------|-------------|
| `workflow.py` | Deterministic pipeline: retrieve, build context, answer in sequence |
| `agent.py` | Bounded agent: can refine search and escalate, with step limits |
| `state.py` | Explicit state management: tracks what the agent has tried and seen |
| `compare.py` | Side-by-side comparison: runs both implementations on the same queries |

## Chapter 4 (`src/ch04_multiagent/`)

*Coming soon*

## Chapter 5 (`src/ch05_hitl/`)

*Coming soon*

## Chapter 6 (`src/ch06/`)

Evaluation, observability, reliability, cost, and security.

| Module | Description |
|--------|-------------|
| `eval_harness.py` | Runs gold dataset through the agent, scores answers, produces failure buckets |
| `tracer.py` | Structured trace logging: captures every tool call, model call, and decision |
| `reliability.py` | Retry logic, timeout handling, fallback chains, circuit breakers |
| `cost_profiler.py` | Token counting, cost estimation, per-call and per-session tracking |
| `security.py` | Input sanitization, output validation, tool permission enforcement |
