# Memory Upgrade Report

## Before
- MemoryFacade (single entry point)
- Memory ranker (cosine word overlap)
- Memory compactor (TTL, dedup)

## After
1. **Memory decay** (Hermes): `memory/memory_decay.py`
   - 0.01/day confidence loss after 7-day grace period
   - High-use items decay slower (use_count bonus)
   - Dry run support for safety

2. **Bounded working memory** (Hermes): `memory/working_memory.py`
   - Token-budget-capped context window per mission
   - Relevance-ranked item selection
   - Automatic eviction of low-relevance items
   - Prompt rendering for LLM context injection

3. **Memory linker**: `memory/memory_linker.py`
   - Links missions↔skills↔failures↔decisions
   - 7 link types (mission_created_skill, failure_led_to_lesson, etc.)
   - get_mission_graph() for cross-entity queries
   - IMPROVED BEYOND all references (no reference system has this)

## Canonical layers
- Working memory (bounded, per-mission)
- Knowledge memory (MemoryFacade)
- Procedural memory (skills)
- Decision memory (DecisionTrace)

## What was NOT copied
- Hermes FTS5 session archive (JSONL + cosine sufficient)
- Honcho user modeling (different product)
