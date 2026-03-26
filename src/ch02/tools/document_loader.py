"""Document loader tool -- ingests PDF, markdown, and text files."""

from __future__ import annotations

from pathlib import Path

from src.shared.types import SideEffect, ToolParameter, ToolSchema

SCHEMA = ToolSchema(
    name="load_document",
    description="Load a document from a file path. Supports PDF, markdown, and plain text.",
    parameters=[
        ToolParameter(name="file_path", type="string", description="Path to the document file"),
    ],
    side_effect=SideEffect.READ,
)


async def load_document(file_path: str) -> str:
    """Load and return the text content of a document."""
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Document not found: {file_path}")

    if path.suffix == ".pdf":
        return _load_pdf(path)
    elif path.suffix in (".md", ".markdown"):
        return path.read_text(encoding="utf-8")
    elif path.suffix in (".txt", ".text", ""):
        return path.read_text(encoding="utf-8")
    else:
        raise ValueError(f"Unsupported file format: {path.suffix}")


def _load_pdf(path: Path) -> str:
    """Extract text from a PDF file."""
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if text:
            pages.append(f"[Page {i + 1}]\n{text}")
    return "\n\n".join(pages)
