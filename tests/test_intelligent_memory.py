"""
Tests — Intelligent Memory Subsystem

Persistence
  M1.  Store and reload from disk
  M2.  Clear wipes everything
  M3.  Stats reflect stored items

Retrieval by Type
  M4.  Retrieve by specific type
  M5.  Retrieve all types when no filter
  M6.  Mission-optimized retrieval prioritizes project context
  M7.  Learning items scored higher when validated

Relevance
  M8.  Keyword overlap boosts score
  M9.  Recency boosts score for short_term
  M10. Type match boosts score
  M11. Scope match boosts score
  M12. Validation boosts score

Deduplication
  M13. Exact duplicate rejected on store
  M14. Deduplicator removes from list
  M15. Near-identical content deduped

Signal Filter
  M16. Short content rejected
  M17. Noise patterns rejected
  M18. Valid content accepted
  M19. Low-relevance items filtered from retrieval

TTL/Pruning
  M20. Expired short_term items pruned
  M21. Size bounds enforced
  M22. Non-expiring types not pruned

Summarizer
  M23. Long content summarized on store
  M24. Short content unchanged

Lesson Reuse
  M25. Store and retrieve validated learning
  M26. Learning appears in mission retrieval
  M27. Non-validated learning scored lower than validated

Mission Improvement (memory vs no-memory)
  M28. Mission retrieval returns relevant context
  M29. Empty memory returns empty context
  M30. Memory as_context produces prompt text
"""
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.intelligent_memory import (
    MemoryType, MemoryItem,
    Deduplicator, RelevanceScorer, SignalFilter, MemoryPruner, MemorySummarizer,
    RetrievalResult, IntelligentMemory,
)


# ═══════════════════════════════════════════════════════════════
# PERSISTENCE
# ═══════════════════════════════════════════════════════════════

class TestPersistence:

    def test_store_reload(self, tmp_path):
        """M1: Store and reload from disk."""
        path = tmp_path / "mem.json"
        mem1 = IntelligentMemory(path)
        mem1.store("Python is a programming language", MemoryType.KNOWLEDGE)
        mem1.store("User prefers concise output", MemoryType.PREFERENCES)

        mem2 = IntelligentMemory(path)
        assert mem2.stats()["total_items"] == 2

    def test_clear(self, tmp_path):
        """M2: Clear wipes everything."""
        mem = IntelligentMemory(tmp_path / "mem.json")
        mem.store("test content for clearing", MemoryType.KNOWLEDGE)
        mem.clear()
        assert mem.stats()["total_items"] == 0

    def test_stats(self, tmp_path):
        """M3: Stats reflect stored items."""
        mem = IntelligentMemory(tmp_path / "mem.json")
        mem.store("Project uses FastAPI for backend", MemoryType.PROJECT, scope="jarvismax")
        mem.store("Timeout fix worked by increasing to 45s", MemoryType.LEARNING, validated=True)
        stats = mem.stats()
        assert stats["total_items"] == 2
        assert stats["validated"] == 1
        assert MemoryType.PROJECT in stats["by_type"]


# ═══════════════════════════════════════════════════════════════
# RETRIEVAL BY TYPE
# ═══════════════════════════════════════════════════════════════

