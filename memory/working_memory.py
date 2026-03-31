"""
memory/working_memory.py — Bounded working memory for mission context.

Inspired by Hermes Agent's bounded memory model.
Caps context injection to prevent prompt flooding.
Ranks and selects the most relevant items within a token budget.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import structlog

log = structlog.get_logger("memory.working_memory")

# Rough chars-to-tokens ratio
_CHARS_PER_TOKEN = 4
_DEFAULT_TOKEN_BUDGET = 2000  # ~8000 chars


@dataclass
class WorkingMemoryItem:
    content: str
    source: str  # "skill", "memory", "failure", "decision"
    relevance: float = 0.5
    tokens_est: int = 0

    def __post_init__(self):
        if self.tokens_est == 0:
            self.tokens_est = max(1, len(self.content) // _CHARS_PER_TOKEN)


@dataclass
class WorkingMemory:
    """
    Bounded context window for a single mission.
    Accepts items, ranks by relevance, evicts when over budget.
    """
    token_budget: int = _DEFAULT_TOKEN_BUDGET
    items: list[WorkingMemoryItem] = field(default_factory=list)

    def add(self, content: str, source: str, relevance: float = 0.5) -> bool:
        """Add an item. Returns False if budget already full."""
        item = WorkingMemoryItem(content=content, source=source, relevance=relevance)
        self.items.append(item)
        self._enforce_budget()
        return item in self.items

    def add_batch(
        self,
        items: list[dict],
    ) -> int:
        """Add multiple items at once. Returns count added."""
        for it in items:
            self.items.append(WorkingMemoryItem(
                content=it.get("content", ""),
                source=it.get("source", "unknown"),
                relevance=it.get("relevance", 0.5),
            ))
        self._enforce_budget()
        return len(self.items)

    def _enforce_budget(self) -> None:
        """
        Sort by relevance (descending), then evict lowest-relevance
        items until we're within budget.
        """
        self.items.sort(key=lambda x: x.relevance, reverse=True)
        total = 0
        cutoff = len(self.items)
        for i, item in enumerate(self.items):
            total += item.tokens_est
            if total > self.token_budget:
                cutoff = i
                break
        evicted = len(self.items) - cutoff
        if evicted > 0:
            self.items = self.items[:cutoff]
            log.debug("working_memory_evicted",
                      evicted=evicted, remaining=len(self.items))

    def to_prompt(self) -> str:
        """Render working memory as a prompt section."""
        if not self.items:
            return ""
        parts = []
        for item in self.items:
            parts.append(f"[{item.source}] {item.content}")
        return "\n".join(parts)

    def used_tokens(self) -> int:
        return sum(it.tokens_est for it in self.items)

    def remaining_tokens(self) -> int:
        return max(0, self.token_budget - self.used_tokens())

    def stats(self) -> dict:
        return {
            "items": len(self.items),
            "used_tokens": self.used_tokens(),
            "budget": self.token_budget,
            "remaining": self.remaining_tokens(),
            "sources": list(set(it.source for it in self.items)),
        }
