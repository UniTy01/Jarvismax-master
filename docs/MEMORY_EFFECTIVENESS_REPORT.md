# Phase 3: Memory Effectiveness

## Status: EFFECTIVE ✅

### Memory layers (4, clear)
1. Working memory: `working_memory.py` — bounded, per-mission, token-capped
2. Knowledge memory: `MemoryFacade` — search, store, ranked retrieval
3. Procedural memory: `core/skills/` — JSONL, cosine retrieval, refinement
4. Decision memory: `DecisionTrace` — JSONL audit per mission

### Noise control
- memory_decay.py: unused entries lose confidence over time
- memory_compactor.py: TTL expiry + dedup
- working_memory.py: token budget prevents prompt flooding

### Retrieval quality
- memory_ranker.py: cosine + recency + confidence + frequency
- skill_retriever.py: cosine + confidence + use_count + problem_type match

### Linking
- memory_linker.py: missions↔skills↔failures cross-referencing
