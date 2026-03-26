# Chapter 7: When Not to Use Agents

## Why this matters

This is the chapter most books on agents would not include. The entire trajectory of the book -- building tools, composing an agent loop, comparing architectures, evaluating and hardening -- has been moving toward more capability, more sophistication, more autonomy. It would be natural to end with "and now you can build agents for everything."

That would be dishonest.

The most valuable skill an engineer can develop is knowing when not to use a powerful tool. A database engineer who reaches for a distributed database for every project is not senior. A systems engineer who deploys Kubernetes for a single-process application is not pragmatic. And an AI engineer who builds an agent when a workflow would suffice is not being thorough -- they are creating unnecessary risk, cost, and complexity.

This chapter is about the decision not to build an agent. It is about recognizing the specific conditions under which autonomy adds value, and the much broader set of conditions under which it does not. It is about building the judgment that turns a capable engineer into a trustworthy one.

## The agent tax

Every agent system pays a tax that simpler architectures do not. Understanding this tax in concrete terms is the foundation for deciding whether to pay it.

**Cost tax.** An agent makes multiple model calls per request. In Chapter 3, we measured 2-5x more tokens for the agent versus the workflow on the same queries. At scale, this is the difference between a viable product and one that bleeds money. The cost is not just the tokens -- it is the infrastructure to track, monitor, and govern those costs.

**Latency tax.** Multiple sequential model calls mean multiple round trips. Each step adds 1-3 seconds. A 5-step agent interaction takes 5-15 seconds. For user-facing applications, this is often unacceptable. For batch processing, it multiplies throughput requirements.

**Reliability tax.** More steps mean more points of failure. Each model call can timeout, rate-limit, or return garbage. Each tool call can fail. The probability of at least one failure in a 5-step interaction is dramatically higher than in a 1-step interaction. You need retry logic, checkpointing, and graceful degradation -- all of which add code complexity.

**Testability tax.** Agent behavior is non-deterministic and path-dependent. The same query can produce different step sequences across runs. Testing requires statistical evaluation over many cases, not deterministic assertions. Your CI pipeline goes from "run tests, check pass/fail" to "run evaluation suite, check aggregate metrics against thresholds." This is harder to build, slower to run, and more nuanced to interpret.

**Debuggability tax.** When a workflow produces a wrong answer, you trace one model call. When an agent produces a wrong answer, you trace N model calls, M tool calls, and the decision chain that led to each one. You need structured tracing (Chapter 4) just to make debugging feasible.

**Governance tax.** For regulated industries, you must explain what the system did and why. A workflow's explanation is trivial: "it retrieved these documents and generated this answer." An agent's explanation requires reconstructing its decision tree from traces. Auditors and compliance teams are not impressed by capability. They are reassured by simplicity.

The agent tax is not a reason to never build agents. It is a reason to build them deliberately, with clear justification for why the tax is worth paying. If you cannot articulate the specific capability the agent provides that a simpler system cannot, you should not pay the tax.

## Alternatives that are usually sufficient

Before reaching for an agent, exhaust these simpler alternatives. Each one handles a set of problems that people commonly build agents for, without the agent tax.

### Workflows

Covered in depth in Chapter 3, but worth revisiting here with different examples.

**Invoice processing.** A common "agent" use case that is almost always a workflow. The steps are known: extract vendor name, extract amounts, extract dates, validate against purchase orders, route for approval. Each step can use an LLM, but the sequence is fixed. There is no decision about what to do next. An agent would add overhead without adding capability.

**Content moderation.** Classify the content, check against policy rules, flag or approve. The steps are fixed, the logic is deterministic, and the LLM's role is classification within each step. Making this an agent -- where the model decides what to check next -- adds unpredictability to a system that needs to be auditable and consistent.

**Report generation.** Gather data from sources, format into sections, generate summaries per section, compile. The structure is known in advance. The LLM generates text within each section, but the control flow is the programmer's.

The pattern: if you can draw the flowchart before you see the input, it is a workflow. Agents are for tasks where the flowchart depends on what you discover along the way.

### Rules engines

Many tasks that look like they need "intelligence" actually need conditional logic. A rules engine evaluates conditions and applies actions. No LLMs, no tokens, no latency.

**Routing.** "If the question is about billing, route to the billing team. If it is about technical support, route to engineering." This is a classifier, not an agent. Train a small model or use keyword matching. Response time: milliseconds. Cost: effectively zero.

**Escalation.** "If confidence is below 0.6 or the query contains keywords X, Y, Z, escalate to a human." This is a rule, not a reasoning task. The confidence score comes from your system; the escalation logic is deterministic.

**Validation.** "If the extracted amount is greater than $10,000, require manager approval." A rules engine checks this in microseconds. An agent checking this by "reasoning" about the amount is using a nuclear reactor to light a candle.

