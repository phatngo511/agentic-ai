---
description: "Why you should reach for deterministic workflows before agents. Decision criteria, architecture comparison, and the engineering instinct that saves production systems."
---

# Chapter 3: Workflow First, Agent Second

## Why this matters

Every time a team builds an agent, they should first ask: would a workflow do the job? This is not anti-agent sentiment. It is the same engineering instinct that asks "do I need a microservice, or would a function call suffice?" The simpler architecture is not always worse. It is usually cheaper, faster, easier to test, and easier to explain to the person who gets paged at 3 AM.

This chapter makes the comparison concrete. We implement the same task -- document question answering with citations -- as both a deterministic workflow and a bounded agent. We run them on the same queries and measure the differences. The goal is not to declare a winner. It is to give you the information you need to choose correctly for your problem.

The decision between workflow and agent is the most consequential architectural choice in an LLM-powered system. Get it right and you have a system that is appropriately scoped -- enough autonomy to handle the task, no more. Get it wrong in either direction and you pay: too little autonomy and the system cannot handle variation; too much and you pay the agent tax in cost, latency, and unpredictability.

## The deterministic workflow

A workflow is a fixed pipeline. Every query takes the same path through the same steps. The code decides what happens next, never the model.

The `DocumentWorkflow` class in `src/ch03/workflow.py` implements our document intelligence task as a three-step pipeline:

1. **Retrieve.** Query the vector index for relevant chunks.
2. **Build context.** Assemble the system prompt, evidence, and query into a message list.
3. **Answer.** Send the context to the model and return the response.

That is the entire implementation. The `run` method is about 15 lines of code:

```python
async def run(self, query: str, top_k: int = 5) -> AgentResponse:
    start = time.monotonic()
    citations = self._index.retrieve(query, top_k=top_k)
    messages = self._context.build(query=query, citations=citations)
    request = CompletionRequest(messages=messages)
    response = await self._client.complete(request)
    elapsed = (time.monotonic() - start) * 1000
    # ... build AgentResponse with confidence and escalation
```

Notice what is absent. No loop. No tool calls. No step budget. No decision-making by the model about what to do next. The model's job is narrowly scoped: given this evidence, answer this question.

### Strengths of the workflow approach

**Predictable cost.** Every query makes exactly one model call. You can calculate the cost ceiling from the model's pricing and your maximum context size. There are no surprises.

**Predictable latency.** One retrieval call plus one model call. You can set SLAs with confidence because the execution path is fixed.

**Easy to test.** You can test retrieval in isolation (does it return relevant chunks?), context assembly in isolation (is the prompt well-formed?), and the model step in isolation (given this exact context, does the model produce a good answer?). End-to-end tests are also straightforward because the system is deterministic up to the model's output.

**Easy to debug.** When the answer is wrong, the investigation path is short. Was the retrieval bad? Look at the chunks. Was the context bad? Print the messages. Was the model's reasoning bad? Read the answer in the context of the evidence. There is no loop to trace through, no tool-call chain to reconstruct.

**Easy to explain.** You can describe the system in one sentence: "it searches the documents, puts the results in a prompt, and asks the model to answer." Stakeholders, auditors, and on-call engineers can all understand this.

### Where the workflow falls short

**Single-pass retrieval.** The workflow gets one shot at finding the right evidence. If the user's query uses different terminology than the documents, or if the answer requires synthesizing information from multiple topics that a single query does not cover, the retrieval may miss.

**No adaptation.** If the first retrieval returns low-quality results, the workflow cannot try again with a refined query. It hands whatever it found to the model and hopes for the best. The confidence estimation can flag low-quality retrievals for escalation, but it cannot fix them.

**No multi-step reasoning.** Some questions require intermediate steps: find one piece of information, use it to formulate a second query, then synthesize both. The workflow cannot do this because it has no loop.

These shortcomings are real but bounded. For many production use cases -- FAQ answering, document search, customer support -- single-pass retrieval with good chunking and a well-tuned index is sufficient. The workflow's limitations become problems only when the task genuinely requires adaptive, multi-step reasoning. And "genuinely requires" is doing a lot of work in that sentence.

## The bounded agent

The `BoundedDocumentAgent` in `src/ch03/agent.py` solves the same task with a fundamentally different architecture. It has a loop, a step budget, tools it can call, and the autonomy to decide at each step whether it has enough evidence or needs to search again.

What distinguishes this from the Chapter 2 agent is the explicit engineering for bounded autonomy:

**Iteration budget.** The `max_steps` parameter (default 5) hard-limits how many model calls the agent can make. This is not optional. An agent without a budget is a runaway process.

**Stop conditions.** The loop continues until either the agent produces a text response (no more tool calls), the agent marks the task complete with a confidence score, or the step budget is exhausted.

