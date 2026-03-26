# Roadmap

---

## Shipped (Phase 1)

Phase 1 is complete. The foundation is solid.

- **5 chapters** covering definitions, tool design, workflow-vs-agent architecture, evaluation and hardening, and the judgment chapter on when not to use agents
- **Working code** for every concept: tool registry, context pipeline, agent loop, workflow implementation, bounded agent, state management, eval harness, tracer, reliability hardening, cost profiler, security hardening
- **Document Intelligence Agent** -- one threaded project built incrementally across all chapters, with architecture docs and failure analysis
- **Eval harness** with gold dataset, rubric, scored comparison script, and failure buckets
- **27 passing tests** across unit and integration suites
- **Architecture diagram** (system-level SVG)
- **Infrastructure**: pyproject.toml, Makefile, .env.example, MIT license

## Next (Phase 2 -- Architecture and Production Depth)

Phase 2 goes deeper into systems that involve multiple agents, human oversight, and production governance. Directions, not promises.

- **Multi-agent systems without theater** -- coordination patterns that solve real problems, not demos with five agents talking to each other
- **State graphs and orchestration** -- explicit state machines for agent control flow
- **Human-in-the-loop as architecture** -- designing systems where human oversight is a first-class component, not a bolt-on
- **Deeper security chapter** -- standalone treatment of prompt injection, tool abuse, data exfiltration, and policy enforcement at scale
- **Governance and auditability** -- audit trails, decision logging, compliance boundaries
- **Bridge chapter** -- how agent systems fit into enterprise operating models
- **2 more projects**: Codebase Analyst, Incident Runbook Agent

## Future (Phase 3 -- Advanced)

Phase 3 covers the harder problems that emerge once you have production agent systems running.

- **Protocols and interoperability** -- how agent systems communicate across boundaries
- **Durable execution** -- long-running agents, checkpointing, resume-after-failure at scale
- **Advanced memory systems** -- beyond session state: long-term memory, retrieval-augmented memory, forgetting
- **Evaluation at scale** -- evaluating agent systems across hundreds of tasks, regression detection, continuous eval
- **Remaining projects**: Data Analyst Agent, Policy Controls Agent, Multi-Agent Research System

---

Content ships when it meets the quality bar. No timelines promised.
