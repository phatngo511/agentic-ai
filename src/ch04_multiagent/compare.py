"""Single-agent vs multi-agent comparison runner."""

from __future__ import annotations

from src.ch02.tools.retriever import DocumentIndex
from src.ch03.agent import BoundedDocumentAgent
from src.ch02.tool_registry import ToolRegistry
from src.ch04_multiagent.orchestrator import MultiAgentOrchestrator
from src.shared.model_client import ModelClient
from src.shared.types import AgentResponse


class MultiAgentComparisonRunner:
    """Runs single-agent and multi-agent on the same queries."""

    def __init__(self, client: ModelClient, index: DocumentIndex):
        self._single = BoundedDocumentAgent(
            client=client, index=index, registry=ToolRegistry(), max_steps=5
        )
        self._multi = MultiAgentOrchestrator(client=client, index=index)

    async def compare(self, queries: list[str]) -> list[ComparisonResult]:
        results = []
        for query in queries:
            single_resp = await self._single.run(query)
            multi_resp = await self._multi.run(query)
            results.append(ComparisonResult(query=query, single_agent=single_resp, multi_agent=multi_resp))
        return results

    @staticmethod
    def print_results(results: list[ComparisonResult]) -> None:
        print(f"\n{'='*80}")
        print("SINGLE-AGENT vs MULTI-AGENT COMPARISON")
        print(f"{'='*80}\n")

        for r in results:
            print(f"Query: {r.query}")
            print(f"  {'Metric':<20} {'Single Agent':<30} {'Multi Agent':<30}")
            print(f"  {'-'*20} {'-'*30} {'-'*30}")
            print(f"  {'Steps':<20} {r.single_agent.steps_taken:<30} {r.multi_agent.steps_taken:<30}")
            print(f"  {'Tokens':<20} {r.single_agent.token_usage.total_tokens:<30} {r.multi_agent.token_usage.total_tokens:<30}")
            print(f"  {'Latency (ms)':<20} {r.single_agent.latency_ms:<30.0f} {r.multi_agent.latency_ms:<30.0f}")
            print(f"  {'Confidence':<20} {r.single_agent.confidence:<30.2f} {r.multi_agent.confidence:<30.2f}")
            print()

        s_tokens = sum(r.single_agent.token_usage.total_tokens for r in results)
        m_tokens = sum(r.multi_agent.token_usage.total_tokens for r in results)
        print(f"{'='*80}")
        print(f"TOTALS ({len(results)} queries)")
        print(f"  Single: {s_tokens} tokens")
        print(f"  Multi:  {m_tokens} tokens")
        print(f"  Multi overhead: {m_tokens - s_tokens} tokens ({(m_tokens / max(s_tokens, 1) - 1) * 100:.0f}% more)")
        print(f"{'='*80}\n")


class ComparisonResult:
    def __init__(self, query: str, single_agent: AgentResponse, multi_agent: AgentResponse):
        self.query = query
        self.single_agent = single_agent
        self.multi_agent = multi_agent
