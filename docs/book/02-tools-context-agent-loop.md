---
description: "How tool-using agents work: function calling, context window management, the agent loop, and writing a working agent without a framework."
---

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

The Document Intelligence Agent has four tools, each in its own module under `src/ch02/tools/`. The diagram below shows the full system architecture: how the document layer feeds into the retrieval layer, which feeds into the reasoning layer, which feeds into the evaluation layer.

<figure>
  <img src="../../diagrams/system-architecture.svg" alt="Document Intelligence Agent system architecture showing document layer, retrieval layer, reasoning layer, and evaluation layer" />
  <figcaption>Figure 2.1: Document Intelligence Agent system architecture</figcaption>
</figure>

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

### Tool schema design -- good vs bad

The schema you write for a tool is not documentation. It is the interface the model reasons against when deciding how to call it. A poorly designed schema does not just look ugly -- it produces wrong tool calls. The model will hallucinate argument values, guess at parameter semantics, and misuse the tool in ways that are hard to debug because the call looks plausible.

Here is a real example from our codebase. The retriever tool needs to search indexed documents. Here is a bad schema:

```python
# BAD: vague, unconstrained, ambiguous
bad_schema = ToolSchema(
    name="search",
    description="Search for stuff",
    parameters=[
        ToolParameter(name="q", type="string", description="query"),
        ToolParameter(name="n", type="integer", description="number", required=False),
        ToolParameter(name="collection", type="string", description="which collection", required=False),
    ],
    side_effect=SideEffect.READ,
)
```

And here is the actual schema from `src/ch02/tools/retriever.py`:

```python
# GOOD: specific names, clear descriptions, appropriate constraints
good_schema = ToolSchema(
    name="retrieve",
    description="Search indexed documents for chunks relevant to a query.",
    parameters=[
        ToolParameter(name="query", type="string", description="The search query"),
        ToolParameter(name="top_k", type="integer", description="Number of results to return", required=False),
    ],
    side_effect=SideEffect.READ,
)
```

The differences look cosmetic. They are not. Here is what happens when the model receives each.

**With the bad schema**, the model sees a tool called `search` that takes `q`, `n`, and `collection`. Three problems emerge immediately:

1. The parameter `q` is ambiguous. The model does not know whether this is a natural language query, a keyword, a regex, or a document ID. In our evaluation runs, models receiving this schema occasionally passed structured queries like `{"q": "type:pdf AND topic:retry"}` because nothing in the schema said otherwise.

2. The parameter `collection` is a free-form string with no enumeration of valid values. This is exactly how Case 4 in our failure analysis played out: the agent called `search_documents(query="retrieval zero results handling", collection="error_handling_docs")` -- a collection that does not exist. The model invented a plausible-sounding collection name because the schema gave it no constraints. (See [Evidence: Failure Case Studies](../proof/failure-cases.md), Case 4.)

3. The description "Search for stuff" tells the model nothing about what kind of results to expect. Does it return full documents? Chunks? Summaries? URLs? The model has to guess, and its guess shapes how it uses the results in subsequent reasoning.

**With the good schema**, the model sees `retrieve`, which takes a `query` (clearly a search query, typed as string) and an optional `top_k` (clearly a count). There is no `collection` parameter because the tool operates on a single pre-configured collection. The model cannot hallucinate a collection name because the interface does not accept one. The description says "chunks relevant to a query," which tells the model it will receive text fragments, not whole documents.

The `ToolParameter` type in `src/shared/types.py` supports an `enum` field for exactly this purpose:

```python
class ToolParameter(BaseModel):
    name: str
    type: str
    description: str
    required: bool = True
    enum: list[str] | None = None
```

When you must expose a parameter with a finite set of valid values, use the enum. The model sees the allowed values in the tool definition and constrains its output accordingly. This is cheaper than catching the error after the call -- both in tokens (no error-retry loop) and in reliability (the model gets it right the first time instead of recovering after a failure).

Three principles for tool schema design:

1. **Name what the tool does, not what it is.** `retrieve` is better than `search` because it implies a specific operation (find and return relevant chunks) rather than a generic one. `load_document` is better than `read_file` because it implies parsing and structure.

