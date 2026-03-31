"""
JARVIS MAX — Intelligent Memory Subsystem
============================================
High-signal AI OS memory: selective, typed, mission-relevant.

Architecture:
  MemoryFacade (raw storage) → IntelligentMemory (quality layer)

Type discipline (6 memory types):
  1. short_term_context  — current mission working memory (TTL: 1h)
  2. mission_memory      — per-mission outcomes and artifacts (TTL: 30d)
  3. project_memory      — persistent project context (TTL: none)
  4. long_term_knowledge  — validated facts and patterns (TTL: none)
  5. user_preferences    — user settings and style (TTL: none)
  6. validated_learning  — improvement loop lessons (TTL: none)

Quality features:
  - Type-aware retrieval with scope filtering
  - Relevance scoring (keyword overlap + recency + type boost)
  - Deduplication (content hash + similarity threshold)
  - TTL/pruning (auto-expire short-lived entries)
  - Low-signal filtering (min content length, no noise)
  - Bounded size per type
  - Summarization of bloated entries
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


# ═══════════════════════════════════════════════════════════════
# MEMORY TYPES
# ═══════════════════════════════════════════════════════════════

class MemoryType(str, Enum):
    SHORT_TERM = "short_term_context"
    MISSION = "mission_memory"
    PROJECT = "project_memory"
    KNOWLEDGE = "long_term_knowledge"
    PREFERENCES = "user_preferences"
    LEARNING = "validated_learning"


# Type → (TTL seconds, max entries, recency_weight)
_TYPE_CONFIG = {
    MemoryType.SHORT_TERM:  (3600,    50,   1.0),   # 1h, 50 items, high recency
    MemoryType.MISSION:     (2592000, 200,  0.5),   # 30d, 200 items
    MemoryType.PROJECT:     (0,       100,  0.3),   # no TTL, 100 items
    MemoryType.KNOWLEDGE:   (0,       500,  0.1),   # no TTL, 500 items
    MemoryType.PREFERENCES: (0,       50,   0.0),   # no TTL, 50 items
    MemoryType.LEARNING:    (0,       300,  0.2),   # no TTL, 300 items
}


# ═══════════════════════════════════════════════════════════════
# MEMORY ENTRY
# ═══════════════════════════════════════════════════════════════

@dataclass
class MemoryItem:
    """Typed, scored memory item."""
    id: str = ""
    content: str = ""
    memory_type: str = MemoryType.KNOWLEDGE
    scope: str = ""          # project name, mission id, etc.
    tags: list[str] = field(default_factory=list)
    relevance: float = 0.0  # 0.0-1.0, computed during retrieval
    recency: float = 0.0    # 0.0-1.0, decays with age
    validated: bool = False  # True if verified by improvement loop
    created_at: float = field(default_factory=time.time)
    source: str = ""

    @property
    def content_hash(self) -> str:
        return hashlib.md5(self.content[:200].lower().strip().encode()).hexdigest()[:12]

    def to_dict(self) -> dict:
        return {
            "id": self.id, "content": self.content[:500],
            "type": self.memory_type, "scope": self.scope,
            "tags": self.tags[:5], "relevance": round(self.relevance, 3),
            "recency": round(self.recency, 3), "validated": self.validated,
            "created_at": self.created_at, "source": self.source,
        }


# ═══════════════════════════════════════════════════════════════
# DEDUPLICATION
# ═══════════════════════════════════════════════════════════════

class Deduplicator:
    """Content-hash based deduplication with similarity threshold."""

    def __init__(self):
        self._seen: dict[str, float] = {}  # content_hash → timestamp

    def is_duplicate(self, item: MemoryItem) -> bool:
        """Check if content is duplicate."""
        h = item.content_hash
        return h in self._seen

    def register(self, item: MemoryItem) -> None:
        self._seen[item.content_hash] = item.created_at

    def deduplicate(self, items: list[MemoryItem]) -> list[MemoryItem]:
        """Remove duplicates, keeping the most recent."""
        seen: dict[str, MemoryItem] = {}
        for item in items:
            h = item.content_hash
            if h not in seen or item.created_at > seen[h].created_at:
                seen[h] = item
        return list(seen.values())

    def clear(self) -> None:
        self._seen.clear()


# ═══════════════════════════════════════════════════════════════
# RELEVANCE SCORER
# ═══════════════════════════════════════════════════════════════

class RelevanceScorer:
    """
    Scores memory items for a query using:
    - Keyword overlap (40%)
    - Recency (30%)
    - Type boost (20%)
    - Validation boost (10%)
    """

    def score(self, item: MemoryItem, query: str,
              preferred_type: str | None = None,
              preferred_scope: str | None = None) -> float:
        """Compute composite relevance score."""
        # 1. Keyword overlap (40%)
        kw_score = self._keyword_score(item.content, query)

        # 2. Recency (30%)
        recency_weight = _TYPE_CONFIG.get(item.memory_type, (0, 0, 0.3))[2]
        age_hours = (time.time() - item.created_at) / 3600
        recency_score = max(0, 1.0 - (age_hours / 720))  # Decays over 30 days
        recency_score *= recency_weight

        # 3. Type boost (20%)
        type_score = 0.0
        if preferred_type and item.memory_type == preferred_type:
            type_score = 1.0
        elif item.memory_type in (MemoryType.KNOWLEDGE, MemoryType.LEARNING):
            type_score = 0.5  # General knowledge is always somewhat relevant

        # 4. Scope match boost
        scope_score = 0.0
        if preferred_scope and item.scope == preferred_scope:
            scope_score = 0.3

        # 5. Validation boost (10%)
        validation_score = 1.0 if item.validated else 0.0

        # Composite
        total = (kw_score * 0.40
                 + recency_score * 0.30
                 + type_score * 0.20
                 + validation_score * 0.10
                 + scope_score * 0.10)

        return min(1.0, total)

    def _keyword_score(self, content: str, query: str) -> float:
        if not query:
            return 0.0
        query_words = set(query.lower().split())
        content_words = set(content.lower().split())
        if not query_words:
            return 0.0
        overlap = len(query_words & content_words)
        return min(1.0, overlap / len(query_words))


# ═══════════════════════════════════════════════════════════════
# SIGNAL FILTER
# ═══════════════════════════════════════════════════════════════

class SignalFilter:
    """
    Filters low-signal memory items.
    Rejects: too short, too generic, noise patterns.
    """

    MIN_CONTENT_LENGTH = 10
    NOISE_PATTERNS = [
        "ok", "done", "yes", "no", "maybe", "thanks",
        "heartbeat_ok", "no_reply", "pass",
    ]

    def is_worth_storing(self, content: str, memory_type: str = "") -> bool:
        """Check if content is worth persisting."""
        if not content or len(content.strip()) < self.MIN_CONTENT_LENGTH:
            return False

        content_lower = content.strip().lower()

        # Reject pure noise
        if content_lower in self.NOISE_PATTERNS:
            return False

        # Short-term context can be shorter
        if memory_type == MemoryType.SHORT_TERM:
            return len(content.strip()) >= 5

        return True

    def is_worth_retrieving(self, item: MemoryItem, min_relevance: float = 0.1) -> bool:
        """Check if item is worth returning in search results."""
        if item.relevance < min_relevance:
            return False
        if not item.content or len(item.content.strip()) < 5:
            return False
        return True


# ═══════════════════════════════════════════════════════════════
# PRUNER
# ═══════════════════════════════════════════════════════════════

class MemoryPruner:
    """Enforces TTL and size bounds per memory type."""

    def prune(self, items: list[MemoryItem]) -> tuple[list[MemoryItem], int]:
        """Prune expired and over-limit items. Returns (kept, removed_count)."""
        now = time.time()
        kept = []
        removed = 0

        # Group by type
        by_type: dict[str, list[MemoryItem]] = {}
        for item in items:
            by_type.setdefault(item.memory_type, []).append(item)

        for mtype, type_items in by_type.items():
            ttl_s, max_items, _ = _TYPE_CONFIG.get(mtype, (0, 500, 0.3))

            # TTL pruning
            if ttl_s > 0:
                valid = [i for i in type_items if (now - i.created_at) < ttl_s]
                removed += len(type_items) - len(valid)
                type_items = valid

            # Size bound (keep most recent)
            if len(type_items) > max_items:
                type_items.sort(key=lambda x: x.created_at, reverse=True)
                removed += len(type_items) - max_items
                type_items = type_items[:max_items]

            kept.extend(type_items)

        return kept, removed


# ═══════════════════════════════════════════════════════════════
# SUMMARIZER
# ═══════════════════════════════════════════════════════════════

class MemorySummarizer:
    """
    Summarizes bloated memory entries.
    Deterministic (no LLM) — uses truncation + key extraction.
    """

    MAX_CONTENT_LENGTH = 500

    def should_summarize(self, item: MemoryItem) -> bool:
        return len(item.content) > self.MAX_CONTENT_LENGTH

    def summarize(self, item: MemoryItem) -> MemoryItem:
        """Produce a condensed version of a long entry."""
        if not self.should_summarize(item):
            return item

        content = item.content
        # Take first paragraph + last sentence
        paragraphs = content.split("\n\n")
        first = paragraphs[0][:300] if paragraphs else content[:300]

        sentences = content.replace("\n", " ").split(". ")
        last = sentences[-1][:100] if sentences else ""

        summarized = first
        if last and last not in first:
            summarized += f" [...] {last}"

        return MemoryItem(
            id=item.id,
            content=summarized[:self.MAX_CONTENT_LENGTH],
            memory_type=item.memory_type,
            scope=item.scope,
            tags=item.tags,
            validated=item.validated,
            created_at=item.created_at,
            source=item.source + ":summarized",
        )


# ═══════════════════════════════════════════════════════════════
# INTELLIGENT MEMORY (main class)
# ═══════════════════════════════════════════════════════════════

@dataclass
class RetrievalResult:
    """Result of an intelligent memory retrieval."""
    items: list[MemoryItem]
    query: str
    types_searched: list[str]
    total_candidates: int
    after_dedup: int
    after_filter: int
    duration_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "items": [i.to_dict() for i in self.items],
            "count": len(self.items),
            "query": self.query[:100],
            "types_searched": self.types_searched,
            "total_candidates": self.total_candidates,
            "after_dedup": self.after_dedup,
            "after_filter": self.after_filter,
            "duration_ms": round(self.duration_ms, 1),
        }

    def as_context(self) -> str:
        """Format top items as text context for prompts."""
        if not self.items:
            return ""
        lines = []
        for i, item in enumerate(self.items[:5]):
            tag = f"[{item.memory_type}]" if item.memory_type else ""
            lines.append(f"{tag} {item.content[:200]}")
        return "\n".join(lines)


class IntelligentMemory:
    """
    High-signal memory layer on top of raw storage.

    Store: validates, deduplicates, filters, types
    Retrieve: scores, filters, ranks, returns structured results
    Maintain: prunes expired, enforces bounds, summarizes bloat
    """

    def __init__(self, persist_path: Path | None = None):
        self._path = persist_path or Path("workspace/intelligent_memory.json")
        self._items: list[MemoryItem] = []
        self._dedup = Deduplicator()
        self._scorer = RelevanceScorer()
        self._filter = SignalFilter()
        self._pruner = MemoryPruner()
        self._summarizer = MemorySummarizer()
        self._load()

    # ── Store ──

    def store(self, content: str, memory_type: str = MemoryType.KNOWLEDGE,
              scope: str = "", tags: list[str] | None = None,
              validated: bool = False, source: str = "runtime") -> bool:
        """
        Store a memory item after quality filtering.
        Returns True if stored, False if rejected.
        """
        # Signal filter
        if not self._filter.is_worth_storing(content, memory_type):
            return False

        item = MemoryItem(
            id=hashlib.md5(f"{content[:100]}:{time.time()}".encode()).hexdigest()[:10],
            content=content.strip(),
            memory_type=memory_type,
            scope=scope,
            tags=tags or [],
            validated=validated,
            created_at=time.time(),
            source=source,
        )

        # Deduplication
        if self._dedup.is_duplicate(item):
            return False
        self._dedup.register(item)

        # Summarize if too long
        if self._summarizer.should_summarize(item):
            item = self._summarizer.summarize(item)

        self._items.append(item)
        self._save()
        return True

    # ── Retrieve ──

    def retrieve(self, query: str, top_k: int = 5,
                 memory_type: str | None = None,
                 scope: str | None = None,
                 min_relevance: float = 0.1) -> RetrievalResult:
        """
        Intelligent retrieval: score, filter, deduplicate, rank.
        """
        start = time.time()
        types_searched = []

        # Select candidates
        if memory_type:
            candidates = [i for i in self._items if i.memory_type == memory_type]
            types_searched = [memory_type]
        else:
            candidates = list(self._items)
            types_searched = list(set(i.memory_type for i in self._items))

        total_candidates = len(candidates)

        # Score all candidates
        for item in candidates:
            item.relevance = self._scorer.score(
                item, query,
                preferred_type=memory_type,
                preferred_scope=scope,
            )

        # Deduplicate
        candidates = self._dedup.deduplicate(candidates)
        after_dedup = len(candidates)

        # Filter low-signal
        candidates = [i for i in candidates
                      if self._filter.is_worth_retrieving(i, min_relevance)]
        after_filter = len(candidates)

        # Sort by relevance
        candidates.sort(key=lambda x: x.relevance, reverse=True)

        duration = (time.time() - start) * 1000

        return RetrievalResult(
            items=candidates[:top_k],
            query=query,
            types_searched=types_searched,
            total_candidates=total_candidates,
            after_dedup=after_dedup,
            after_filter=after_filter,
            duration_ms=duration,
        )

    def retrieve_for_mission(self, goal: str, project: str = "",
                             top_k: int = 5) -> RetrievalResult:
        """
        Mission-optimized retrieval: combines multiple type searches
        with boosted project context and validated learning.
        """
        start = time.time()
        all_items: list[MemoryItem] = []

        # 1. Project memory (highest priority if scope matches)
        if project:
            proj_items = [i for i in self._items
                          if i.memory_type == MemoryType.PROJECT and i.scope == project]
            for item in proj_items:
                item.relevance = self._scorer.score(item, goal,
                                                     preferred_scope=project)
            all_items.extend(proj_items)

        # 2. Validated learning
        learning_items = [i for i in self._items
                          if i.memory_type == MemoryType.LEARNING]
        for item in learning_items:
            item.relevance = self._scorer.score(item, goal,
                                                 preferred_type=MemoryType.LEARNING)
        all_items.extend(learning_items)

        # 3. Long-term knowledge
        knowledge_items = [i for i in self._items
                           if i.memory_type == MemoryType.KNOWLEDGE]
        for item in knowledge_items:
            item.relevance = self._scorer.score(item, goal)
        all_items.extend(knowledge_items)

        # 4. Recent mission memory
        mission_items = [i for i in self._items
                         if i.memory_type == MemoryType.MISSION]
        for item in mission_items:
            item.relevance = self._scorer.score(item, goal)
        all_items.extend(mission_items)

        # Deduplicate and filter
        all_items = self._dedup.deduplicate(all_items)
        all_items = [i for i in all_items
                     if self._filter.is_worth_retrieving(i, 0.05)]
        all_items.sort(key=lambda x: x.relevance, reverse=True)

        duration = (time.time() - start) * 1000
        return RetrievalResult(
            items=all_items[:top_k],
            query=goal,
            types_searched=["project", "learning", "knowledge", "mission"],
            total_candidates=len(self._items),
            after_dedup=len(all_items),
            after_filter=len(all_items),
            duration_ms=duration,
        )

    # ── Maintenance ──

    def prune(self) -> int:
        """Run TTL and size pruning. Returns number removed."""
        self._items, removed = self._pruner.prune(self._items)
        if removed > 0:
            self._save()
        return removed

    def stats(self) -> dict:
        """Memory statistics per type."""
        by_type: dict[str, int] = {}
        for item in self._items:
            by_type[item.memory_type] = by_type.get(item.memory_type, 0) + 1
        validated = sum(1 for i in self._items if i.validated)
        return {
            "total_items": len(self._items),
            "by_type": by_type,
            "validated": validated,
            "oldest_age_hours": round(
                (time.time() - min((i.created_at for i in self._items), default=time.time())) / 3600, 1
            ),
        }

    # ── Import from existing systems ──

    def import_lessons(self) -> int:
        """Import lessons from self_improvement_loop.LessonMemory."""
        imported = 0
        try:
            from core.self_improvement_loop import LessonMemory
            mem = LessonMemory()
            for lesson_dict in mem.get_all():
                content = f"Problem: {lesson_dict.get('problem', '')}. " \
                          f"Strategy: {lesson_dict.get('strategy', '')}. " \
                          f"Result: {lesson_dict.get('result', '')}. " \
                          f"Lesson: {lesson_dict.get('lessons', '')}"
                success = lesson_dict.get("result") == "success"
                if self.store(content, MemoryType.LEARNING,
                              validated=success, source="improvement_loop"):
                    imported += 1
        except Exception:
            pass
        return imported

    # ── Persistence ──

    def _save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            data = [i.to_dict() for i in self._items]
            self._path.write_text(
                json.dumps(data, indent=2, default=str), encoding="utf-8")
        except Exception:
            pass

    def _load(self) -> None:
        if self._path.exists():
            try:
                data = json.loads(self._path.read_text(encoding="utf-8"))
                for d in data:
                    item = MemoryItem(
                        id=d.get("id", ""),
                        content=d.get("content", ""),
                        memory_type=d.get("type", MemoryType.KNOWLEDGE),
                        scope=d.get("scope", ""),
                        tags=d.get("tags", []),
                        validated=d.get("validated", False),
                        created_at=d.get("created_at", 0),
                        source=d.get("source", ""),
                    )
                    self._items.append(item)
                    self._dedup.register(item)
            except Exception:
                pass

    def clear(self) -> None:
        """Clear all memory (for testing)."""
        self._items.clear()
        self._dedup.clear()
        if self._path.exists():
            self._path.unlink()
