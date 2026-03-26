# Agentic AI for Serious Engineers

**Build trustworthy AI systems, not demos.**

---

## Thesis

Most material on AI agents teaches you how to build one. This book teaches you when to build one, and -- more importantly -- when not to. It threads a single project from first principles through production hardening, using working Python code that you can read, run, and adapt. The emphasis is on engineering judgment: understanding failure surfaces before you encounter them, choosing the simplest architecture that solves the problem, and building evaluation into the system from the start rather than bolting it on at the end.

## Who This Is For

You are a software engineer, ML engineer, or technical architect who:

- Has built software systems in production and understands why they break
- Wants to use LLMs as components inside larger systems, not as toys
- Needs to make informed decisions about when autonomy adds value and when it adds risk
- Prefers working code over slide decks, and honest tradeoff analysis over hype

**Who this is not for:** If you are looking for a tutorial on prompt engineering, a survey of agent frameworks, or an argument that agents will change everything, this is not that book. If you want to understand the engineering beneath the abstractions, read on.

## Learning Paths

Not everyone needs to read every chapter in order. Here are three paths depending on your goal.

### The Fast Engineer Path

You want to build something this week with a clear understanding of the tradeoffs.

1. **Chapter 1** -- Understand the taxonomy: what is and is not an agent
2. **Chapter 2** -- Build the tools, context pipeline, and agent loop
3. **Chapter 5** -- Learn when to step back from agents entirely

### The Full Mastery Path

You want to understand every layer, from concepts through production hardening.

1. **Chapter 1** -- Definitions and decision framework
2. **Chapter 2** -- Tools, context, and the agent loop
3. **Chapter 3** -- Workflow-first architecture and bounded agents
4. **Chapter 4** -- Evaluation, reliability, cost, and security
5. **Chapter 5** -- When not to build an agent

### The Enterprise Architect Path

You are evaluating agentic patterns for a team or organization.

1. **Chapter 1** -- Decision map: which pattern for which problem
2. **Chapter 3** -- Workflow vs agent comparison with metrics
3. **Chapter 4** -- Evaluation, observability, and governance
4. **Chapter 5** -- The judgment chapter: when agents hurt more than they help

## Chapters

| # | Title | Focus |
|---|-------|-------|
| 1 | [What "Agentic" Actually Means](01-what-agentic-means.md) | Precise definitions, comparison table, decision map -- no code |
| 2 | [Tools, Context, and the Agent Loop](02-tools-context-agent-loop.md) | Build a working tool-using agent from typed contracts up |
| 3 | [Workflow First, Agent Second](03-workflow-first-agent-second.md) | Same task two ways; the most important architectural decision |
| 4 | [Evaluating and Hardening Agents](04-evaluating-and-hardening.md) | Eval, tracing, reliability, cost, security -- making it trustworthy |
| 5 | [When Not to Use Agents](05-when-not-to-use-agents.md) | The signature chapter: building engineering judgment |

## The Running Example: Document Intelligence Agent

Every chapter uses the same project -- a Document Intelligence Agent that ingests documents, answers questions with citations, and knows when it does not know enough to answer.

This is not a toy example. It has four layers (document, retrieval, reasoning, evaluation), real failure modes, and two implementations of the same task (deterministic workflow and bounded agent). The project code lives in `src/` and the project documentation lives in `project/doc-intelligence-agent/`.

The architecture is documented in [`project/doc-intelligence-agent/docs/architecture.md`](../project/doc-intelligence-agent/docs/architecture.md). The failure analysis is documented in [`project/doc-intelligence-agent/docs/failure-analysis.md`](../project/doc-intelligence-agent/docs/failure-analysis.md).

By the end of the book, you will have built, compared, evaluated, and hardened this system -- and you will have a clear framework for deciding whether an agent was the right choice in the first place.
