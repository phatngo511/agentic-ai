# Chapter 2: Tools, Context, and the Agent Loop

## Why this matters

Chapter 1 gave you a vocabulary. This chapter gives you the building blocks. By the end, you will have a working tool-using agent -- not a framework wrapper, but code you wrote, understand, and can modify without consulting documentation for a library you did not choose.

The reason to build from components rather than reaching for a framework is not ideology. It is engineering. When your agent hallucinates a tool argument at 2 AM, you need to know exactly what sits between the model's output and the function call. When your context window fills up and the model starts ignoring evidence, you need to know exactly how that context was assembled. When costs spike because the agent is making unnecessary tool calls, you need to see the loop that drives those calls.

Frameworks abstract away exactly the things you need to see when things break. This chapter keeps them visible.

## An LLM primer for systems engineers

If you have used LLMs through an API, you know the basic interaction: you send messages, you get a completion. But to build systems on top of them, you need to understand a few properties that are not obvious from the API documentation.

**Models are stateless.** Every API call is independent. The model has no memory of previous calls. What feels like a conversation is your code sending the full conversation history with every request. This means you control the model's memory -- it sees exactly what you put in the message list and nothing more.

**Models are probabilistic.** Even at temperature zero, model outputs are not perfectly deterministic across providers and versions. Your system must handle variation in output format, reasoning quality, and tool-call structure. Any code path that assumes exact string matching against model output is fragile.

**Context is finite and expensive.** Every token in the input costs money and occupies space in a fixed-size window. Context engineering -- deciding what goes in and what stays out -- is not a nicety. It is a core system design problem. A model with the right 2,000 tokens of context will outperform the same model with 20,000 tokens of marginally relevant noise.

**Tool calling is structured output.** When a model "calls a tool," it is actually generating a JSON object that your code parses and executes. The model does not run the tool. It produces a structured request, and your code decides whether and how to execute it. This distinction matters for security, validation, and testing.

### Provider neutrality

The first design decision in our system is provider neutrality. Look at `src/shared/model_client.py`. The `ModelClient` abstract class defines a single method:

```python
async def complete(self, request: CompletionRequest) -> CompletionResponse
```

Every model interaction in the system goes through this interface. The `OpenAIClient` and `AnthropicClient` implement it for their respective APIs. The `MockClient` implements it for testing. The `create_client` factory function picks the right one based on configuration.

Why this matters in practice:

- When you need to switch from GPT-4o to Claude for cost or quality reasons, you change a config value, not your agent code.
- When you need to test your agent logic without making API calls (or spending money), you use the `MockClient` with canned responses.
- When you need to add cost tracking or rate limiting, you add it in one place -- the client -- not in every agent that makes model calls.

The rest of the codebase never imports `openai` or `anthropic` directly. Provider-specific formatting lives in private functions inside the client module: `_to_openai_message`, `_to_anthropic_tool`, and their counterparts. This is not over-engineering. It is the minimum abstraction needed to keep your agent logic portable and testable.

### Typed contracts

All data flowing through the system uses the types defined in `src/shared/types.py`. These are Pydantic models: `Message`, `ToolSchema`, `ToolCall`, `ToolResult`, `CompletionRequest`, `CompletionResponse`, `AgentResponse`.

Two types deserve special attention.

`ToolSchema` defines what a tool is -- its name, description, parameters, side effect classification, and whether it requires approval:

```python
class ToolSchema(BaseModel):
    name: str
    description: str
    parameters: list[ToolParameter] = Field(default_factory=list)
    side_effect: SideEffect = SideEffect.READ
    requires_approval: bool = False
```

`SideEffect` classifies what a tool does to the world:

```python
class SideEffect(str, Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
```

This classification is not for documentation. It drives permission checking, audit logging, and approval gates. A tool marked `READ` can be retried freely. A tool marked `WRITE` needs more care. A tool marked `DELETE` needs explicit approval. These properties are declared in code, not left to the model to decide at runtime.

## Tools as contracts

A tool in our system is not just a function. It is a contract with three parts: a schema that declares what the tool does and accepts, a handler that implements the behavior, and a registry that validates calls and logs execution.

### The tool registry

The `ToolRegistry` in `src/ch02/tool_registry.py` is the gatekeeper for all tool execution. It exists because of four specific failure modes:

1. **The model calls a tool that does not exist.** Maybe it hallucinated a tool name. Maybe the tool list changed since the system prompt was written. Without the registry, this is an unhandled `KeyError`. With the registry, it is a structured error result that the agent can interpret and recover from.

2. **The model passes wrong arguments.** It omits a required parameter, invents a parameter name, or passes the wrong type. The registry validates arguments against the schema before execution. The error message tells the model exactly what went wrong: which arguments are missing, what was expected.

