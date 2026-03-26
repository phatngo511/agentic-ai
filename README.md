# Agentic AI for Serious Engineers

**A practical field guide to building reliable, evaluable, and production-grade agent systems.**

---

Most agentic AI material teaches you how to make an impressive demo. This repo teaches engineers how to build agent systems that survive real-world constraints.

## What This Is

A deep, engineering-first guide to designing, building, evaluating, and hardening agentic AI systems. Five chapters of structured material, working Python code for every concept, and a threaded project that runs from first principles through production readiness. This is not a tutorial. It is a field manual.

## Who This Is For

Backend engineers, platform engineers, staff+ engineers, software architects, technical leads, and data engineers building AI systems for production use.

**Assumed baseline:** You know APIs, Python, software architecture, services, testing, and databases. You have built production systems and understand why they break.

**Not assumed:** Transformers in depth, embeddings and retrieval, agent orchestration, AI evaluation, agent governance. These are taught here.

## Who This Is Not For

If you are looking for a prompt engineering tutorial, a framework crash course, or a breathless argument that agents will change everything -- this is not that. If you want to build demos that impress at a meetup but fail in production, there are faster options elsewhere.

## What This Repo Teaches

- When to build an agent and when not to (the decision that matters most)
- Precise definitions: LLM app vs workflow vs tool-using system vs agent
- Tool design as typed contracts with validation, permissions, and error handling
- Context engineering: system prompts, retrieval context, grounding, injection boundaries
- The observe-think-act loop and what makes it work or fail
- Workflow-first architecture: building the same system both ways and comparing
- State management, planning, and uncertainty-based escalation
- Evaluation harnesses: gold datasets, rubric scoring, failure bucketing
- Reliability engineering: retries, checkpointing, crash recovery, cost profiling
- Security hardening: prompt injection, tool abuse, data exfiltration, least privilege
- Observability: structured traces, token accounting, latency decomposition
- Engineering judgment: knowing when simpler architectures win

## What Makes It Different

**Engineering-first.** Every topic starts with the engineering reason it matters. Not "here is the API" but "here is the problem this solves and here is what breaks when you get it wrong."

**Judgment-heavy.** The most valuable chapter teaches you when NOT to build an agent. Most material skips this because it is harder to write and less exciting to market. It is also the chapter that will save you the most time and money.

**Production-aware.** Evaluation, reliability, cost, security, and observability are not appendix topics. They are woven through every chapter because that is how production engineering works.

**Framework-neutral.** Concepts are taught through raw implementations, minimal custom orchestration, and selected frameworks. You learn ideas that survive tool churn, not one vendor's ecosystem.

**Deep but focused.** Five chapters, not twenty. Each one is dense enough to re-read and find something new. No filler sections, no padding, no "hello world" warmups.

**Serious examples.** The running project has four layers, real failure modes, two implementations of the same task, an eval harness with gold data, and an honest retrospective on which parts actually needed agent autonomy.

## The Threaded Project: Document Intelligence Agent

Every chapter uses the same system -- a Document Intelligence Agent that ingests documents, answers questions with citations, and knows when it does not have enough evidence to answer. It is introduced in Chapter 1, first built in Chapter 2, compared against a deterministic workflow in Chapter 3, evaluated and hardened in Chapter 4, and honestly assessed in Chapter 5. By the end, you will have built, compared, evaluated, and hardened this system -- and you will have a clear framework for deciding whether an agent was the right call.

## Learning Paths

| Path | Goal | Chapters |
|------|------|----------|
| **Fast Engineer** | Build something this week with clear tradeoffs | 1, 2, 5 |
| **Full Mastery** | Understand every layer from concepts through hardening | 1, 2, 3, 4, 5 |
| **Enterprise Architect** | Evaluate agentic patterns for a team or organization | 1, 3, 4, 5 |

## Chapters

| # | Title | Focus |
|---|-------|-------|
| 1 | What "Agentic" Actually Means | Definitions, comparison table, decision map |
| 2 | Tools, Context, and the Agent Loop | Tool registry, context pipeline, first working agent |
| 3 | Workflow First, Agent Second | Same task two ways -- the key architectural decision |
| 4 | Evaluating and Hardening Agents | Eval, tracing, reliability, cost, security |
| 5 | When Not to Use Agents | The signature chapter -- building engineering judgment |

## Repo Structure

```
agentic-ai-for-serious-engineers/
├── book/                          # Field manual chapters (structured markdown)
│   ├── index.md                   # Chapter overview and learning paths
│   ├── 01-what-agentic-means.md
│   ├── 02-tools-context-agent-loop.md
│   ├── 03-workflow-first-agent-second.md
│   ├── 04-evaluating-and-hardening.md
│   └── 05-when-not-to-use-agents.md
├── src/                          # Working examples, per-chapter
│   ├── shared/                    # Model client, config, common types
│   ├── ch02/                      # Tool registry, context pipeline, first agent
│   ├── ch03/                      # Workflow vs agent comparison, state, planning
│   └── ch04/                      # Eval harness, traces, reliability, security
├── project/                       # Threaded end-to-end project
│   └── doc-intelligence-agent/
│       ├── evals/                 # Gold dataset, rubric, eval runner
│       └── docs/                  # Architecture and failure analysis
├── diagrams/
│   └── source/                    # Architecture-grade SVG diagrams
├── tests/
│   ├── unit/                      # Component-level tests
│   └── integration/               # Pipeline and system tests
├── pyproject.toml                 # Dependencies (single source of truth)
├── Makefile                       # install, test, eval, run, compare
├── .env.example                   # Required environment variables
├── PRINCIPLES.md                  # Engineering principles
├── ROADMAP.md                     # What shipped, what is next
└── LICENSE                        # MIT
```

## Getting Started

```bash
# Install
make install

# Run tests (27 passing)
make test

# Run the Document Intelligence Agent
make run

# Run the eval harness
make eval
```

Copy `.env.example` to `.env` and add your API key before running.

## Principles

This repo follows eight engineering principles that shape every chapter, every code example, and every design decision. Read them: [PRINCIPLES.md](PRINCIPLES.md).

## Roadmap

Phase 1 is shipped. Phase 2 covers multi-agent systems, deeper security, governance, and two more projects. No timelines promised. Read the details: [ROADMAP.md](ROADMAP.md).

## License

MIT. See [LICENSE](LICENSE).