2. **Eliminate free-form strings where possible.** Every unconstrained string parameter is a surface for hallucination. If the parameter has five valid values, make it an enum with five entries. If it must be free-form, make the description specific enough that the model can self-validate.

3. **Write descriptions for the model, not for humans.** Your team reads the docstring. The model reads the `description` field in the schema. "The search query" is better than "query" because it confirms the parameter's role. "Number of results to return" is better than "number" because it removes ambiguity about what is being counted.

These are not style preferences. They are engineering constraints that directly affect tool call accuracy. In our baseline evaluation, the four tools with specific schemas had a 94% valid-call rate. When we tested the same agent with loosened schemas (vague names, missing descriptions, unconstrained parameters), the valid-call rate dropped to 71%. The model's ability to use a tool correctly is bounded by the quality of the schema it reasons against.

## Context engineering

Context engineering is the most underrated skill in building LLM-powered systems. The model's output quality is bounded by the quality of its input. A model with poorly assembled context will produce poor answers regardless of how good the model is.

The `ContextPipeline` in `src/ch02/context.py` handles context assembly. It takes three inputs -- a query, a list of citations (retrieved evidence), and optional conversation history -- and produces a list of `Message` objects ready for the model.

### Context window economics

Before looking at how context is assembled, you need to understand the economics of the window you are assembling it into.

A context window is measured in tokens. GPT-4o supports 128k tokens. Claude 3.5 Sonnet supports 200k. These numbers sound generous until you do the arithmetic.

A 5-page PDF becomes roughly 2,000 tokens after extraction. A single retrieved chunk at our default size of 512 tokens is about 200 tokens after the embedding model's tokenizer processes it. Our system prompt is 142 tokens. The query itself is typically 10-20 tokens. So for a single-turn question with 5 retrieved chunks:

```
System prompt:     142 tokens
5 chunks × 200:  1,000 tokens
Query:              12 tokens
---
Total context:   1,154 tokens
```

That is 0.9% of a 128k window. Plenty of room. But this is one query against one document.

Now scale to a production scenario with 50 indexed documents. Each document averages 15 pages, so the full corpus is roughly 30,000 tokens of raw text after extraction. You still retrieve only 5 chunks per query, so the per-query context stays the same. The issue is not the per-query cost -- it is what happens when the retrieval set is noisy.

When your corpus grows, retrieval quality often degrades. The top-5 chunks may include 2 relevant chunks and 3 that are topically adjacent but not useful. Those 3 irrelevant chunks cost 600 tokens and, worse, they dilute the signal. The model now has to distinguish good evidence from noise, and it does this imperfectly. In our evaluation runs, answer quality dropped measurably when more than 40% of the retrieved chunks were irrelevant (relevance score below 0.5).

The real constraint is not window size -- it is window quality. Here are the thresholds that matter:

- **Below 2,000 tokens of context:** The model lacks sufficient evidence for most non-trivial questions. Answers become vague or rely on training knowledge.
- **2,000 to 8,000 tokens:** The productive range for most RAG tasks. Enough evidence for detailed answers, small enough that the model attends to all of it.
- **8,000 to 32,000 tokens:** Diminishing returns. The model may miss details buried in the middle of long contexts (the "lost in the middle" effect documented in Liu et al., 2023). You are paying for tokens the model partially ignores.
- **Above 32,000 tokens of context:** Unless you have a specific reason (full-document analysis, code review), you are wasting money. At GPT-4o input pricing of $2.50 per million tokens, a 32k context costs $0.08 per query. That adds up at 10,000 queries per day.

The multi-step agent loop makes this worse. Each step appends to the message list: the model's previous response, the tool call results, and the new prompt. By step 3 of a 5-step run, the context has grown by 50% or more. From our Trace 3 data (see [Evidence: Trace Examples](../proof/trace-example.md)), context grew from 1,012 tokens to 1,509 tokens in just two steps -- a 50% increase. In a 5-step run, this compounds. If you are not monitoring context size per step, you will not notice the growth until the model starts dropping information or you get a hard error from exceeding the window limit.

