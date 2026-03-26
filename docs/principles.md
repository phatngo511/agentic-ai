---
description: "Core engineering principles behind the book: workflow-first design, failure-mode thinking, evaluation over vibes, and judgment over hype."
---

# Engineering Principles

These principles shape every chapter, every code example, and every design decision in this book. They are not aspirational. They are constraints.

---

## 1. Why before how

Every topic starts with the engineering reason it matters. Before you see an API call or a code sample, you understand the problem being solved and why the obvious approaches fail. "How" without "why" produces engineers who can follow instructions but cannot adapt when the instructions stop applying. The goal is transferable understanding, not recipe execution.

## 2. What breaks before what works

Failure modes are first-class, not an afterthought section at the bottom. Engineers learn fastest when they understand what can go wrong, because production systems spend most of their life in degraded states, edge cases, and partial failures. Every concept is taught alongside the ways it fails, so you build with those failure surfaces in mind from the start.

## 3. Compare alternatives

No design decision is presented in isolation. Workflow vs agent, single-model vs multi-model, cheap model vs expensive, plan-and-execute vs direct response -- every choice is framed against the thing you would do instead. Engineering is about tradeoffs. If you only see one option, you are not making a decision; you are following a path someone else chose for you.

## 4. Evaluation is mandatory

If you cannot evaluate a system, you do not understand it well enough to ship it. Evaluation is not a phase that happens after building; it is a design constraint that shapes how you build. Every system in this book ships with an eval harness, gold data, rubrics, and failure buckets. Vibes-based testing is not engineering.

## 5. Security boundaries live outside the model

Prompts can be manipulated. Instructions can be overridden. Retrieval context can be poisoned. The only security boundaries that hold are the ones enforced in code, not in the model's context window. This book treats prompt injection as a given, not a theoretical risk, and builds defenses in application logic, tool permissions, and policy enforcement layers.

## 6. Concepts over frameworks

Frameworks change every six months. Concepts survive. This book teaches ideas -- tool contracts, context engineering, evaluation design, trust boundaries, autonomy budgets -- using implementations that make the concept visible. Where frameworks appear, they illustrate a concept, not the other way around. An engineer who reads this should make better decisions regardless of which SDK they use next year.

## 7. Explicit tradeoffs over black-box abstractions

Every abstraction has a cost: latency, token spend, debuggability, vendor lock-in, failure opacity. This book surfaces those costs rather than hiding them behind convenience wrappers. When you choose an architecture, you should know what you are paying and what you are getting. Hidden complexity does not disappear; it just shows up at 2am in production.

## 8. Simpler systems win until proven otherwise

The default is a workflow. The default is a single model call. The default is deterministic logic. Agents, multi-agent systems, and autonomous loops must justify their complexity with measurable value that simpler approaches cannot deliver. This is not anti-agent -- it is pro-judgment. The signature chapter of this book teaches you when not to build an agent, because that decision will save you more time and money than any framework ever will.
