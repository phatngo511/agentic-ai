"""Structured trace logging for agent systems."""

from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Any

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger()


class TraceSpan(BaseModel):
    span_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str
    start_time: float
    end_time: float = 0.0
    duration_ms: float = 0.0
    input_data: dict[str, Any] = Field(default_factory=dict)
    output_data: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    children: list[TraceSpan] = Field(default_factory=list)


class Trace(BaseModel):
    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    query: str
    start_time: float = Field(default_factory=time.time)
    end_time: float = 0.0
    total_duration_ms: float = 0.0
    spans: list[TraceSpan] = Field(default_factory=list)
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    success: bool = True
    error: str | None = None

    def add_span(self, span: TraceSpan) -> None:
        self.spans.append(span)

    def finalize(self) -> None:
        self.end_time = time.time()
        self.total_duration_ms = (self.end_time - self.start_time) * 1000

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)

    def summary(self) -> str:
        status = "OK" if self.success else f"FAIL: {self.error}"
        return (
            f"[{self.trace_id[:8]}] {self.query[:50]} | "
            f"{len(self.spans)} spans | {self.total_duration_ms:.0f}ms | "
            f"{self.total_tokens} tokens | {status}"
        )


class Tracer:
    def __init__(self, output_dir: str | Path | None = None):
        self._output_dir = Path(output_dir) if output_dir else None
        self._traces: list[Trace] = []

    def start_trace(self, query: str) -> Trace:
        trace = Trace(query=query)
        self._traces.append(trace)
        logger.info("trace_started", trace_id=trace.trace_id[:8], query=query[:80])
        return trace

    def start_span(self, name: str, input_data: dict[str, Any] | None = None) -> TraceSpan:
        return TraceSpan(name=name, start_time=time.time(), input_data=input_data or {})

    def end_span(
        self, span: TraceSpan, output_data: dict[str, Any] | None = None, error: str | None = None
    ) -> TraceSpan:
        span.end_time = time.time()
        span.duration_ms = (span.end_time - span.start_time) * 1000
        span.output_data = output_data or {}
        span.error = error
        return span

    def end_trace(self, trace: Trace, success: bool = True, error: str | None = None) -> Trace:
        trace.success = success
        trace.error = error
        trace.finalize()
        logger.info("trace_completed", trace_id=trace.trace_id[:8], summary=trace.summary())
        if self._output_dir:
            self._save_trace(trace)
        return trace

    def get_traces(self) -> list[Trace]:
        return list(self._traces)

    def _save_trace(self, trace: Trace) -> None:
        self._output_dir.mkdir(parents=True, exist_ok=True)
        path = self._output_dir / f"{trace.trace_id}.json"
        path.write_text(trace.to_json())
