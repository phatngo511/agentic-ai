---
hide:
  - navigation
  - toc
---

# Agentic AI for Serious Engineers

**A practical field guide to building reliable, evaluable, and production-grade agent systems**

Most agentic AI material teaches you how to make an impressive demo. This book teaches engineers how to build agent systems that survive real-world constraints.

This is written for backend engineers, platform engineers, and staff+ engineers who understand distributed systems, reliability, and the cost of complexity -- but are relatively new to AI. You do not need a machine learning background. You need the judgment to know when AI helps and when it makes things worse.

What makes this different is the engineering-first approach. Every concept comes with failure modes, tradeoffs against alternatives, and evaluation criteria. There is no vibes-based testing, no "just prompt it better" advice, and no framework worship. The goal is transferable understanding: principles that hold regardless of which SDK ships next month.

## Chapters

| # | Chapter | What you learn |
|---|---------|----------------|
| 1 | [What "Agentic" Actually Means](book/01-what-agentic-means.md) | Precise vocabulary: LLM app vs workflow vs agent vs multi-agent |
| 2 | [Tools, Context, and the Agent Loop](book/02-tools-context-agent-loop.md) | Building blocks: tool registry, context engineering, observe-think-act |
| 3 | [Workflow-First, Agent-Second](book/03-workflow-first-agent-second.md) | The most important architectural decision |
| 4 | [Multi-Agent Systems Without Theater](book/04-multi-agent-without-theater.md) | When multiple agents help and when they are complexity theater |
| 5 | [Human-in-the-Loop as Architecture](book/05-human-in-the-loop.md) | Approval gates, escalation, and auditability |
| 6 | [Evaluating and Hardening Agent Systems](book/06-evaluating-and-hardening.md) | Eval harnesses, tracing, reliability, cost, security |
| 7 | [When Not to Use Agents](book/07-when-not-to-use-agents.md) | The signature chapter -- judgment over hype |

## Learning Paths

| Path | Chapters | Time |
|------|----------|------|
| **Fast Engineer** | 1, 2, 7 | ~1 hour |
| **Full Mastery** | 1 through 7 in order | ~4 hours |
| **Enterprise Architect** | 1, 3, 5, 6, 7 | ~2.5 hours |

## Projects

Two end-to-end systems built incrementally through the chapters:

- **[Document Intelligence Agent](projects/doc-intelligence-agent.md)** -- Ingest documents, retrieve evidence, answer with citations, escalate on uncertainty
- **[Incident Runbook Agent](projects/incident-runbook-agent.md)** -- Inspect signals, search runbooks, propose remediation, request human approval

---

[GitHub Repository](https://github.com/sunilp/agentic-ai-for-serious-engineers) | [sunilprakash.com](https://sunilprakash.com)