**State tracking.** The `TaskState` object (defined in `src/ch03/state.py`) records every step: what action was taken, what parameters were used, and what result was observed. This is the audit trail that lets you reconstruct what the agent did and why.

**Graceful degradation.** When the budget is exhausted without a confident answer, the agent does not crash or return nothing. It produces the best partial answer it has, sets `escalated=True`, and includes the reason: "Budget exhausted without reaching confidence threshold." This is the system telling its operator: "I tried, I ran out of room, here is what I found."

**Confidence-gated completion.** The agent tracks citation quality and checks for source attribution in its own answers. Higher relevance scores plus proper citations yield higher confidence. Below the threshold, the agent either keeps searching (if it has budget) or escalates.

### The bounded agent's system prompt

The system prompt in `src/ch03/agent.py` is different from the workflow's prompt. It instructs the model about its constraints:

```
You are a document intelligence agent with bounded autonomy.

You have tools available. You may:
- Call 'retrieve' to search for more evidence if the initial results are insufficient.
- Call 'extract_structured' to pull specific fields from text.

Constraints:
- You have a limited step budget. Use it wisely.
- Only use information from retrieved documents. Do not use training knowledge.
- If you cannot answer confidently within your budget, say what you found
  and what is missing. Do not guess.

After each step, decide: do I have enough evidence to answer, or should I
search again with a different query?
```

This prompt gives the model an explicit decision framework: assess sufficiency, then either answer or search again. The model does not always follow this perfectly -- it is a probabilistic system -- but the instruction measurably improves the quality of the agent's step-by-step decisions compared to a generic agent prompt.

### State management

The `src/ch03/state.py` module defines two kinds of state:

**SessionState** tracks a conversation across multiple queries. It stores a history of query-answer pairs and counts turns. This is useful for multi-turn interactions where the agent needs to maintain context across questions.

**TaskState** tracks a single task's execution. It records every step (action, parameters, result, timestamp), the current result and confidence, and whether the task is complete or over budget. The properties `is_complete`, `is_over_budget`, and `budget_remaining` let the agent loop make clean control-flow decisions.

The separation between session and task state is deliberate. A session can span many tasks, and a task's state is discarded after it completes. This matches how users interact with the system: they ask a series of questions, and each question is a separate task that should not be contaminated by the internal state of previous tasks.

Why track state this carefully? Three reasons:

1. **Debugging.** When an agent produces a bad answer, you can replay its steps from the `TaskState` and see exactly where it went wrong. Did it retrieve the right evidence? Did it waste budget on irrelevant tool calls? Did it stop too early?

2. **Evaluation.** The step log lets you evaluate not just the final answer but the agent's process. Did it take an efficient path? Did it call tools unnecessarily? Process evaluation catches problems that output evaluation misses.

3. **Resumption.** If the agent is interrupted (crash, timeout, deployment), a checkpointed `TaskState` lets you resume from the last good step rather than starting over. Chapter 4 implements this with the `Checkpoint` class.

## Same task, two ways: the comparison

The `ComparisonRunner` in `src/ch03/compare.py` runs both implementations on the same queries and collects metrics side by side.

```python
class ComparisonRunner:
    def __init__(self, client: ModelClient, index: DocumentIndex):
        self._workflow = DocumentWorkflow(client=client, index=index)
        self._agent = BoundedDocumentAgent(
            client=client, index=index,
            registry=ToolRegistry(), max_steps=5,
        )

    async def compare(self, queries: list[str]) -> list[ComparisonResult]:
        results = []
        for query in queries:
            workflow_resp = await self._workflow.run(query)
            agent_resp = await self._agent.run(query)
            results.append(ComparisonResult(
                query=query, workflow=workflow_resp, agent=agent_resp,
            ))
        return results
```

The `print_results` method outputs a table comparing steps, tokens, latency, confidence, and escalation status for each query.

Here is what you typically see when you run this comparison:

**For straightforward queries** (the answer is clearly present in one or two chunks), the workflow and agent produce equivalent answers. But the agent takes 2-3 steps and uses 2-3x more tokens. The agent's extra steps are wasted -- the first retrieval was sufficient.

**For ambiguous queries** (the answer requires synthesizing information from different sections, or the terminology does not match), the agent sometimes outperforms the workflow. Its ability to search again with a refined query finds evidence the workflow misses. But "sometimes" is the operative word. The agent does not always choose to refine its search, and when it does, the refinement is not always better.

**For queries with no answer in the corpus**, both implementations should escalate. The workflow escalates based on low relevance scores. The agent escalates either because of low relevance or because it exhausted its budget without finding sufficient evidence. The agent's escalation is more informative (it can say "I searched for X, then Y, and neither produced relevant results") but more expensive (it spent its budget searching before escalating).

