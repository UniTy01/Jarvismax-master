"""
memory/memory_models.py — Unified memory model for JarvisMax.

Four clean layers:
1. Working memory (current mission, ephemeral)
2. Knowledge memory (stable facts, reusable)
3. Procedural memory (skills — delegated to core/skills/)
4. Decision memory (audit trail, lessons, failures)
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class MemoryType(str, Enum):
    WORKING = "working"         # ephemeral, mission-scoped
    KNOWLEDGE = "knowledge"     # stable facts
    PROCEDURAL = "procedural"   # skills (alias for core/skills)
    DECISION = "decision"       # audit trail, failures, lessons
    MISSION_OUTCOME = "mission_outcome"  # mission results


@dataclass
class MemoryItem:
    """Universal memory item across all layers."""
    memory_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    content: str = ""
    memory_type: MemoryType = MemoryType.KNOWLEDGE
    source: str = ""                # who/what created this
    confidence: float = 0.5
    relevance: float = 0.0         # computed at retrieval time
    tags: list[str] = field(default_factory=list)

    # Linking
    related_mission_id: str = ""
    related_component: str = ""
    related_skill_id: str = ""

    # Metadata
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    access_count: int = 0
    last_accessed_at: Optional[float] = None

    def to_dict(self) -> dict:
        return {
            "memory_id": self.memory_id,
            "content": self.content[:500],
            "memory_type": self.memory_type.value,
            "source": self.source,
            "confidence": self.confidence,
            "relevance": self.relevance,
            "tags": self.tags,
            "related_mission_id": self.related_mission_id,
            "related_component": self.related_component,
            "related_skill_id": self.related_skill_id,
            "created_at": self.created_at,
            "access_count": self.access_count,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "MemoryItem":
        mt = d.pop("memory_type", "knowledge")
        if isinstance(mt, str):
            try:
                mt = MemoryType(mt)
            except ValueError:
                mt = MemoryType.KNOWLEDGE
        return cls(memory_type=mt, **d)

    def touch(self) -> None:
        """Record an access."""
        self.access_count += 1
        self.last_accessed_at = time.time()
