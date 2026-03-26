"""Tests for the context assembly pipeline."""

from src.ch02.context import ContextPipeline
from src.shared.types import Citation, Role


def test_build_system_prompt():
    pipeline = ContextPipeline()
    messages = pipeline.build(query="test", citations=[])
    system = messages[0]
    assert system.role == Role.SYSTEM
    assert "document intelligence" in system.content.lower()


def test_build_includes_citations():
    pipeline = ContextPipeline()
    citations = [
        Citation(source="test.pdf", text="The answer is 42.", relevance_score=0.9),
    ]
    messages = pipeline.build(query="what is the answer?", citations=citations)
    full_text = " ".join(m.content for m in messages)
    assert "The answer is 42." in full_text
    assert "test.pdf" in full_text


def test_build_includes_query():
    pipeline = ContextPipeline()
    messages = pipeline.build(query="what is the answer?", citations=[])
    user_msgs = [m for m in messages if m.role == Role.USER]
    assert any("what is the answer?" in m.content for m in user_msgs)


def test_empty_citations_still_works():
    pipeline = ContextPipeline()
    messages = pipeline.build(query="hello", citations=[])
    assert len(messages) >= 2
    assert messages[0].role == Role.SYSTEM
