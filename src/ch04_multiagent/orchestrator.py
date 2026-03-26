"""Multi-agent orchestrator for document intelligence.

Coordinates three agents: retriever -> reasoner -> verifier.
If verification fails, re-dispatches to the reasoner with feedback.
Max 2 verification rounds to prevent infinite loops.
"""

from __future__ import annotations

import time

from src.ch02.tools.retriever import DocumentIndex
from src.ch04_multiagent.agents import ReasoningAgent, RetrieverAgent, VerifierAgent
from src.ch04_multiagent.contracts import (
    ReasoningRequest,
    RetrievalRequest,
    VerificationRequest,
)
from src.shared.model_client import ModelClient
from src.shared.types import AgentResponse, TokenUsage


class MultiAgentOrchestrator:
    """Coordinates retriever, reasoner, and verifier agents."""

    def __init__(
        self,
        client: ModelClient,
        index: DocumentIndex,
        max_verification_rounds: int = 2,
    ):
        self._retriever = RetrieverAgent(index)
        self._reasoner = ReasoningAgent(client)
        self._verifier = VerifierAgent(client)
        self._max_rounds = max_verification_rounds

    async def run(self, query: str, top_k: int = 5) -> AgentResponse:
        start = time.monotonic()
        steps = 0

        # Step 1: Retrieve
        retrieval = await self._retriever.run(RetrievalRequest(query=query, top_k=top_k))
        steps += 1

        # Step 2: Reason
        reasoning = await self._reasoner.run(
            ReasoningRequest(query=query, citations=retrieval.citations)
        )
        steps += 1

        # Step 3: Verify (with retry loop)
        verified = False
        verification_rounds = 0

        while not verified and verification_rounds < self._max_rounds:
            verification = await self._verifier.run(
                VerificationRequest(
                    answer=reasoning.answer,
                    cited_sources=reasoning.cited_sources,
                    citations=retrieval.citations,
                )
            )
            steps += 1
            verification_rounds += 1

            if verification.verified:
                verified = True
            else:
                # Re-reason with feedback
                feedback_query = (
                    f"{query}\n\nPrevious answer had issues: {', '.join(verification.issues)}. "
                    f"Please correct and re-answer using only the provided evidence."
                )
                reasoning = await self._reasoner.run(
                    ReasoningRequest(query=feedback_query, citations=retrieval.citations)
                )
                steps += 1

        elapsed = (time.monotonic() - start) * 1000
        total_usage = _merge_all_usage(
            self._retriever.total_usage,
            self._reasoner.total_usage,
            self._verifier.total_usage,
        )

        avg_relevance = (
            sum(c.relevance_score for c in retrieval.citations) / len(retrieval.citations)
            if retrieval.citations
            else 0.0
        )

        confidence = min(0.95, avg_relevance) if verified else avg_relevance * 0.5

        return AgentResponse(
            answer=reasoning.answer,
            citations=retrieval.citations,
            confidence=confidence,
            escalated=confidence < 0.3,
            escalation_reason="Low confidence after multi-agent pipeline"
            if confidence < 0.3
            else None,
            steps_taken=steps,
            token_usage=total_usage,
            latency_ms=elapsed,
        )


def _merge_all_usage(*usages: TokenUsage) -> TokenUsage:
    return TokenUsage(
        prompt_tokens=sum(u.prompt_tokens for u in usages),
        completion_tokens=sum(u.completion_tokens for u in usages),
        total_tokens=sum(u.total_tokens for u in usages),
    )
