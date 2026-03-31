"""
executor/observation.py — Structured observation from execution.

Inspired by OpenHands' observation->action->observation loop.
Every execution produces an Observation, not just raw output.
Observations carry structured metadata for the orchestrator to reason about.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ObservationType(str, Enum):
    TOOL_OUTPUT = "tool_output"
    LLM_RESPONSE = "llm_response"
    FILE_CONTENT = "file_content"
    ERROR = "error"
    TIMEOUT = "timeout"
    APPROVAL_REQUIRED = "approval_required"
    NO_OP = "no_op"


@dataclass
class Observation:
    """
    Structured observation from an execution step.
    Goes beyond raw output — carries semantic meaning.
    """
    obs_type: ObservationType
    content: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    success: bool = True
    confidence: float = 0.5

    # Cost tracking
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0

    # Provenance
    source_tool: str = ""
    source_step: int = 0

    def is_actionable(self) -> bool:
        """Can the orchestrator use this to continue?"""
        return self.success and self.content.strip() != ""

    def is_error(self) -> bool:
        return self.obs_type in (ObservationType.ERROR, ObservationType.TIMEOUT)

    def summary(self, max_len: int = 100) -> str:
        prefix = f"[{self.obs_type.value}]"
        body = self.content[:max_len].replace("\n", " ")
        return f"{prefix} {body}"

    def to_dict(self) -> dict:
        return {
            "type": self.obs_type.value,
            "content": self.content[:500],
            "success": self.success,
            "confidence": self.confidence,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "cost_usd": round(self.cost_usd, 6),
            "source_tool": self.source_tool,
            "source_step": self.source_step,
        }


@dataclass
class ExecutionBudget:
    """
    Budget constraint for mission execution.
    Prevents runaway costs. Tracks cumulative spend.
    """
    max_tokens: int = 100_000
    max_cost_usd: float = 1.0
    max_steps: int = 20
    max_duration_s: int = 300  # 5 min

    # Counters (mutable)
    used_tokens: int = 0
    used_cost_usd: float = 0.0
    used_steps: int = 0

    def record(self, obs: Observation) -> None:
        """Record an observation against this budget."""
        self.used_tokens += obs.tokens_in + obs.tokens_out
        self.used_cost_usd += obs.cost_usd
        self.used_steps += 1

    def is_exceeded(self) -> tuple[bool, str]:
        """Check if any budget limit is exceeded."""
        if self.used_tokens > self.max_tokens:
            return True, f"tokens: {self.used_tokens}/{self.max_tokens}"
        if self.used_cost_usd > self.max_cost_usd:
            return True, f"cost: ${self.used_cost_usd:.4f}/${self.max_cost_usd}"
        if self.used_steps > self.max_steps:
            return True, f"steps: {self.used_steps}/{self.max_steps}"
        return False, ""

    def remaining_pct(self) -> float:
        """How much budget remains (worst case across dimensions)."""
        pcts = [
            1 - (self.used_tokens / max(self.max_tokens, 1)),
            1 - (self.used_cost_usd / max(self.max_cost_usd, 0.01)),
            1 - (self.used_steps / max(self.max_steps, 1)),
        ]
        return max(0.0, min(pcts))

    def to_dict(self) -> dict:
        return {
            "tokens": f"{self.used_tokens}/{self.max_tokens}",
            "cost": f"${self.used_cost_usd:.4f}/${self.max_cost_usd}",
            "steps": f"{self.used_steps}/{self.max_steps}",
            "remaining_pct": round(self.remaining_pct(), 3),
        }