What happens when you exceed the window depends on the provider. OpenAI returns a 400 error with "maximum context length exceeded." Anthropic returns a similar error. Neither silently truncates -- you get a hard failure. But the more insidious problem is approaching the limit without exceeding it. At 90% of window capacity, model quality degrades because the model's attention is spread across too many tokens. You will not get an error. You will get a subtly worse answer, and you will not know unless you are running evaluations.

The practical mitigation is to set a token budget per query and enforce it in the context pipeline. In our system, we control this through `top_k` (how many chunks to retrieve) and chunk size (how large each chunk is). The defaults -- 5 chunks at 512 characters -- keep us well within budget for single-turn queries. For multi-step runs, Chapter 4 introduces context pruning between steps to prevent unbounded growth.

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

<figure>
  <img src="../../diagrams/context-pipeline-layers.svg" alt="Context assembly showing three layers: system prompt, evidence excerpts, and user query" />
  <figcaption>Figure 2.2: Context assembly -- three layers from system prompt to user query</figcaption>
</figure>

### Retrieval failure modes

Context quality depends on retrieval quality, and retrieval fails in specific, predictable ways. Understanding these failure modes is essential because they determine the ceiling for your agent's answer quality. No amount of prompt engineering can fix an answer built on the wrong evidence. (See [Evidence: Failure Case Studies](../proof/failure-cases.md) for detailed traces of each failure mode in production.)

**Vocabulary mismatch.** The user asks "how to restart the service" but the documentation says "bounce the process." Embedding models capture semantic similarity, but they are not omniscient. The cosine distance between "restart the service" and "bounce the process" may be large enough that the relevant chunk does not appear in the top-5 results. In our evaluation, Case 1 showed this pattern: the query "What quantum computing algorithms does the system support?" retrieved chunks about "algorithms" and "optimization" -- topically adjacent words, completely wrong context. The retrieval scores were 0.31-0.42, but the agent answered confidently anyway.

The mitigation for vocabulary mismatch is a combination of query expansion (generating synonyms or paraphrases before retrieval) and a minimum relevance threshold. Our hardened system uses a threshold of 0.5: if the best retrieved chunk scores below 0.5, the system escalates before the model ever sees the evidence. This prevents the model from constructing a plausible-sounding answer from irrelevant chunks.

**Chunk boundary splits.** The answer to the user's question spans lines 45-55 of a document. Chunk 1 contains lines 1-50. Chunk 2 contains lines 46-60 (with a 5-line overlap). The critical sentence sits at line 52 -- cleanly inside chunk 2. But chunk 2 starts mid-paragraph, so its opening sentences lack the context that makes line 52 meaningful. The model sees chunk 2 in isolation and either misinterprets it or ignores it.

Case 3 in our failure analysis illustrates this precisely. The question asked about tradeoffs between retry-on-all-exceptions versus selective retry. The key paragraph was split between two chunks. Chunk 15 ended with "you should narrow this to retryable errors only." Chunk 16 began with "A 429 (rate limited) is retryable. A 400 (bad request) is not." Both chunks were retrieved, but they were not adjacent in the context -- an unrelated chunk about checkpointing appeared between them because it had a slightly higher relevance score for the keyword "retry." The model synthesized from chunk 15 alone and missed the concrete HTTP status code examples.

The fix we applied was a "neighbor boost": when a chunk scores above 0.7, its immediate neighbors get a relevance boost of 0.15. This keeps related chunks adjacent in the context window. After this fix, the case score went from 0.62 (FAIL) to 0.82 (PASS).

**Embedding blind spots.** Embedding models are trained primarily on prose. Code snippets, configuration files, log output, and structured data embed poorly. A Python class definition and a natural language question about that class may have low cosine similarity even though they are directly relevant to each other.

In Case 2 of our failure analysis, the model needed the `TraceSpan` class definition to answer a question about its fields. The embedding model ranked the narrative description of `TraceSpan` higher than the actual code block, because the description contained prose tokens that matched the query better. The model could answer from the narrative description, but it cited `src/ch06/tracer.py` (the source file it inferred) rather than `chapter_06.md` (the document the evidence came from). The answer was correct; the citation was wrong.

For code-heavy corpora, consider supplementing vector retrieval with keyword search (BM25) or structured lookups. Some teams maintain a separate index for code blocks with metadata (class name, function name, module path) that supports exact match queries alongside semantic search. This hybrid approach catches what embeddings miss.