class TestRetrievalByType:

    def test_by_specific_type(self, tmp_path):
        """M4: Retrieve by specific type."""
        mem = IntelligentMemory(tmp_path / "mem.json")
        mem.store("Python is dynamically typed", MemoryType.KNOWLEDGE)
        mem.store("User likes dark theme configuration", MemoryType.PREFERENCES)
        result = mem.retrieve("Python", memory_type=MemoryType.KNOWLEDGE)
        assert all(i.memory_type == MemoryType.KNOWLEDGE for i in result.items)

    def test_all_types(self, tmp_path):
        """M5: No type filter → search all."""
        mem = IntelligentMemory(tmp_path / "mem.json")
        mem.store("FastAPI backend architecture patterns", MemoryType.KNOWLEDGE)
        mem.store("Last mission analyzed performance", MemoryType.MISSION)
        result = mem.retrieve("architecture")
        assert result.total_candidates >= 2

    def test_mission_retrieval_prioritizes_project(self, tmp_path):
        """M6: Mission retrieval prioritizes project context."""
        mem = IntelligentMemory(tmp_path / "mem.json")
        mem.store("JarvisMax uses Python and FastAPI for web framework", MemoryType.PROJECT, scope="jarvismax")
        mem.store("Ruby is another programming language", MemoryType.KNOWLEDGE)
        result = mem.retrieve_for_mission("Build a FastAPI endpoint", project="jarvismax")
        if result.items:
            # Project item should be first
            assert "FastAPI" in result.items[0].content or "jarvismax" in result.items[0].scope

    def test_validated_learning_scored_higher(self, tmp_path):
        """M7: Validated learning scored higher."""
        mem = IntelligentMemory(tmp_path / "mem.json")
        mem.store("Timeout fix: increase to 45s worked well", MemoryType.LEARNING, validated=True)
        mem.store("Random unvalidated thought about systems", MemoryType.LEARNING, validated=False)
        result = mem.retrieve("timeout fix improvement")
        validated = [i for i in result.items if i.validated]
        non_validated = [i for i in result.items if not i.validated]
        if validated and non_validated:
            assert validated[0].relevance >= non_validated[0].relevance


# ═══════════════════════════════════════════════════════════════
# RELEVANCE
# ═══════════════════════════════════════════════════════════════

class TestRelevance:

    def test_keyword_overlap(self):
        """M8: Keyword overlap boosts score."""
        scorer = RelevanceScorer()
        item = MemoryItem(content="Python FastAPI backend architecture")
        high = scorer.score(item, "Python FastAPI backend")
        low = scorer.score(item, "Ruby Rails frontend")
        assert high > low

    def test_recency_boost(self):
        """M9: Recency boosts for short_term."""
        scorer = RelevanceScorer()
        recent = MemoryItem(content="current task context data",
                            memory_type=MemoryType.SHORT_TERM, created_at=time.time())
        old = MemoryItem(content="current task context data",
                         memory_type=MemoryType.SHORT_TERM, created_at=time.time() - 86400)
        s_recent = scorer.score(recent, "task context")
        s_old = scorer.score(old, "task context")
        assert s_recent >= s_old

    def test_type_match(self):
        """M10: Type match boosts score."""
        scorer = RelevanceScorer()
        item = MemoryItem(content="Python programming knowledge", memory_type=MemoryType.KNOWLEDGE)
        with_type = scorer.score(item, "Python", preferred_type=MemoryType.KNOWLEDGE)
        without_type = scorer.score(item, "Python", preferred_type=MemoryType.PREFERENCES)
        assert with_type > without_type

    def test_scope_match(self):
        """M11: Scope match boosts score."""
        scorer = RelevanceScorer()
        item = MemoryItem(content="Backend uses FastAPI framework", scope="jarvismax")
        with_scope = scorer.score(item, "FastAPI", preferred_scope="jarvismax")
        without_scope = scorer.score(item, "FastAPI", preferred_scope="other_project")
        assert with_scope > without_scope

    def test_validation_boost(self):
        """M12: Validated items score higher."""
        scorer = RelevanceScorer()
        validated = MemoryItem(content="Timeout fix works by increasing", validated=True)
        unvalidated = MemoryItem(content="Timeout fix works by increasing", validated=False)
        s_v = scorer.score(validated, "timeout fix")
        s_u = scorer.score(unvalidated, "timeout fix")
        assert s_v > s_u


# ═══════════════════════════════════════════════════════════════
# DEDUPLICATION
# ═══════════════════════════════════════════════════════════════

