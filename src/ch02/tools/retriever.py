"""Retriever tool -- finds relevant chunks for a query using vector similarity."""

from __future__ import annotations

import chromadb
from chromadb.config import Settings as ChromaSettings

from src.ch02.tools.chunker import Chunk
from src.shared.types import Citation, ToolSchema, ToolParameter, SideEffect


SCHEMA = ToolSchema(
    name="retrieve",
    description="Search indexed documents for chunks relevant to a query.",
    parameters=[
        ToolParameter(name="query", type="string", description="The search query"),
        ToolParameter(name="top_k", type="integer", description="Number of results to return", required=False),
    ],
    side_effect=SideEffect.READ,
)


class DocumentIndex:
    """Manages a vector index of document chunks."""

    def __init__(self, collection_name: str = "documents"):
        self._client = chromadb.Client(ChromaSettings(anonymized_telemetry=False))
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def add_chunks(self, chunks: list[Chunk]) -> None:
        """Add chunks to the index."""
        if not chunks:
            return
        self._collection.add(
            ids=[c.chunk_id for c in chunks],
            documents=[c.text for c in chunks],
            metadatas=[{"source": c.source, "start_char": c.start_char, "end_char": c.end_char} for c in chunks],
        )

    def retrieve(self, query: str, top_k: int = 5) -> list[Citation]:
        """Find the most relevant chunks for a query."""
        results = self._collection.query(
            query_texts=[query],
            n_results=min(top_k, self._collection.count() or 1),
        )

        citations = []
        for i, doc in enumerate(results["documents"][0]):
            meta = results["metadatas"][0][i]
            distance = results["distances"][0][i] if results.get("distances") else 0.0
            citations.append(Citation(
                source=meta["source"],
                chunk_id=results["ids"][0][i],
                text=doc,
                relevance_score=1.0 - distance,
            ))

        return citations

    def clear(self) -> None:
        """Remove all documents from the index."""
        self._client.delete_collection(self._collection.name)
        self._collection = self._client.get_or_create_collection(
            name=self._collection.name,
            metadata={"hnsw:space": "cosine"},
        )
