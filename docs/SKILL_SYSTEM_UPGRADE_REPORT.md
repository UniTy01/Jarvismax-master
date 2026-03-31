# Skill System Upgrade Report

## Before
- JSONL skill storage
- Cosine similarity retrieval
- Skill builder with duplicate detection
- MetaOrchestrator integration

## After
1. **Skill refinement on reuse** (Hermes): `skill_service.refine_skill()`
   - Successful reuse: confidence += (1.0 - confidence) * 0.1
   - Failed reuse: confidence -= 0.05
   - Wired into MetaOrchestrator: prior skills refined after DONE

2. **Problem-type matching boost**: `skill_retriever.py`
   - +0.15 score bonus when skill.problem_type matches mission type
   - Enables cross-mission skill reuse for same problem class

## Dedup: ALREADY STRONG
- Builder checks cosine similarity > 0.8 before creating new skill
- No change needed

## Confidence scoring: ALREADY STRONG + REFINED
- Initial confidence set at creation
- Now: boosted/degraded on each reuse
- Now: decayed over time if unused (via memory_decay)

## What was NOT copied
- Hermes markdown skill files (JSONL is more machine-friendly)
- Voyager skill library structure (our flat JSONL is simpler)
