# Phase 4: Skill System Final

## Status: COHERENT ✅

### Lifecycle: create → retrieve → refine → decay
- Created: only from non-trivial successful missions (builder checks)
- Retrieved: before similar missions via context_assembler
- Refined: confidence boost on reuse, degrade on failure
- Decayed: unused skills lose confidence via memory_decay

### Dedup: cosine > 0.8 → skip creation
### Confidence: 0.0-1.0, asymptotic boost, linear degrade
### Problem-type matching: +0.15 retrieval boost for same type
### Storage: JSONL (workspace/skills.jsonl)
