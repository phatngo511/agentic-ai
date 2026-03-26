"""Side-by-side comparison: workflow vs agent on the same task."""

from __future__ import annotations

from src.ch02.tool_registry import ToolRegistry
from src.ch02.tools.retriever import DocumentIndex
from src.ch03.agent import BoundedDocumentAgent
from src.ch03.workflow import DocumentWorkflow
from src.shared.model_client import ModelClient
from src.shared.types import AgentResponse


class ComparisonRunner:
    """Runs both workflow and agent on the same queries and collects metrics."""

    def __init__(self, client: ModelClient, index: DocumentIndex):
        self._workflow = DocumentWorkflow(client=client, index=index)
        self._agent = BoundedDocumentAgent(
            client=client,
            index=index,
            registry=ToolRegistry(),
            max_steps=5,
        )

    async def compare(self, queries: list[str]) -> list[ComparisonResult]:
        results = []
        for query in queries:
            workflow_resp = await self._workflow.run(query)
            agent_resp = await self._agent.run(query)
            results.append(ComparisonResult(
                query=query,
                workflow=workflow_resp,
                agent=agent_resp,
            ))
        return results

    @staticmethod
    def print_results(results: list[ComparisonResult]) -> None:
        print(f"\n{'='*80}")
        print("WORKFLOW vs AGENT COMPARISON")
        print(f"{'='*80}\n")

        for r in results:
            print(f"Query: {r.query}")
            print(f"  {'Metric':<20} {'Workflow':<30} {'Agent':<30}")
            print(f"  {'-'*20} {'-'*30} {'-'*30}")
            print(f"  {'Steps':<20} {r.workflow.steps_taken:<30} {r.agent.steps_taken:<30}")
            print(f"  {'Tokens':<20} {r.workflow.token_usage.total_tokens:<30} {r.agent.token_usage.total_tokens:<30}")
            print(f"  {'Latency (ms)':<20} {r.workflow.latency_ms:<30.0f} {r.agent.latency_ms:<30.0f}")
            print(f"  {'Confidence':<20} {r.workflow.confidence:<30.2f} {r.agent.confidence:<30.2f}")
            print(f"  {'Escalated':<20} {str(r.workflow.escalated):<30} {str(r.agent.escalated):<30}")
            print()

        w_tokens = sum(r.workflow.token_usage.total_tokens for r in results)
        a_tokens = sum(r.agent.token_usage.total_tokens for r in results)
        w_latency = sum(r.workflow.latency_ms for r in results)
        a_latency = sum(r.agent.latency_ms for r in results)

        print(f"{'='*80}")
        print(f"TOTALS ({len(results)} queries)")
        print(f"  Workflow: {w_tokens} tokens, {w_latency:.0f}ms total")
        print(f"  Agent:    {a_tokens} tokens, {a_latency:.0f}ms total")
        print(f"  Agent overhead: {a_tokens - w_tokens} tokens, {a_latency - w_latency:.0f}ms")
        print(f"{'='*80}\n")


class ComparisonResult:
    def __init__(self, query: str, workflow: AgentResponse, agent: AgentResponse):
        self.query = query
        self.workflow = workflow
        self.agent = agent
