"""Chunker tool -- splits documents into retrieval-friendly chunks."""

from __future__ import annotations

from pydantic import BaseModel

from code.shared.types import ToolSchema, ToolParameter, SideEffect


SCHEMA = ToolSchema(
    name="chunk_document",
    description="Split document text into chunks for retrieval.",
    parameters=[
        ToolParameter(name="text", type="string", description="The document text to chunk"),
        ToolParameter(name="source", type="string", description="Source identifier"),
        ToolParameter(name="chunk_size", type="integer", description="Target chunk size in characters", required=False),
        ToolParameter(name="overlap", type="integer", description="Overlap between chunks in characters", required=False),
    ],
    side_effect=SideEffect.READ,
)


class Chunk(BaseModel):
    """A single chunk of text with metadata for retrieval."""
    chunk_id: str
    text: str
    source: str
    start_char: int
    end_char: int


def chunk_document(
    text: str,
    source: str,
    chunk_size: int = 1000,
    overlap: int = 200,
) -> list[Chunk]:
    """Split text into overlapping chunks."""
    if not text.strip():
        return []

    chunks: list[Chunk] = []
    start = 0
    chunk_index = 0

    while start < len(text):
        end = start + chunk_size

        # Try to break at a paragraph boundary
        if end < len(text):
            newline_pos = text.rfind("\n\n", start, end)
            if newline_pos > start + chunk_size // 2:
                end = newline_pos

        chunk_text = text[start:end].strip()
        if chunk_text:
            chunks.append(Chunk(
                chunk_id=f"{source}::chunk_{chunk_index}",
                text=chunk_text,
                source=source,
                start_char=start,
                end_char=end,
            ))
            chunk_index += 1

        start = end - overlap
        if start >= len(text):
            break

    return chunks


async def chunk_document_tool(text: str, source: str, chunk_size: int = 1000, overlap: int = 200) -> str:
    """Tool-compatible wrapper that returns a string summary."""
    chunks = chunk_document(text, source, chunk_size, overlap)
    return f"Created {len(chunks)} chunks from '{source}'"