### The overhead question

The agent's advantage is adaptive reasoning. Its cost is overhead: more model calls, more tokens, more latency, more failure surface. The comparison forces you to quantify this tradeoff for your specific task.

If 90% of your queries are straightforward and the workflow handles them well, the agent's overhead on those 90% of queries is pure waste. You are paying 2-3x more tokens for the same answer. The agent is worth it only if the remaining 10% of queries produce sufficiently better results to justify the aggregate cost.

This is a calculation, not a philosophy. Run the comparison on your actual queries, with your actual documents, and look at the numbers. The answer will be specific to your use case.

## Design guidance: when to choose which

Based on the comparison and production experience with similar systems, here is a decision framework.

### Choose the workflow when:

- **The retrieval quality is good.** If your index, chunking strategy, and embeddings consistently return relevant evidence for your query distribution, single-pass retrieval is sufficient. Invest in better retrieval rather than adding an agent loop.

- **The task is predictable.** If you know the shape of incoming queries -- FAQ-style questions, lookup requests, summarization tasks -- a workflow handles the known patterns without the agent's overhead.

- **Cost and latency matter.** If you have SLAs, budget constraints, or user-facing latency requirements, the workflow's predictability is a feature, not a limitation.

- **You need testability.** If regulatory or compliance requirements demand that you can explain and reproduce the system's behavior, the workflow's fixed path is much easier to audit than the agent's variable path.

### Choose the agent when:

- **Queries are diverse and unpredictable.** If users ask novel questions that require different retrieval strategies, the agent's ability to refine its search adds value.

- **Multi-step reasoning is necessary.** If answers require finding one piece of information, using it to formulate a follow-up query, and then synthesizing the results, the agent's loop is the right tool.

- **The cost of a wrong answer is high.** Paradoxically, the agent can be more reliable for high-stakes queries because it can iteratively verify its evidence. But you must pair this with proper evaluation (Chapter 4) to confirm that the extra steps actually improve quality.

- **You have already tried the workflow and measured its limitations.** This is the most important criterion. Do not start with an agent. Start with a workflow, measure where it fails, and add agency only to address the measured shortcomings.

### The hybrid approach

The most practical production architecture is often a hybrid: workflow by default, with agent escalation for hard cases.

The pattern:

1. Run the workflow.
2. Assess the result (confidence score, relevance scores).
3. If the result is above the confidence threshold, return it.
4. If below, run the agent with the workflow's retrieval results as a starting point.

This gives you the workflow's cost efficiency for easy queries and the agent's adaptive reasoning for hard ones. It also gives you data: the fraction of queries that escalate from workflow to agent tells you how much autonomy your task actually needs.

## Planning and single-agent design

The bounded agent in this chapter is a single-agent system. It has one loop, one tool set, and one scope of responsibility. Before you reach for multi-agent architectures, it is worth understanding how far a single agent can go when properly designed.

### Planning inside the loop

The bounded agent does not have an explicit planning step. Its "plan" emerges from the observe-think-act loop: at each step, the model decides what to do based on what it has seen so far. This implicit planning works for tasks with shallow depth -- the document intelligence task rarely needs more than 2-3 meaningful steps.

For deeper tasks, you can add explicit planning without moving to multiple agents. The technique is straightforward: add a planning prompt as the first step that asks the model to outline its approach, then execute the plan step by step. The plan is not binding -- the model can deviate based on intermediate results -- but it provides structure that reduces wasted steps.

The key insight: planning is a prompt pattern, not an architecture pattern. You do not need a "planner agent" and an "executor agent." You need one agent that thinks before it acts.

### Tool composition vs. agent composition

When a task gets complex, there are two ways to decompose it:

**Tool composition:** Add more specialized tools to the single agent. The agent selects the right tool for each step. This works when the tools are independent and the agent can reason about when to use each one.

**Agent composition:** Create multiple agents, each with a focused tool set. A coordinator delegates subtasks. This works when the subtasks require different system prompts, different model configurations, or truly independent execution.

The threshold for moving from tool composition to agent composition is higher than most people think. A single agent with 5-8 well-designed tools can handle surprisingly complex tasks. Agent composition adds coordination overhead (how do agents communicate?), state synchronization (how do agents share context?), and evaluation complexity (how do you test the aggregate behavior?).

Rule of thumb: if you can describe the task decomposition as "do A, then do B with the result" -- tool composition within a single agent. If the decomposition is "A and B can run in parallel with different expertise and need to reconcile their findings" -- maybe agent composition. But reach for it as a last resort.

## Failure modes specific to this chapter

The workflow and agent have different failure profiles, which is part of the comparison.

### Workflow-specific failures