**Semantic drift in multi-step retrieval.** When the agent refines its query across multiple steps, each refinement risks drifting further from the original intent. In Case 5, the agent spent 4 of 5 steps drilling deeper into retry logic instead of broadening its search to find checkpointing and circuit breakers. Each refined query ("system recovery provider failure," "handle API failure gracefully") pulled back similar chunks about retry. The agent never encountered the other recovery mechanisms because its search strategy was greedy rather than exploratory.

This is an architectural problem, not a retrieval problem. The retrieval system returned what was asked for. The agent asked the wrong questions. The fix is query decomposition: before retrieval, break multi-part questions into independent sub-queries that each search a different aspect of the topic.

## The agent loop

Everything so far -- tools, context, model client -- is a component. The agent loop in `src/ch02/agent.py` is what connects them into a system that can reason iteratively.

### Observe-think-act

The `DocumentAgent` class implements the observe-think-act loop:

1. **Observe.** Retrieve evidence relevant to the query. Assemble the context (system prompt, evidence, query) into a message list.

2. **Think.** Send the context to the model and get a response. The response is either a text answer or a list of tool calls.

3. **Act.** If the model produced tool calls, execute each one through the registry. Append the results to the message list. Go back to step 2. If the model produced a text answer, return it.

The loop continues until either the model produces a final answer (no tool calls) or the step budget is exhausted.

<figure>
  <img src="../../diagrams/observe-think-act.svg" alt="The observe-think-act agent loop showing iteration from observation through model reasoning to tool execution and back" />
  <figcaption>Figure 2.3: The observe-think-act agent loop</figcaption>
</figure>

### What actually happens -- a traced iteration

The observe-think-act loop is easy to describe in the abstract. Here is what it looks like with actual data from a traced run. This is Trace 1 from our evaluation: a clean pass on the query "What retry strategy does the reliability module use?" (See [Evidence: Trace Examples](../proof/trace-example.md) for the complete annotated trace.)

**Step 1: Observe.** The retriever executes a vector similarity search against the indexed corpus. This takes 45ms. It returns 5 chunks, ranked by relevance. The best match is chunk 14 from chapter_06.md (relevance: 0.87), which contains the `with_retry` function signature and its parameters.

**Step 2: Build context.** The context pipeline assembles the message list:

- System prompt: 142 tokens (the instruction set shown earlier in this chapter)
- 5 evidence chunks: 823 tokens total, each wrapped in `[Excerpt N] (Source: ..., relevance: ...)` format
- User query: 12 tokens

Total context: 977 tokens. This is what the model will see. Nothing more, nothing less. The assembly takes 3ms -- negligible.

**Step 3: Think.** The full 977-token context goes to GPT-4o at temperature 0.0. The model returns 870 tokens of completion in 1,890ms. The response is a direct answer with citations -- no tool calls. The model decided it had enough evidence to answer without using any tools.

**Step 4: Parse and return.** The response contains no tool calls, so the loop exits. Confidence is estimated at 0.74 (above the 0.3 escalation threshold). Total wall time: 2,140ms. Total cost: roughly $0.004.

The important observation: the model call consumed 88% of the total wall time (1,890ms out of 2,140ms). Retrieval was 2% (45ms). Context assembly was 0.1% (3ms). Parsing was 0.1% (2ms). If you need to make this agent faster, you optimize the model call -- shorter context, a faster model, or response caching. Optimizing the retrieval or context assembly would save single-digit milliseconds.

Now compare with a multi-step run. Trace 3 from our evaluation asked "What fields does the EvalCase model include?" The agent took 3 steps:

1. Initial retrieval found the narrative description of EvalCase but not the code definition. Context: 1,012 tokens.
2. The model decided to call `extract_code_block("chapter_06.md", "EvalCase")` to get the exact field list. The tool executed in 12ms and returned 89 tokens of code.
3. With both narrative and code evidence, the model produced a complete answer listing all six fields with types.

Context grew from 1,012 to 1,509 tokens between steps -- a 50% increase that includes the model's previous response and the tool result. Total time: 4,280ms. Total tokens: 3,240. Total cost: roughly $0.008.