The question to ask: does this decision require understanding natural language in a way that cannot be captured by conditions and patterns? If yes, you might need an LLM (though probably a classifier, not an agent). If no, a rules engine is faster, cheaper, more predictable, and easier to audit.

### Retrieval-only systems

Many "agent" systems are actually retrieval systems with a generation step. The user asks a question, the system finds relevant passages, and the system returns the passages (possibly with a generated summary). This is a workflow, and often the generation step is optional.

**Documentation search.** The user wants to find the relevant section of a manual. Returning the top-3 relevant chunks with highlighted keywords is faster, cheaper, and more trustworthy than having an agent "reason" over the chunks and produce a synthesized answer. The user can read the original text and judge for themselves.

**Legal research.** Finding relevant precedents and statutes. The value is in surfacing the right documents, not in an LLM's interpretation of them. Lawyers need citations they can verify, not synthesized conclusions from a system they cannot examine.

**Internal knowledge bases.** When employees search for company policies or procedures, they usually want the source document, not an AI's paraphrase of it. The retrieval is the product. Generation adds risk (hallucination) without proportional value.

The question to ask: does the user need the system to reason over the retrieved content, or do they need the system to find the right content? If finding is sufficient, skip the generation. If reasoning is needed, a single-step workflow (retrieve then generate) usually suffices. If the reasoning requires multiple passes with different queries -- then you might need an agent.

### Classifiers

Many agent systems are elaborate ways to do classification. The agent "analyzes" input and "decides" which category it belongs to. This is a classification task. Use a classifier.

**Intent detection.** "The user wants to return a product" / "The user wants to track an order" / "The user wants to cancel a subscription." Fine-tune a small model. Response time: under 100ms. Cost: negligible. Accuracy: often higher than a general-purpose LLM because the classifier is specialized.

**Sentiment analysis.** Positive, negative, neutral. A fine-tuned classifier or even a rule-based system outperforms an LLM agent for this task on every dimension: speed, cost, consistency, and testability.

**Triage.** Assigning priority or routing to incoming requests. This is classification with a domain-specific label set. Build a classifier, not an agent.

The question to ask: is the system's primary job to assign a label from a known set? If yes, use a classifier. Agents are for open-ended tasks where the output space is not enumerable.

### Human-in-the-loop with LLM assistance

Sometimes the right architecture is a human doing the task, with an LLM providing suggestions. This is not a cop-out. It is a legitimate system design that combines the model's breadth with the human's judgment.

**Medical report analysis.** The LLM highlights relevant findings and suggests possible interpretations. The doctor makes the diagnosis. The LLM's role is to surface information, not to decide.

**Contract review.** The LLM identifies clauses that deviate from standard terms. The lawyer reviews the flagged clauses and makes the legal judgment. The LLM accelerates the human's work without replacing the human's accountability.

**Code review.** The LLM identifies potential bugs, style violations, and missing tests. The engineer reviews the suggestions and decides which to act on. The LLM's output is advisory, not authoritative.

In these cases, building an autonomous agent is not just unnecessary -- it is actively harmful. The stakes are too high for unsupervised autonomous decisions, and the humans in the loop have expertise that the model lacks. The right system design amplifies the human rather than replacing them.

## A decision framework

Here is a structured approach to deciding whether a task needs an agent.

### Step 1: Can you draw the flowchart?

If you can specify the steps before seeing the input, it is a workflow. Do not build an agent. The test is not whether the task is complex -- complex workflows with many steps are still workflows. The test is whether the steps are known in advance.

### Step 2: Does the task require multi-step reasoning with intermediate decisions?

If the answer to step 1's question requires finding information and then using that information to decide what to look for next -- that is a reason for an agent. But be honest: does it really require this, or are you imagining edge cases that represent 5% of the query volume?

### Step 3: Have you measured the workflow's limitations?

Build the workflow first. Run it on your actual queries. Measure where it fails. If it fails on 30% of queries because single-pass retrieval is insufficient, you have data justifying an agent. If it fails on 3% of queries, consider handling those 3% with human escalation rather than building an agent for all queries.

### Step 4: Does the agent actually improve the failure cases?

Build the agent. Run it on the cases where the workflow failed. If the agent recovers 80% of those failures, you have a strong case for the agent (or the hybrid approach from Chapter 3). If the agent recovers 20% of them while costing 3x more on every query, the math does not work.

### Step 5: Is the agent's improvement worth the agent tax?

Multiply the agent's per-query cost by your volume. Compare against the workflow's cost. Calculate the value of the improvement. In some domains (medical, legal, financial), recovering even a small number of failures has high value. In others (content summarization, FAQ), the value of marginal improvement is low.

This framework is deliberately conservative. It assumes the workflow is the default and the agent must justify itself. This is the right starting point because the agent tax is real and the agent's benefits are uncertain until measured.

