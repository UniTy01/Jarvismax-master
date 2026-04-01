# Memory/Skill Writeback Consolidation

## Status: CONTROLLED ✅

### Write paths (all via MemoryFacade)
- Success: store_outcome() → knowledge memory
- Failure: store_failure() → failure memory (for future pre-exec matching)
- Lesson: learning_loop → store_failure(context, error, recovery)
- Skill: record_outcome() → create if non-trivial + DONE
- Refinement: refine_skill() → boost/degrade confidence

### Noise control
- memory_decay: unused entries lose confidence
- memory_compactor: TTL expiry + dedup
- working_memory: bounded token budget
- Skill dedup: cosine > 0.8 → skip creation