**Retrieval miss, no recovery.** If the first (and only) retrieval pass misses the relevant evidence, the workflow has no recourse. It produces an answer based on whatever it found, with appropriate confidence scoring and possible escalation. But it cannot try again.

**Terminology mismatch.** If the user asks about "compensation" but the documents use "remuneration," the embedding similarity may be too low. The workflow cannot rephrase the query. The agent can.

**Multi-hop inability.** If the answer requires two pieces of information that would require two separate queries (e.g., "What is the budget for the project mentioned in the risk assessment?"), the workflow gets one query. The agent can chain them.

### Agent-specific failures

**Budget waste.** The agent might spend its budget on unnecessary tool calls. It retrieves evidence, decides to retrieve again with a slightly different query, gets similar results, and burns through steps without improving its answer. This is the most common failure mode in practice.

**Decision quality degradation.** As the message list grows with tool results, the model's context gets noisier. Later steps have worse signal-to-noise ratios than earlier steps, because the model is reasoning over more text. The agent can actually get worse as it works longer.

**Stop condition ambiguity.** The model does not always know when to stop. It might produce a tool call when it already has sufficient evidence, or it might produce an answer too early when more evidence would help. The confidence estimation helps, but it is heuristic.

**Tool error loops.** If a tool call fails (e.g., the retriever returns no results for a refined query), the agent might try the same approach again rather than trying something different. The idempotency tracking in Chapter 4 addresses this, but in this chapter's code, the agent can waste budget retrying failures.

### Shared failures

**Hallucination despite grounding.** Both the workflow and the agent can hallucinate -- the model ignores the evidence and answers from training knowledge. Grounding instructions in the system prompt reduce this but do not eliminate it. Evaluation (Chapter 4) is the only reliable way to measure hallucination rates.

**Citation fabrication.** Both can produce citations that do not match the evidence. The model generates a [Source: filename] marker but attributes information to the wrong source. This is detectable in evaluation but not preventable through prompting alone.

**Over-confidence.** Both can produce confident answers when the evidence is weak. The confidence estimation is a heuristic that catches some cases but misses others. In production, you need calibrated confidence -- which requires running evaluation over many examples and adjusting the threshold.

## Production notes

**Cost comparison.** Track the token usage from `ComparisonRunner` for your actual queries. The typical ratio is 2-5x more tokens for the agent versus the workflow on the same query. At scale, this multiplier dominates your LLM spend. A system processing 10,000 queries per day at $0.003 per workflow query costs $30/day. The same system with agents at $0.012 per query costs $120/day. The agent needs to produce measurably better results to justify that difference.

**Latency comparison.** The workflow makes one model call. The agent makes 2-5. If your model provider averages 1.5 seconds per call, the workflow takes about 1.5 seconds and the agent takes 3-7.5 seconds. For user-facing applications, this is the difference between "fast" and "noticeably slow."

**Monitoring.** In production, monitor the following per-query metrics for both implementations: token count, latency, confidence score, escalation rate, and step count (for the agent). The step count distribution tells you whether the agent is using its budget efficiently. If most queries complete in 1-2 steps, the agent loop is overhead for those queries. If queries regularly hit the budget limit, the budget may be too low or the task may be too hard for the agent.

**A/B testing.** The comparison framework is designed for offline evaluation, but the same structure supports A/B testing in production. Route a fraction of traffic through the agent and compare aggregate quality metrics against the workflow baseline. This gives you real-world data on whether the agent justifies its cost.

**State persistence.** The `TaskState` in this chapter is in-memory. For production systems with long-running tasks or reliability requirements, serialize the state to a database or the file system. Chapter 4's `Checkpoint` class provides a simple file-based implementation.

## Further reading

- **"Workflows vs Agents"** -- Anthropic's engineering blog post on when to use each pattern. The clearest industry guidance on this decision, consistent with the framework in this chapter.
- **"Designing Autonomous AI Agents"** by Shunyu Yao et al. -- The ReAct paper that formalized the observe-think-act pattern. Worth reading for the conceptual framework, though the implementation details are now dated.
- **tenacity library documentation** -- The retry library used in Chapter 4's reliability module. Understanding exponential backoff and retry strategies is essential for production agent systems.

## What comes next

You have now built the same task two ways and have a framework for choosing between them. You understand the cost, latency, and quality tradeoffs. You have state management that tracks every step for debugging and evaluation.

But the single-agent boundary is not always the right boundary. Some tasks are genuinely parallel. Some require different expertise in different stages. Some are too large for one context window, one tool set, or one system prompt to handle well.

Chapter 4 pushes into that territory. It asks: I know when to use a single agent. But when do I actually need multiple agents -- and how do I keep them from turning into distributed confusion?