3. **The tool raises an exception.** A file does not exist, a network call times out, a parsing library throws. The registry catches the exception, logs it, and returns a `ToolResult` with `success=False` and a descriptive error. The agent loop never crashes because of a tool failure.

4. **You need an audit trail.** Every tool execution is logged with the tool name, arguments, success status, timing, and timestamp. When something breaks in production, you can reconstruct exactly what the agent did and in what order.

The key design choice: `execute()` never raises exceptions for tool-level errors. It always returns a `ToolResult`. This is intentional. The agent loop should handle errors as data, not as exceptions that break the control flow. When a tool fails, the model gets a message saying what went wrong, and it can decide whether to retry, try a different approach, or give up. This is fundamentally different from a system where tool errors crash the loop and require external retry logic.

### The four document tools

The Document Intelligence Agent has four tools, each in its own module under `src/ch02/tools/`.

**Document Loader** (`document_loader.py`): Ingests PDF, Markdown, and plain text files. Each format has its own parsing path. The tool returns raw text -- no interpretation, no summarization. Failure mode: unsupported formats raise a clear error rather than silently producing garbage.

**Chunker** (`chunker.py`): Splits document text into overlapping chunks for retrieval. The chunking strategy is paragraph-aware: it tries to break at paragraph boundaries rather than at arbitrary character positions. The overlap parameter (default 200 characters) ensures that information near chunk boundaries is not lost. This is a direct mitigation for the chunk-boundary failure mode documented in `project/doc-intelligence-agent/docs/failure-analysis.md`.

**Retriever** (`retriever.py`): Wraps a vector index (ChromaDB) to find chunks relevant to a query. Returns `Citation` objects with source attribution and relevance scores. The `DocumentIndex` class manages the lifecycle of the vector collection, including adding chunks and clearing the index.

**Extractor** (`extractor.py`): Uses an LLM to pull structured fields from text. This is the one tool that makes its own model call. It takes raw text and a comma-separated list of field names, and returns a JSON object. The extraction prompt explicitly instructs the model to use `null` for fields it cannot determine -- a grounding technique that reduces hallucination in structured extraction tasks.

Notice that each tool module defines both a `SCHEMA` constant (the contract) and a handler function (the implementation). The schema declares the tool's interface -- name, description, parameters, and side effect classification. The handler is the async function that does the work. Registration connects them:

```python
registry.register(document_loader.SCHEMA, document_loader.load_document)
registry.register(chunker.SCHEMA, chunker.chunk_document_tool)
```

This separation means you can read the tool's contract without reading its implementation, and you can test the implementation without the registry infrastructure.

## Context engineering

Context engineering is the most underrated skill in building LLM-powered systems. The model's output quality is bounded by the quality of its input. A model with poorly assembled context will produce poor answers regardless of how good the model is.

The `ContextPipeline` in `src/ch02/context.py` handles context assembly. It takes three inputs -- a query, a list of citations (retrieved evidence), and optional conversation history -- and produces a list of `Message` objects ready for the model.

### The system prompt

The system prompt establishes the model's role, its rules of engagement, and its constraints:

```
You are a document intelligence assistant. Your job is to answer questions
based strictly on the provided evidence.

Rules:
- Only use information from the provided document excerpts.
- Cite your sources using [Source: filename] notation.
- If the evidence does not contain enough information to answer confidently,
  say so explicitly. Do not guess or use your training knowledge.
- If you are uncertain, explain what you found and what is missing.
- Be precise and concise. Engineers are reading this.
```

Every sentence here addresses a specific failure mode:

- "based strictly on the provided evidence" -- mitigates hallucination from training data
- "Cite your sources" -- enables verification and grounding assessment
- "say so explicitly. Do not guess" -- prevents confident wrong answers when evidence is insufficient
- "explain what you found and what is missing" -- produces useful partial answers instead of refusals

A system prompt is not a wish list. It is an instruction set for a probabilistic system that will follow instructions imperfectly. Each instruction should be testable: you should be able to write an eval case that checks whether the model followed it.

### Evidence formatting

When citations are available, the pipeline formats them into numbered excerpts with source attribution and relevance scores:

```
[Excerpt 1] (Source: architecture.md, relevance: 0.87)
The agent has four layers: document, retrieval, reasoning, evaluation.

[Excerpt 2] (Source: failure-analysis.md, relevance: 0.72)
Chunk boundary: The answer spans two chunks and neither chunk alone is sufficient.
```

When no citations are found, the pipeline includes an explicit note:

```
No relevant document excerpts were found for this query.
If you cannot answer without evidence, say so clearly.
```

This is not politeness. It is a grounding signal. Without this explicit note, the model is more likely to answer from its training data, which defeats the purpose of a document-grounded system.

### What to include and what to leave out

