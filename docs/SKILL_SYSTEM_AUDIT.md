# Skill System Audit

## State Before This Work

`core/skills/` was ABSENT. No procedural memory existed.

## State After This Work

**Verdict: IMPLEMENTED AND USABLE**

All modules exist and pass 25/25 tests.

### Modules

| File | Lines | Purpose |
|---|---|---|
| `core/skills/skill_models.py` | 78 | Skill + SkillStep dataclasses |
| `core/skills/skill_registry.py` | 126 | JSONL-backed persistent storage |
| `core/skills/skill_retriever.py` | 139 | TF-IDF cosine similarity retrieval |
| `core/skills/skill_builder.py` | 212 | Gated skill creation (anti-noise) |
| `core/skills/skill_service.py` | 147 | Unified facade |

Storage: `workspace/skills.jsonl` (append-friendly, grep-friendly)

### MetaOrchestrator Integration

Skills are injected **before** planning (`prior_skills` in mission context).
Skills are evaluated **after** mission success via `record_outcome()`.

```python
# Before planning
skill_context = skill_service.retrieve_for_mission(goal)

# After success
skill_service.record_outcome(mission_id, goal, result, status)
```

### Creation Gates (anti-noise)

A skill is created only when:
- Mission status is DONE/success
- Goal length ≥ 10 chars
- Result length ≥ 80 chars
- Confidence ≥ 0.4
- No near-duplicate exists (cosine similarity < 0.75)

### Retrieval

Uses TF-IDF word overlap + cosine similarity. No external ML deps.
Tags-based fallback for low text-similarity cases.

## Remaining Limitations

- No vector embeddings (intentional — avoids heavy deps)
- Confidence is caller-provided, not auto-computed
- Skills accumulate but no auto-pruning of stale skills yet
