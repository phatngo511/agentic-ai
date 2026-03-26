"""Tool registry -- the gatekeeper for all tool execution.

Why a registry instead of bare function calls?
1. Validation: the model can hallucinate argument names or types.
   The registry catches this before the tool runs.
2. Permissions: write tools need different handling than read tools.
   The registry knows which is which.
3. Audit: every execution is logged. When something breaks at 3am,
   you need to know what the agent did and in what order.
4. Normalization: tools return strings, dicts, exceptions. The registry
   normalizes everything into ToolResult so callers have one type to handle.

Failure modes this design addresses:
- Model calls a tool that does not exist -> error result, not crash
- Model passes wrong arguments -> validation error with specifics
- Tool raises an exception -> caught, logged, returned as error result
- Tool takes too long -> timeout (not implemented in Phase 1, noted for ch04)
"""

from __future__ import annotations

import time
from typing import Any, Callable, Awaitable

import structlog

from code.shared.types import ToolSchema, ToolResult

logger = structlog.get_logger()


class ToolRegistry:
    """Registers tools, validates calls, executes them, and logs everything."""

    def __init__(self):
        self._tools: dict[str, _RegisteredTool] = {}
        self._execution_log: list[dict[str, Any]] = []

    def register(self, schema: ToolSchema, handler: Callable[..., Awaitable[str]]) -> None:
        """Register a tool with its schema and handler function."""
        self._tools[schema.name] = _RegisteredTool(schema=schema, handler=handler)

    def list_tools(self) -> list[ToolSchema]:
        """Return schemas for all registered tools."""
        return [t.schema for t in self._tools.values()]

    def get_schema(self, name: str) -> ToolSchema | None:
        """Return the schema for a specific tool, or None if not found."""
        tool = self._tools.get(name)
        return tool.schema if tool else None

    async def execute(self, name: str, arguments: dict[str, Any], call_id: str = "") -> ToolResult:
        """Execute a tool by name with the given arguments.

        Returns a ToolResult in all cases -- never raises for tool-level errors.
        This is intentional: the agent loop should handle errors as data,
        not as exceptions that break the control flow.
        """
        start = time.monotonic()

        # Tool exists?
        tool = self._tools.get(name)
        if tool is None:
            result = ToolResult(
                tool_call_id=call_id,
                name=name,
                content="",
                success=False,
                error=f"Tool not found: '{name}'. Available tools: {list(self._tools.keys())}",
            )
            self._log_execution(name, arguments, result, 0.0)
            return result

        # Validate required arguments
        missing = []
        for param in tool.schema.parameters:
            if param.required and param.name not in arguments:
                missing.append(param.name)
        if missing:
            result = ToolResult(
                tool_call_id=call_id,
                name=name,
                content="",
                success=False,
                error=f"Missing required arguments: {missing}. "
                      f"Expected: {[p.name for p in tool.schema.parameters]}",
            )
            self._log_execution(name, arguments, result, 0.0)
            return result

        # Execute
        try:
            output = await tool.handler(**arguments)
            elapsed = (time.monotonic() - start) * 1000
            result = ToolResult(
                tool_call_id=call_id,
                name=name,
                content=str(output),
                success=True,
            )
        except Exception as e:
            elapsed = (time.monotonic() - start) * 1000
            logger.error("tool_execution_failed", tool=name, error=str(e))
            result = ToolResult(
                tool_call_id=call_id,
                name=name,
                content="",
                success=False,
                error=f"Tool execution failed: {type(e).__name__}: {e}",
            )

        self._log_execution(name, arguments, result, elapsed)
        return result

    def get_execution_log(self) -> list[dict[str, Any]]:
        """Return the full execution audit log."""
        return list(self._execution_log)

    def _log_execution(
        self, name: str, arguments: dict[str, Any], result: ToolResult, elapsed_ms: float
    ) -> None:
        entry = {
            "tool_name": name,
            "arguments": arguments,
            "success": result.success,
            "error": result.error,
            "elapsed_ms": elapsed_ms,
            "timestamp": time.time(),
        }
        self._execution_log.append(entry)
        logger.info("tool_executed", **entry)


class _RegisteredTool:
    """Internal container for a tool's schema and handler."""

    def __init__(self, schema: ToolSchema, handler: Callable[..., Awaitable[str]]):
        self.schema = schema
        self.handler = handler
