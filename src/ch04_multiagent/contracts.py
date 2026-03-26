"""Message contracts for multi-agent communication.

In a multi-agent system, agents need a shared language.
Without typed contracts, you get string-passing chaos
where debugging means reading raw text dumps.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from src.shared.types import Citation


class MessageType(StrEnum):
    TASK = "task"
    RESULT = "result"
    FEEDBACK = "feedback"
    ESCALATION = "escalation"


class AgentMessage(BaseModel):
    """A typed message between agents."""

    sender: str
    recipient: str
    message_type: MessageType
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class RetrievalRequest(AgentMessage):
    """Request to the retriever agent."""

    query: str
    top_k: int = 5

    def __init__(self, **data):
        data.setdefault("sender", "orchestrator")
        data.setdefault("recipient", "retriever")
        data.setdefault("message_type", MessageType.TASK)
        data.setdefault("content", data.get("query", ""))
        super().__init__(**data)


class RetrievalResult(AgentMessage):
    """Result from the retriever agent."""

    citations: list[Citation] = Field(default_factory=list)
    chunks_searched: int = 0

    def __init__(self, **data):
        data.setdefault("sender", "retriever")
        data.setdefault("recipient", "orchestrator")
        data.setdefault("message_type", MessageType.RESULT)
        data.setdefault("content", f"Found {len(data.get('citations', []))} relevant passages")
        super().__init__(**data)


class ReasoningRequest(AgentMessage):
    """Request to the reasoning agent."""

    query: str
    citations: list[Citation] = Field(default_factory=list)

    def __init__(self, **data):
        data.setdefault("sender", "orchestrator")
        data.setdefault("recipient", "reasoner")
        data.setdefault("message_type", MessageType.TASK)
        data.setdefault("content", data.get("query", ""))
        super().__init__(**data)


class ReasoningResult(AgentMessage):
    """Result from the reasoning agent."""

    answer: str = ""
    cited_sources: list[str] = Field(default_factory=list)

    def __init__(self, **data):
        data.setdefault("sender", "reasoner")
        data.setdefault("recipient", "orchestrator")
        data.setdefault("message_type", MessageType.RESULT)
        data.setdefault("content", data.get("answer", ""))
        super().__init__(**data)


class VerificationRequest(AgentMessage):
    """Request to the verifier agent."""

    answer: str
    cited_sources: list[str] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)

    def __init__(self, **data):
        data.setdefault("sender", "orchestrator")
        data.setdefault("recipient", "verifier")
        data.setdefault("message_type", MessageType.TASK)
        data.setdefault("content", "Verify citations in answer")
        super().__init__(**data)


class VerificationResult(AgentMessage):
    """Result from the verifier agent."""

    verified: bool = False
    issues: list[str] = Field(default_factory=list)

    def __init__(self, **data):
        data.setdefault("sender", "verifier")
        data.setdefault("recipient", "orchestrator")
        data.setdefault("message_type", MessageType.RESULT)
        status = "verified" if data.get("verified", False) else "issues found"
        data.setdefault("content", status)
        super().__init__(**data)
