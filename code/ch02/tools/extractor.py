"""Extractor tool -- pulls structured data from text using an LLM."""

from __future__ import annotations

from typing import Any

from code.shared.model_client import ModelClient
from code.shared.types import (
    CompletionRequest,
    Message,
    Role,
    ToolSchema,
    ToolParameter,
    SideEffect,
)


SCHEMA = ToolSchema(
    name="extract_structured",
    description="Extract structured information from text according to a specified schema.",
    parameters=[
        ToolParameter(name="text", type="string", description="Source text to extract from"),
        ToolParameter(name="fields", type="string", description="Comma-separated list of fields to extract"),
    ],
    side_effect=SideEffect.READ,
)


EXTRACTION_PROMPT = """Extract the following fields from the provided text.
Return a JSON object with exactly these fields: {fields}

Rules:
- Only extract information that is explicitly stated in the text.
- If a field cannot be determined from the text, set it to null.
- Do not infer or guess values. If unsure, use null.
- Return valid JSON only, no markdown formatting.

Text:
{text}"""


async def extract_structured(
    text: str,
    fields: str,
    client: ModelClient,
) -> dict[str, Any]:
    """Extract structured fields from text using an LLM."""
    import json

    request = CompletionRequest(
        messages=[
            Message(role=Role.SYSTEM, content="You are a precise information extractor. Return only valid JSON."),
            Message(role=Role.USER, content=EXTRACTION_PROMPT.format(fields=fields, text=text)),
        ],
        temperature=0.0,
        response_format={"type": "json_object"},
    )

    response = await client.complete(request)
    if not response.content:
        return {field.strip(): None for field in fields.split(",")}

    return json.loads(response.content)