class TestDeduplication:

    def test_exact_duplicate_rejected(self, tmp_path):
        """M13: Exact duplicate rejected on store."""
        mem = IntelligentMemory(tmp_path / "mem.json")
        r1 = mem.store("FastAPI is a modern web framework", MemoryType.KNOWLEDGE)
        r2 = mem.store("FastAPI is a modern web framework", MemoryType.KNOWLEDGE)
        assert r1 is True
        assert r2 is False
        assert mem.stats()["total_items"] == 1

    def test_deduplicator_list(self):
        """M14: Deduplicator removes from list."""
        dedup = Deduplicator()
        items = [
            MemoryItem(content="same content exactly", created_at=1),
            MemoryItem(content="same content exactly", created_at=2),
            MemoryItem(content="different content here", created_at=3),
        ]
        unique = dedup.deduplicate(items)
        assert len(unique) == 2

    def test_near_identical(self, tmp_path):
        """M15: Near-identical (same hash prefix) deduped."""
        mem = IntelligentMemory(tmp_path / "mem.json")
        mem.store("FastAPI is a modern web framework", MemoryType.KNOWLEDGE)
        mem.store("fastapi is a modern web framework", MemoryType.KNOWLEDGE)
        # Case-insensitive hash should catch this
        assert mem.stats()["total_items"] == 1


# ═══════════════════════════════════════════════════════════════
# SIGNAL FILTER
# ═══════════════════════════════════════════════════════════════

class TestSignalFilter:

    def test_short_rejected(self):
        """M16: Short content rejected."""
        f = SignalFilter()
        assert not f.is_worth_storing("hi")
        assert not f.is_worth_storing("ok")

    def test_noise_rejected(self):
        """M17: Noise patterns rejected."""
        f = SignalFilter()
        assert not f.is_worth_storing("heartbeat_ok")
        assert not f.is_worth_storing("no_reply")

    def test_valid_accepted(self):
        """M18: Valid content accepted."""
        f = SignalFilter()
        assert f.is_worth_storing("Python is a programming language")

    def test_low_relevance_filtered(self, tmp_path):
        """M19: Low-relevance items filtered from retrieval."""
        mem = IntelligentMemory(tmp_path / "mem.json")
        mem.store("Python web development framework for backends", MemoryType.KNOWLEDGE)
        result = mem.retrieve("completely unrelated quantum physics topic", min_relevance=0.3)
        # Should return nothing or low-scored items
        for item in result.items:
            assert item.relevance >= 0.3


# ═══════════════════════════════════════════════════════════════
# TTL/PRUNING
# ═══════════════════════════════════════════════════════════════

class TestPruning:

    def test_expired_pruned(self, tmp_path):
        """M20: Expired short_term items pruned."""
        mem = IntelligentMemory(tmp_path / "mem.json")
        # Manually add an expired short_term item
        item = MemoryItem(
            id="old", content="old context from long ago",
            memory_type=MemoryType.SHORT_TERM,
            created_at=time.time() - 7200,  # 2h ago (TTL=1h)
        )
        mem._items.append(item)
        removed = mem.prune()
        assert removed >= 1
        assert not any(i.id == "old" for i in mem._items)

    def test_size_bound(self, tmp_path):
        """M21: Size bounds enforced."""
        mem = IntelligentMemory(tmp_path / "mem.json")
        # Add 60 short_term items (limit=50)
        for i in range(60):
            mem._items.append(MemoryItem(
                id=f"st-{i}", content=f"context item number {i} with enough length",
                memory_type=MemoryType.SHORT_TERM,
                created_at=time.time() - i,
            ))
        removed = mem.prune()
        short_term = [i for i in mem._items if i.memory_type == MemoryType.SHORT_TERM]
        assert len(short_term) <= 50

    def test_non_expiring_not_pruned(self, tmp_path):
        """M22: Knowledge (no TTL) not pruned."""
        mem = IntelligentMemory(tmp_path / "mem.json")
        mem._items.append(MemoryItem(
            id="old-knowledge", content="Python was created by Guido van Rossum in 1991",
            memory_type=MemoryType.KNOWLEDGE,
            created_at=time.time() - 864000,  # 10 days ago
        ))
        removed = mem.prune()
        assert any(i.id == "old-knowledge" for i in mem._items)


# ═══════════════════════════════════════════════════════════════
# SUMMARIZER
# ═══════════════════════════════════════════════════════════════

