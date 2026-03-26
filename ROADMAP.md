# Roadmap

---

## Shipped (Phase 1 + Phase 2)

Both phases are complete. The full foundation is solid.

- **7 chapters** covering definitions, tool design, workflow-vs-agent architecture, multi-agent systems, human-in-the-loop, evaluation and hardening, and the judgment chapter on when not to use agents
- **Working code** for every concept: tool registry, context pipeline, agent loop, workflow implementation, bounded agent, state management, multi-agent orchestration, approval gates, escalation engine, audit logging, eval harness, tracer, reliability hardening, cost profiler, security hardening
- **2 end-to-end projects**: Document Intelligence Agent and Incident Runbook Agent
- **Eval harness** with gold dataset, rubric, scored comparison script, and failure buckets
- **52+ passing tests** across unit and integration suites
- **9 architecture-grade diagrams** (hand-crafted SVGs)
- **MkDocs Material site** at [sunilprakash.com/agentic-ai](https://sunilprakash.com/agentic-ai/)
- **Infrastructure**: pyproject.toml, Makefile, .env.example, MIT license

## Next (Phase 3 -- Advanced Topics)

Phase 3 goes deeper into governance, interoperability, and long-running agent systems. Directions, not promises.

- **Deeper security chapter** -- standalone treatment of prompt injection, tool abuse, data exfiltration, and policy enforcement at scale
- **Governance and auditability** -- audit trails, decision logging, compliance boundaries
- **Bridge chapter** -- how agent systems fit into enterprise operating models

## Future (Phase 4 -- Advanced)

Phase 4 covers the harder problems that emerge once you have production agent systems running.

- **Protocols and interoperability** -- how agent systems communicate across boundaries
- **Durable execution** -- long-running agents, checkpointing, resume-after-failure at scale
- **Advanced memory systems** -- beyond session state: long-term memory, retrieval-augmented memory, forgetting
- **Evaluation at scale** -- evaluating agent systems across hundreds of tasks, regression detection, continuous eval
- **Remaining projects**: Data Analyst Agent, Policy Controls Agent, Multi-Agent Research System

---

Content ships when it meets the quality bar. No timelines promised.