## Systems that should not have been agents

These are composite examples drawn from patterns seen across the industry. They illustrate the mismatch between the agent pattern and the actual problem.

### The "agent" that always follows the same path

A company built a customer support agent that follows this sequence: classify the query, look up the customer's account, check for known issues, generate a response. The agent had tools for each step and a loop that called them in order.

The agent always called the same tools in the same order. It never skipped a step. It never went back to re-classify after seeing the account. It never decided that a different approach was needed.

This was a workflow wearing an agent costume. The agent loop added latency (3x slower than a fixed pipeline), cost (2.5x more tokens), and unpredictability (occasionally the model decided to skip the account lookup step, producing a generic response). Replacing the agent with a workflow improved response time, reduced cost, and eliminated the random skipping behavior.

The lesson: if the agent's decisions are predictable, you do not need an agent to make them. Write the decisions in code.

### The multi-agent system for a single-agent task

A team built a three-agent system for document analysis: a "planner" agent that decomposed the query, an "executor" agent that ran the search and extraction, and a "reviewer" agent that checked the answer. Each agent had its own system prompt, tool set, and model calls.

The planner's decomposition was almost always the same: "search for relevant information and extract the answer." The reviewer almost always approved the executor's answer. The system made 8-12 model calls per query, with most of the tokens spent on inter-agent communication (the planner's plan, the executor's report, the reviewer's assessment).

A single agent with a 5-step budget produced equivalent quality with 3-4 model calls. The three-agent architecture added coordination complexity, made debugging harder (which agent was responsible for a bad answer?), and cost 3x more.

The lesson: do not decompose into agents when tool decomposition within a single agent works. Agent boundaries should correspond to genuinely different capabilities or expertise, not to steps in a process.

### The agent that reinvented grep

A startup built an "intelligent code analysis agent" that searched codebases for patterns, analyzed the results, and produced reports. The agent used tools for file search, content extraction, and pattern matching.

The core operation -- finding files matching a pattern and extracting relevant sections -- is what grep, ripgrep, and language server protocols do. The LLM's contribution was formatting the results into a human-readable report. The "intelligence" in the system was 95% traditional text search and 5% LLM summarization.

Replacing the agent with a script that ran the searches and used a single LLM call to format the results produced the same output quality at 1/10th the cost and 1/20th the latency.

The lesson: before building an agent, check whether the task's core operations are already solved by existing tools. If the LLM's role is primarily formatting or summarization of results obtained by conventional means, use a workflow with a single generation step.

## An honest retrospective on the Document Intelligence Agent

Throughout this book, we built the Document Intelligence Agent as both a workflow and a bounded agent. Here is an honest assessment of whether the agent was justified.

### Where the agent helped

**Ambiguous queries.** When the user's terminology did not match the documents, the agent's ability to rephrase and re-search occasionally found evidence the workflow missed. This was a real, measurable improvement on about 15-20% of our test cases.

**Multi-part questions.** Questions that required finding two pieces of information and synthesizing them benefited from the agent's loop. The workflow could only answer the first part; the agent could sometimes answer both.

### Where the agent did not help

**Straightforward lookups.** For the majority of queries (roughly 70-80%), the first retrieval pass found sufficient evidence. The agent's extra steps on these queries were pure overhead -- it retrieved the same evidence, sometimes called tools unnecessarily, and produced an equivalent answer at 2-3x the cost.

**Questions with no answer.** When the evidence was not in the corpus, the agent spent its budget searching fruitlessly before escalating. The workflow escalated immediately (low relevance scores, low confidence). The agent was more expensive for the same outcome.

**Structured extraction.** When the task was to extract specific fields from a document, the agent's adaptive reasoning did not help. The extraction was a single-step operation. The agent loop added nothing.

### The honest verdict

For this specific task and document corpus, the hybrid approach from Chapter 3 is the right architecture: workflow by default, agent escalation for the cases where the workflow's confidence is low. This captures the agent's value on hard queries without paying the agent tax on easy ones.

If the query distribution were different -- if most queries were ambiguous, if the documents were poorly organized, if the task required deep multi-step reasoning -- the balance might tip differently. The point is not that agents are wrong. The point is that the decision should be driven by measurement, not by default.

And here is the most important takeaway: the workflow was built first. The agent was built second, as an improvement on measured limitations of the workflow. This sequence -- simple first, complex only when justified -- is not just good engineering. It is the only way to know whether the complexity is justified.

## When autonomy genuinely adds value

Lest this chapter read as anti-agent, here are the conditions where autonomy is the right choice.

**Open-ended research tasks.** When the user asks a question and you genuinely do not know what information will be needed or where it will be found, an agent's ability to search, assess, and search again is valuable. Research assistants, competitive analysis, and literature review are good agent candidates.

**Multi-system orchestration.** When the task requires interacting with multiple external systems (databases, APIs, file systems) and the sequence of interactions depends on intermediate results, an agent's decision-making is useful. But verify that the sequence is genuinely data-dependent, not just long.

**Adversarial or dynamic environments.** When the task involves navigating a changing environment where the right action depends on observations that cannot be predicted -- game playing, interactive testing, adaptive negotiation -- agents are the right tool.

**Tasks where exploration has value.** When trying multiple approaches and comparing results is better than committing to one approach -- creative tasks, optimization, hypothesis testing -- the agent's loop provides the structure for exploration.

Notice the common thread: the task requires decisions that depend on intermediate observations that cannot be predicted at design time. If the decisions can be predicted, use a workflow. If they cannot, use an agent. This is the simplest, most reliable heuristic for the build/do not build decision.

## The cost of getting it wrong in each direction

**Building an agent when you need a workflow** is the more common mistake. The costs: higher per-request expense, slower responses, harder testing, more complex operations, and an architecture that is harder to explain and audit. The benefit: none, because the agent is not using its autonomy for anything the workflow cannot do.

**Building a workflow when you need an agent** is less common but also costly. The costs: the system cannot handle the cases that require adaptive reasoning. Users hit these cases and get poor results or escalations that require human intervention. The benefit: simpler, cheaper system for the cases it handles well.

The asymmetry is important. Building an agent when you need a workflow costs you on every request. Building a workflow when you need an agent costs you only on the requests the workflow cannot handle. This is why "workflow first, agent second" is the safer default. The downside of starting simple is bounded. The downside of starting complex is unbounded.

## Principles for the decision

1. **Start with the simplest architecture that could work.** LLM app before workflow. Workflow before tool-using system. Tool-using system before agent. Agent before multi-agent. Move right only when you have measured evidence that the current architecture is insufficient.

2. **Measure before you move.** Do not add autonomy because you think you need it. Add it because you have run evaluation and the current system fails on a specific, quantified set of cases that the more complex architecture handles.

3. **Account for the full cost.** Not just the token cost, but the engineering cost of building, testing, operating, debugging, and governing the more complex system. A system that costs 3x more to run and 5x more to maintain needs to be 8x more valuable.

4. **Evaluate continuously.** The decision is not permanent. Your query distribution will change. Your document corpus will change. Your model provider will update their models. Re-run the comparison periodically. What was an agent-worthy task last quarter may be a workflow task this quarter (because retrieval improved) or vice versa (because the query distribution shifted).

5. **Design for demotion.** Build your agent so that the agent loop can be disabled, leaving a workflow. This lets you A/B test, fall back during incidents, and re-evaluate the decision without a rewrite. The `ComparisonRunner` in Chapter 3 shows this structure: both implementations share components and differ only in the orchestration layer.

6. **Respect the humans.** For high-stakes decisions, the right amount of autonomy is often "suggest, do not decide." The LLM surfaces information and proposes actions. The human reviews and approves. This is not a failure of automation. It is appropriate system design for tasks where the cost of a wrong autonomous decision exceeds the cost of a human review step.

## Further reading

- **"Do You Need an Agent?"** (Chip Huyen) -- A practical framework for evaluating whether a task needs agentic architecture. Independently arrives at many of the same conclusions as this chapter.
- **"Simple Made Easy"** (Rich Hickey, 2011) -- Not about AI, but the best articulation of why simplicity is a feature, not a compromise. The talk is 60 minutes well spent for anyone building complex systems.
- **"An Opinionated Guide to LLM Frameworks"** -- Compares the complexity and abstraction tradeoffs of major LLM frameworks. Useful for understanding what frameworks hide and whether that hiding helps or hurts your specific use case.
- **The original RAG paper** (Lewis et al., 2020) -- Worth reading to understand how much capability a non-agentic retrieval-augmented system provides. Many tasks attributed to "agents" are actually well-scoped RAG systems.

## Closing

This book started with a taxonomy and ends with a judgment call. The five chapters form a progression: understand the options, build the components, compare the architectures, harden the system, and decide when to use each approach.

The Document Intelligence Agent was the vehicle for this progression. We built it as a workflow. We built it as an agent. We evaluated both. We hardened both. And we concluded that for this task, the right answer is mostly the workflow, with the agent as an escalation path for the cases the workflow cannot handle.

Your task will be different. Your documents will be different. Your query distribution will be different. The specific answer will be different. But the process -- build simple, measure, add complexity only when justified, measure again -- is universal.

The engineers who build the most durable, trustworthy AI systems will not be the ones who build the most sophisticated agents. They will be the ones who know when a workflow is enough and when an agent is worth the cost. That judgment -- earned through building, measuring, and comparing -- is what separates serious engineering from impressive demos.