The multi-step run produced a better answer (it included the `difficulty` field that the single-step approach would have missed) at 2x the cost and 2x the latency. This is the core tradeoff of the agent loop: better answers cost more and take longer. Chapter 3 explores this tradeoff systematically.

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

Every component introduced in this chapter has specific failure modes. Here is where they show up and how the code handles them. (For detailed traces of these failures in evaluation, see [Evidence: Failure Case Studies](../proof/failure-cases.md).)

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

Each of these is a testable property. Each corresponds to a failure mode we have already identified. The evaluation harness in Chapter 4 will test all of them systematically. (See [Evidence: Baseline Evaluation Report](../proof/baseline-eval-report.md) for the 30-case evaluation that quantifies exactly where the baseline agent succeeds and fails.)

## Production notes

The components in this chapter work in a development environment. Production introduces a different set of concerns. Here is what to watch for, with specific numbers from our evaluation runs. (See [Evidence: Baseline Evaluation Report](../proof/baseline-eval-report.md) for the full dataset.)

**Token cost per query.** Every model call costs money. In our baseline evaluation of 30 test cases, the total token consumption was 47,200 tokens at a total cost of $0.118 -- roughly $0.004 per query. That is cheap for development. At 10,000 queries per day, it becomes $40/day or $1,200/month. At 100,000 queries per day, it is $12,000/month. And those numbers assume single-step queries. Multi-step agent runs compound costs: Trace 3 in our evaluation used 3,240 tokens across 3 steps, costing $0.008. A 5-step run on a complex query can consume 5,000-8,000 tokens. The agent loop's growing message list means each subsequent step is more expensive than the last because the prompt includes all previous messages.

Track `token_usage` on every `AgentResponse`. Aggregate it by query category, step count, and model. This data tells you where to optimize: if 80% of your cost comes from 15% of queries (the multi-step ones), consider whether those queries should use the agent loop at all or whether a workflow would suffice (Chapter 3 addresses this directly).

**Latency breakdown.** From our traced runs, here is where time goes in a typical single-step query:

```
Retrieval (vector search):      45ms    (2.1%)
Context assembly:                3ms    (0.1%)
Model call:                  1,890ms   (88.3%)
Response parsing:                2ms    (0.1%)
Overhead (logging, metrics):   200ms    (9.3%)
---
Total:                       2,140ms
```

The model call is 88% of the wall time. This has two implications. First, optimizing anything other than the model call yields marginal gains. Second, the latency is almost entirely determined by your model provider's response time, which you do not control. For user-facing applications with SLA requirements, consider response streaming (the model returns tokens as they are generated), caching (return a cached answer for repeated queries), or using a smaller, faster model for simple queries and routing complex ones to the full model.

For multi-step runs, latency compounds linearly. A 3-step run took 4,280ms. A 5-step run takes 8-10 seconds. Users will notice.

**Structured output failures.** When the extractor tool asks the model for structured JSON output, the model complies most of the time. But not always. With GPT-4o at temperature 0.0, we observed invalid JSON in approximately 2-3% of structured output requests. The failures include trailing commas, unescaped quotes in string values, and occasionally truncated JSON when the completion hits the max token limit mid-object.

The mitigation is validation and retry. Parse the model's output with a JSON parser. If it fails, send the output back to the model with a correction prompt: "The following JSON is invalid: [error message]. Please fix it." This works in nearly all cases and costs one additional model call. The alternative -- writing a custom JSON repair function -- is brittle and handles fewer edge cases than the model does.

**Rate limiting and retry behavior.** Model providers impose rate limits. OpenAI's limits vary by tier but commonly cap at 500-10,000 requests per minute depending on your plan. When you hit the limit, the API returns HTTP 429 with a `Retry-After` header. The agent loop in this chapter has no retry logic -- a rate limit error on step 3 of 5 crashes the run and wastes the work from steps 1-2.

The minimum viable retry strategy is exponential backoff on 429 and 500-series errors, with a maximum of 3 attempts. Do not retry on 400 (bad request) or 401 (authentication) -- those are permanent failures. Chapter 4 implements this properly with the `with_retry` wrapper. For this chapter, be aware that the code will fail under load and plan your evaluation runs accordingly.

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
