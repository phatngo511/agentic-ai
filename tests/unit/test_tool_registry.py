"""Tests for the tool registry."""

import pytest

from src.ch02.tool_registry import ToolRegistry
from src.shared.types import SideEffect, ToolParameter, ToolSchema


@pytest.fixture
def registry() -> ToolRegistry:
    r = ToolRegistry()

    async def echo_tool(text: str) -> str:
        return f"echo: {text}"

    r.register(
        schema=ToolSchema(
            name="echo",
            description="Echoes input text",
            parameters=[
                ToolParameter(name="text", type="string", description="Text to echo"),
            ],
            side_effect=SideEffect.READ,
        ),
        handler=echo_tool,
    )
    return r


@pytest.mark.asyncio
async def test_execute_valid_tool(registry: ToolRegistry):
    result = await registry.execute("echo", {"text": "hello"})
    assert result.success is True
    assert result.content == "echo: hello"


@pytest.mark.asyncio
async def test_execute_unknown_tool(registry: ToolRegistry):
    result = await registry.execute("nonexistent", {})
    assert result.success is False
    assert "not found" in result.error.lower()


@pytest.mark.asyncio
async def test_execute_missing_required_arg(registry: ToolRegistry):
    result = await registry.execute("echo", {})
    assert result.success is False
    assert "text" in result.error.lower()


def test_list_tools(registry: ToolRegistry):
    tools = registry.list_tools()
    assert len(tools) == 1
    assert tools[0].name == "echo"


def test_get_tool_schema(registry: ToolRegistry):
    schema = registry.get_schema("echo")
    assert schema is not None
    assert schema.name == "echo"


def test_get_unknown_schema(registry: ToolRegistry):
    assert registry.get_schema("nonexistent") is None


@pytest.mark.asyncio
async def test_execution_log(registry: ToolRegistry):
    await registry.execute("echo", {"text": "test"})
    log = registry.get_execution_log()
    assert len(log) == 1
    assert log[0]["tool_name"] == "echo"
    assert log[0]["success"] is True