Context engineering is as much about exclusion as inclusion. Here are the tradeoffs in our pipeline:

**Relevance scores are included** because they help the model weigh evidence. If one excerpt has relevance 0.92 and another has 0.34, the model can (and does) prioritize the higher-scoring evidence. Without scores, the model treats all evidence equally, which degrades answer quality when the retrieval set is noisy.

**Source attribution is included** with each excerpt, not just in the answer. This makes it easier for the model to cite correctly. If it sees "[Source: architecture.md]" next to the evidence, it can reproduce that citation in its answer. If the source is only in metadata the model cannot see, citation accuracy drops.

**Conversation history is optional.** For single-turn question answering, it is omitted. For multi-turn interactions, it is prepended before the evidence. But there is a tradeoff: longer history means fewer tokens available for evidence. In production, you typically need a strategy for summarizing or truncating history to stay within budget.

**Raw text, not summaries.** The pipeline passes the actual chunk text, not a summary of it. Summaries lose detail, and the model's job is to reason over the evidence, not over a lossy compression of it.

## The agent loop

Everything so far -- tools, context, model client -- is a component. The agent loop in `src/ch02/agent.py` is what connects them into a system that can reason iteratively.

### Observe-think-act

The `DocumentAgent` class implements the observe-think-act loop:

1. **Observe.** Retrieve evidence relevant to the query. Assemble the context (system prompt, evidence, query) into a message list.

2. **Think.** Send the context to the model and get a response. The response is either a text answer or a list of tool calls.

3. **Act.** If the model produced tool calls, execute each one through the registry. Append the results to the message list. Go back to step 2. If the model produced a text answer, return it.

The loop continues until either the model produces a final answer (no tool calls) or the step budget is exhausted.

Here is the critical section of the loop:

```python
while response.tool_calls and steps < self._max_steps:
    for tc in response.tool_calls:
        result = await self._registry.execute(tc.name, tc.arguments, tc.id)
        messages.append(Message(role=Role.ASSISTANT, content=f"Calling tool: {tc.name}"))
        messages.append(Message(role=Role.TOOL, content=result.content if result.success else f"Error: {result.error}", tool_call_id=tc.id))

    request = CompletionRequest(messages=messages, tools=tools if tools else None)
    response = await self._client.complete(request)
    total_usage = _merge_usage(total_usage, response.usage)
    steps += 1
```

Several design choices deserve attention:

**Tool results go back into the message list.** This is how the model "sees" what happened. Each tool result becomes a message with `role=Role.TOOL`, which the model processes in its next turn. The model can then reason about the result -- was it what it expected? Does it need more information? Is it ready to answer?

**Both success and failure results are included.** When a tool fails, the error message goes into the context. This lets the model recover: it can try a different tool, rephrase its query, or acknowledge the failure in its answer. Systems that silently swallow tool errors lose this recovery capability.

**Step counting is explicit.** The `steps` counter increments with every model call, and the loop exits when `steps >= self._max_steps`. This is the iteration budget. It is a hard limit, not a suggestion.

**Token usage is tracked across steps.** The `_merge_usage` function accumulates prompt and completion tokens across all model calls. This feeds into cost tracking and helps you understand the actual cost of a multi-step interaction.

### Confidence and escalation

After the loop completes, the agent estimates its confidence:

```python
def _estimate_confidence(citations: list[Citation], answer: str) -> float:
    if not citations:
        return 0.1
    avg_relevance = sum(c.relevance_score for c in citations) / len(citations)
    has_citation_markers = "[Source:" in answer or "[source:" in answer.lower()
    if has_citation_markers and avg_relevance > 0.7:
        return min(0.95, avg_relevance)
    elif avg_relevance > 0.5:
        return avg_relevance * 0.8
    else:
        return avg_relevance * 0.5
```

This is a rough heuristic, not a calibrated probability. But it serves a critical function: it powers the escalation decision. When confidence drops below 0.3, the agent sets `escalated=True` and includes an escalation reason. This is the system saying "I do not trust my own answer enough to present it as authoritative."

Escalation is the most important feature an agent can have. A system that always produces an answer, regardless of evidence quality, is more dangerous than one that says "I do not know." The confidence threshold is a tunable parameter -- in production, you calibrate it against your evaluation results.

### The AgentResponse

The `AgentResponse` model (defined in `src/shared/types.py`) is the output contract:

```python
class AgentResponse(BaseModel):
    answer: str
    citations: list[Citation]
    confidence: float
    escalated: bool
    escalation_reason: str | None
    steps_taken: int
    token_usage: TokenUsage
    latency_ms: float
```

Every field here is operationally meaningful:

- `answer` and `citations` are the user-facing output
- `confidence` and `escalated` drive routing decisions (show to user vs. send to human reviewer)
- `steps_taken` and `token_usage` feed cost tracking and budget monitoring
- `latency_ms` feeds SLA monitoring

This is not just a data container. It is the interface between the agent and every system that consumes its output: the API layer, the evaluation harness, the monitoring dashboard, and the escalation queue.

## Failure modes in this chapter's code

Every component introduced in this chapter has specific failure modes. Here is where they show up and how the code handles them.

**Model hallucinates a tool name.** The registry's `execute` method checks if the tool exists. If not, it returns a `ToolResult` with `success=False` and an error listing the available tools. The model sees this error in its next turn and can adjust.

**Model passes invalid arguments.** The registry validates required parameters before execution. Missing arguments produce a specific error listing what is missing and what was expected.

**Retrieved evidence is irrelevant.** The confidence estimation catches this: low relevance scores produce low confidence, which triggers escalation. The model also sees the relevance scores in the context and can (sometimes) self-assess evidence quality.

**No evidence found at all.** The context pipeline includes the `NO_EVIDENCE_NOTE`, which tells the model there is no evidence. Combined with the system prompt instruction to not guess, this should produce an honest "I cannot answer" response. Should. This is why you need evaluation (Chapter 4).

**Document format unsupported.** The loader raises a `ValueError` with a clear message. The registry catches it and returns an error result.

**Context window overflow.** Not handled in this chapter's code. This is a real production concern -- if you retrieve too many chunks, the context exceeds the model's window. Chapter 4 addresses monitoring for this. The mitigation is controlling `top_k` and chunk size.

**API errors.** Also not handled in this chapter. The model client will raise on HTTP errors. Chapter 4 adds retry logic with exponential backoff.

## Evaluation preview

How do you know this agent works? You do not, yet. We have built the components and connected them into a loop, but we have not measured anything. You can run the agent, read its answers, and manually judge whether they are good. That does not scale, and it does not catch regressions.

Chapter 4 introduces a formal evaluation harness. But even now, you should be thinking about evaluation questions:

- Does the agent cite the correct sources?
- Does it refuse to answer when evidence is insufficient?
- Does it escalate when confidence is low?
- Does it stay within its step budget?
- Does it produce valid JSON when asked for structured output?

Each of these is a testable property. Each corresponds to a failure mode we have already identified. The evaluation harness in Chapter 4 will test all of them systematically.

## Production notes

**Cost.** Every model call costs money. In the agent loop, costs compound: each step adds prompt tokens (the growing message list) and completion tokens (the model's response). A 5-step agent interaction can easily cost 5-10x a single-call workflow doing the same task. Track `token_usage` on every `AgentResponse`.

**Latency.** Each step adds round-trip latency to the model provider. A 5-step loop with 2-second round trips takes 10 seconds minimum. For user-facing applications, this matters. Consider whether a single-step workflow would produce acceptable quality faster.

**Reliability.** The agent loop has no retry logic in this chapter. A transient API error on step 3 of 5 wastes the work from steps 1-2. Chapter 4 adds retry and checkpoint mechanisms.

**Security.** The tool registry validates arguments but does not check permissions. A model could, in theory, call any registered tool with any arguments. Chapter 4 adds a permission policy layer that restricts which tools are available and which side effects are allowed.

**Governance.** The `AgentResponse` includes everything needed for audit: the answer, its citations, the confidence level, the escalation status, the number of steps, the tokens consumed, and the latency. This is the minimum set of fields an enterprise system needs to log for every agent interaction.

## Further reading

- **"A Survey of Agent Systems"** (Wang et al., 2024) -- Comprehensive taxonomy that aligns with the five types discussed in Chapter 1. Useful for comparing your definitions with the broader research landscape.
- **Anthropic tool use documentation** -- The clearest explanation of how tool calling works at the protocol level. Even if you use OpenAI, read this for the mental model.
- **ChromaDB documentation** -- The vector database used in our retriever. The getting-started guide covers the embedding and similarity search concepts our code relies on.
- **Pydantic documentation on model validation** -- Our type system is built on Pydantic. Understanding validation, serialization, and `model_dump` is necessary for working with the code.

## What comes next

You now have a working agent. It retrieves evidence, reasons over it, calls tools when needed, and produces answers with citations and confidence scores. The components are typed, the tools are validated, and the execution is logged.

But you built an agent. Should you have? The Document Intelligence Agent follows a fairly predictable pattern: retrieve evidence, then answer the question. The model's "decisions" in the loop are often unnecessary -- it has enough evidence from the first retrieval pass. When would a deterministic workflow that skips the loop produce equally good answers at lower cost and higher predictability?

Chapter 3 answers this question by building both: the same task implemented as a workflow and as a bounded agent, compared side by side on the same queries. It is the most important architectural decision in this book.
