"""Cost and latency profiling for agent systems."""

from __future__ import annotations

import time

from pydantic import BaseModel, Field

MODEL_PRICING: dict[str, dict[str, float]] = {
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
    "claude-haiku-4-5": {"input": 0.80, "output": 4.00},
}


class CostEntry(BaseModel):
    step: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    timestamp: float = Field(default_factory=time.time)


class CostProfile(BaseModel):
    entries: list[CostEntry] = Field(default_factory=list)

    @property
    def total_tokens(self) -> int:
        return sum(e.prompt_tokens + e.completion_tokens for e in self.entries)

    @property
    def total_cost_usd(self) -> float:
        return sum(e.cost_usd for e in self.entries)

    @property
    def total_latency_ms(self) -> float:
        return sum(e.latency_ms for e in self.entries)

    @property
    def model_call_count(self) -> int:
        return len(self.entries)

    def add(
        self, step: str, model: str, prompt_tokens: int, completion_tokens: int, latency_ms: float
    ) -> None:
        pricing = MODEL_PRICING.get(model, {"input": 5.0, "output": 15.0})
        cost = (
            prompt_tokens * pricing["input"] / 1_000_000
            + completion_tokens * pricing["output"] / 1_000_000
        )
        self.entries.append(
            CostEntry(
                step=step,
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                cost_usd=cost,
                latency_ms=latency_ms,
            )
        )

    def summary(self) -> str:
        return (
            f"Cost profile: {self.model_call_count} calls | "
            f"{self.total_tokens} tokens | "
            f"${self.total_cost_usd:.4f} | "
            f"{self.total_latency_ms:.0f}ms"
        )
