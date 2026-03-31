# Skill System — Procedural Memory for JarvisMax

## Purpose

The skill system stores reusable problem-solving procedures learned from
successful mission executions. It enables Jarvis to:

1. Remember how it solved problems before
2. Retrieve relevant procedures before executing similar tasks
3. Improve consistency and reduce repeated problem-solving
4. Build confidence through successful reuse

## Architecture Placement

```
Mission arrives
    │
    ▼
MetaOrchestrator.run_mission()
    │
    ├── 1. SkillService.retrieve_for_mission(goal)  ← PRE-EXECUTION
    │       Returns relevant prior skills for planning context
    │
    ├── 2. Normal planning + execution flow
    │       (JarvisOrchestrator / OrchestratorV2)
    │
    └── 3. SkillService.record_outcome(...)         ← POST-EXECUTION
            Maybe creates a skill if criteria met
```

The skill system is an **extension** of MetaOrchestrator, not a parallel system.
It does not replace planning, memory, or execution.

## Module Structure

```
core/skills/
    __init__.py          — Public API (Skill, SkillService, get_skill_service)
    skill_models.py      — Skill + SkillStep dataclasses
    skill_registry.py    — JSONL-backed persistent storage
    skill_retriever.py   — Cosine similarity search + scoring
    skill_builder.py     — Creation criteria, duplicate detection, merging
    skill_service.py     — Unified facade + singleton
api/routes/skills.py     — REST API for inspection
tests/test_skill_system.py — 25 lifecycle tests
```

Storage: `workspace/skills.jsonl` (append-friendly, consistent with MemoryFacade pattern).

## Skill Lifecycle

### Creation Criteria

A skill is only created when ALL conditions are met:
- Mission status = DONE
- Goal length >= 10 characters
- Result length >= 80 characters
- Confidence >= 0.4
- No near-duplicate exists (cosine similarity < 0.75)

### Duplicate Handling

When a duplicate is detected:
- The existing skill is updated (not replaced)
- Confidence is recalculated (weighted average)
- New tools are merged
- use_count incremented

### Retrieval

Before execution, relevant skills are found by:
1. Tokenize query (lowercase, alpha-only)
2. Compute cosine similarity against each skill
3. Apply confidence boost (+0.1 * confidence)
4. Apply use_count boost (up to +0.05)
5. Filter by min_score (default 0.15) and min_confidence (default 0.3)
6. Return top_k results (default 3)

Retrieved skills are injected into `ctx.metadata["prior_skills"]` for planning.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/v2/skills | List all skills |
| GET | /api/v2/skills/stats | System statistics |
| GET | /api/v2/skills/search?q=... | Search by similarity |
| GET | /api/v2/skills/{id} | Get one skill |
| DELETE | /api/v2/skills/{id} | Delete a skill |

## Limitations

- No vector embeddings (uses word-overlap cosine — sufficient for 100s of skills)
- No LLM-based skill extraction (heuristic steps only)
- Skills influence planning context but don't directly control execution
- No automatic skill pruning yet (manual delete via API)

## Future Extension Points

- Vector embedding retrieval (via Qdrant, already available)
- LLM-assisted skill summarization
- Automatic confidence decay for unused skills
- Skill chains (prerequisite ordering)
- Skill versioning
