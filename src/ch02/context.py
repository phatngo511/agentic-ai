"""Context assembly pipeline.

This is where you control what the model sees before it reasons.
The quality of the context directly determines the quality of the output.
"""

from __future__ import annotations

from src.shared.types import Citation, Message, Role


SYSTEM_PROMPT = """You are a document intelligence assistant. Your job is to answer questions
based strictly on the provided evidence.

Rules:
- Only use information from the provided document excerpts.
- Cite your sources using [Source: filename] notation.
- If the evidence does not contain enough information to answer confidently,
  say so explicitly. Do not guess or use your training knowledge.
- If you are uncertain, explain what you found and what is missing.
- Be precise and concise. Engineers are reading this."""


EVIDENCE_TEMPLATE = """Here are the relevant document excerpts:

{evidence}

---
Each excerpt includes its source. Use [Source: filename] when citing."""


NO_EVIDENCE_NOTE = """No relevant document excerpts were found for this query.
If you cannot answer without evidence, say so clearly."""


class ContextPipeline:
    """Assembles the full context for the model from query + retrieved evidence."""

    def __init__(self, system_prompt: str = SYSTEM_PROMPT):
        self._system_prompt = system_prompt

    def build(
        self,
        query: str,
        citations: list[Citation],
        conversation_history: list[Message] | None = None,
    ) -> list[Message]:
        """Build the full message list for a completion request."""
        messages: list[Message] = []

        messages.append(Message(role=Role.SYSTEM, content=self._system_prompt))

        if conversation_history:
            messages.extend(conversation_history)

        if citations:
            evidence_text = self._format_citations(citations)
            user_content = f"{EVIDENCE_TEMPLATE.format(evidence=evidence_text)}\n\nQuestion: {query}"
        else:
            user_content = f"{NO_EVIDENCE_NOTE}\n\nQuestion: {query}"

        messages.append(Message(role=Role.USER, content=user_content))

        return messages

    def _format_citations(self, citations: list[Citation]) -> str:
        """Format citations into a readable evidence block."""
        parts = []
        for i, c in enumerate(citations, 1):
            source_label = c.source
            if c.page is not None:
                source_label += f", page {c.page}"
            parts.append(f"[Excerpt {i}] (Source: {source_label}, relevance: {c.relevance_score:.2f})\n{c.text}")
        return "\n\n".join(parts)