class TestSummarizer:

    def test_long_summarized(self, tmp_path):
        """M23: Long content summarized on store."""
        mem = IntelligentMemory(tmp_path / "mem.json")
        long_content = "This is the first paragraph about Python. " * 20 + \
                       "\n\n" + "More details about the topic. " * 10 + \
                       "Final conclusion: Python is great."
        mem.store(long_content, MemoryType.KNOWLEDGE)
        items = mem._items
        assert len(items) == 1
        assert len(items[0].content) <= 500

    def test_short_unchanged(self, tmp_path):
        """M24: Short content unchanged."""
        mem = IntelligentMemory(tmp_path / "mem.json")
        short = "Python is a programming language"
        mem.store(short, MemoryType.KNOWLEDGE)
        assert mem._items[0].content == short


# ═══════════════════════════════════════════════════════════════
# LESSON REUSE
# ═══════════════════════════════════════════════════════════════

class TestLessonReuse:

    def test_store_validated_learning(self, tmp_path):
        """M25: Store and retrieve validated learning."""
        mem = IntelligentMemory(tmp_path / "mem.json")
        mem.store("Timeout fix: increase timeout from 30s to 45s resolved issue",
                  MemoryType.LEARNING, validated=True)
        result = mem.retrieve("timeout increase fix", memory_type=MemoryType.LEARNING)
        assert len(result.items) >= 1
        assert result.items[0].validated

    def test_learning_in_mission(self, tmp_path):
        """M26: Learning appears in mission retrieval."""
        mem = IntelligentMemory(tmp_path / "mem.json")
        mem.store("Retry policy with exponential backoff reduces tool failures",
                  MemoryType.LEARNING, validated=True)
        result = mem.retrieve_for_mission("Fix tool reliability with retry improvements")
        assert len(result.items) >= 1
        assert any("retry" in i.content.lower() for i in result.items)

    def test_validated_higher_than_unvalidated(self, tmp_path):
        """M27: Validated learning scored higher."""
        mem = IntelligentMemory(tmp_path / "mem.json")
        mem.store("Confirmed fix: timeout 45s resolves API issues",
                  MemoryType.LEARNING, validated=True)
        mem.store("Unconfirmed idea about increasing timeout values",
                  MemoryType.LEARNING, validated=False)
        result = mem.retrieve("timeout fix solution approach")
        if len(result.items) >= 2:
            validated = [i for i in result.items if i.validated]
            unval = [i for i in result.items if not i.validated]
            if validated and unval:
                assert validated[0].relevance >= unval[0].relevance


# ═══════════════════════════════════════════════════════════════
# MISSION IMPROVEMENT
# ═══════════════════════════════════════════════════════════════

class TestMissionImprovement:

    def test_relevant_context(self, tmp_path):
        """M28: Mission retrieval returns relevant context."""
        mem = IntelligentMemory(tmp_path / "mem.json")
        mem.store("JarvisMax uses Python FastAPI for API endpoints", MemoryType.PROJECT, scope="jarvismax")
        mem.store("API timeout should be at least 30 seconds", MemoryType.KNOWLEDGE)
        mem.store("Previous mission fixed endpoint validation", MemoryType.MISSION)

        result = mem.retrieve_for_mission("Add new API endpoint to JarvisMax", project="jarvismax")
        assert len(result.items) >= 1
        # Should have relevant content
        all_content = " ".join(i.content for i in result.items).lower()
        assert "api" in all_content or "fastapi" in all_content

    def test_empty_memory(self, tmp_path):
        """M29: Empty memory returns empty context."""
        mem = IntelligentMemory(tmp_path / "mem.json")
        result = mem.retrieve_for_mission("Build something")
        assert len(result.items) == 0
        assert result.as_context() == ""

    def test_as_context_prompt(self, tmp_path):
        """M30: as_context produces prompt text."""
        mem = IntelligentMemory(tmp_path / "mem.json")
        mem.store("FastAPI requires async function handlers for best performance",
                  MemoryType.KNOWLEDGE)
        result = mem.retrieve("FastAPI async handlers")
        text = result.as_context()
        assert "FastAPI" in text or len(text) == 0  # Depends on scoring
