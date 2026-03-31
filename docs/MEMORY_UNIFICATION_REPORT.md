# Memory Unification Report

## Problem
16 memory files, 2 competing entry points (MemoryFacade vs MemoryBus),
direct imports from specialized backends scattered across API routes.

## Solution

### Canonical Entry: core/memory_facade.py
Added convenience methods to MemoryFacade:
- `store_decision()` — audit trail entries
- `store_failure()` — failure learning entries
- `store_outcome()` — mission result entries
- `get_decisions()` — retrieve decisions
- `get_failures()` — retrieve failures

### Memory Layers (conceptual)
| Layer | Storage | Entry Point |
|-------|---------|-------------|
| Working | in-memory (MissionContext) | MetaOrchestrator |
| Knowledge | JSONL + vector backends | MemoryFacade.store() |
| Procedural | workspace/skills.jsonl | core/skills/ |
| Decision | JSONL via MemoryFacade | MemoryFacade.store_decision() |

### Ranking: memory/memory_ranker.py
Cosine similarity + recency + confidence boost.

### Compaction: memory/memory_compactor.py
Prune empty, old low-confidence, expired working memory.

### What Remains
- MemoryBus (801 lines): still used by 3 API routes. Contains vector/postgres logic.
  Will be absorbed into MemoryFacade backends when postgres is stabilized.
- Direct decision_memory imports in api/routes/missions.py: functional, not urgent.
