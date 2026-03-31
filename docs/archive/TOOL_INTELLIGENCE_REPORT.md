# Tool Intelligence Layer V1 — Report

**Branch:** `claude/tool-intelligence-v1`
**Date:** 2026-03-25
**Status:** MERGED-READY — 11/11 local, 24/24 VPS

---

## Phase 0 — Audit

### Files Analyzed

| File | Role | Gap |
|------|------|-----|
| `core/tool_registry.py` | Static tool definitions, semantic scoring via keyword overlap, `score_tool_relevance()`, `rank_tools_for_task()` | No runtime observation; scoring is static keyword matching only |
| `core/agent_runner.py` | Launches agents with timing logs (AGENT_RUN / AGENT_DONE) | Logs duration but does not persist per-tool outcome data |
| `core/knowledge/capability_scorer.py` | Domain-level scoring (coding, debugging, etc.) — JSON persistence, composite formula | Per-domain only; no per-tool granularity |
| `core/knowledge/pattern_detector.py` | Qdrant + KnowledgeMemory pattern detection for sequences, tool combos | Requires Qdrant; no lightweight local fallback for tool spam detection |
| `core/planner.py` | `build_plan()` assembles context dict injected into mission plan | No tool intelligence hooks; result dict accepts new keys safely |

### Key Findings

- **No per-tool runtime observation** existed before this layer. `score_tool_relevance()` uses keyword overlap on task description, not actual execution history.
- **No anti-spam protection**: a loop calling the same tool 4+ times was not detected anywhere.
- **`build_plan()` result dict** is the correct injection point — it already accepts arbitrary keys (`prior_knowledge`, `objective_context`, `self_improvement_context`). The `tool_intelligence_hints` key follows the same pattern.
- `capability_scorer.py` scoring formula (40% success / 30% speed / 20% errors / 10% retries) was reused as inspiration for `tool_scorer.py` (40% success / 20% stability / 20% speed / 20% retry).

---

## Architecture

```
core/tool_intelligence/
├── __init__.py          Feature flag: USE_TOOL_INTELLIGENCE env var
├── tool_observer.py     Records every tool call → JSON (workspace/tool_intelligence/observations.json)
├── tool_scorer.py       Computes 0-1 score per tool from observations, 5-min cache
├── anti_spam.py         In-memory streak/count guards (fail-open)
└── planner_hints.py     Injects hints into planner when flag enabled
```

### Data Flow

```
Tool call
   └─► tool_observer.record_tool_call()
           └─► workspace/tool_intelligence/observations.json
                   └─► tool_scorer.compute_tool_score()
                           └─► planner_hints.get_hints_for_planner()
                                   └─► result["tool_intelligence_hints"] in build_plan()

Concurrent:
   tool call ─► anti_spam.check_tool_allowed() ─► allowed / replan / request_validation
```

---

## Files Created / Modified

### Created

| File | Lines | Purpose |
|------|-------|---------|
| `core/tool_intelligence/__init__.py` | 6 | Feature flag |
| `core/tool_intelligence/tool_observer.py` | 78 | Observation layer, atomic JSON writes |
| `core/tool_intelligence/tool_scorer.py` | 107 | Effectiveness scoring + hint generation |
| `core/tool_intelligence/anti_spam.py` | 70 | Streak/limit protection |
| `core/tool_intelligence/planner_hints.py` | 24 | Planner integration |
| `tests/test_tool_intelligence.py` | 129 | 11 tests |

### Modified

| File | Change |
|------|--------|
| `core/planner.py` | +8 lines: inject `result["tool_intelligence_hints"]` after `self_improvement_context`, fail-open |

### Protected Files (untouched)
- `core/meta_orchestrator.py`
- `core/orchestrator.py`
- `core/orchestrator_v2.py`
- `api/schemas.py`

---

## Scoring Formula — tool_scorer.py

```
tool_score = success_rate * 0.4
           + stability     * 0.2   (1 - rollback_rate)
           + speed_score   * 0.2   (1 - avg_time/30s, clipped [0,1])
           + retry_score   * 0.2   (1 - avg_retries/3, clipped [0,1])

confidence = min(1.0, observation_count / 50)

preferred_tools: tool_score >= 0.7
tools_to_avoid:  tool_score < 0.3 AND confidence > 0.3
```

---

## Anti-Spam Guards

| Guard | Limit | Action |
|-------|-------|--------|
| Same-tool streak | 4 consecutive calls per task | `replan` |
| Objective tool budget | 30 total calls per objective | `request_validation` |
| Fail-open | Any check error | `proceed` (no crash) |

---

## Test Results

### Local (Python 3.14.3 / Windows)

```
tests/test_tool_intelligence.py — 11 passed in 0.19s
```

| # | Test | Result |
|---|------|--------|
| 1 | `test_tool_observation_records_usage` | PASSED |
| 2 | `test_tool_scoring_updates` | PASSED |
| 3 | `test_tool_sequence_pattern_detected` | PASSED |
| 4 | `test_tool_loop_detected` | PASSED |
| 5 | `test_tool_retry_limit_triggered` | PASSED |
| 6 | `test_tool_hint_injected` | PASSED |
| 7 | `test_fail_open_if_module_missing` | PASSED |
| 8 | `test_planner_behavior_unchanged_when_disabled` | PASSED |
| 9 | `test_json_fallback_if_qdrant_missing` | PASSED |
| 10 | `test_no_duplicate_logging` | PASSED |
| 11 | `test_tool_confidence_updates_over_time` | PASSED |

### VPS (Python 3.12.13 / Docker)

```
24 passed, 1 warning in 0.20s
```

| Suite | Tests | Result |
|-------|-------|--------|
| `test_tool_intelligence.py` | 11/11 | ALL PASSED |
| `test_stability.py` | 7/7 | ALL PASSED |
| `test_pipeline_guard.py` | 6/6 | ALL PASSED |

Warning: pytest cache permission (non-blocking, pre-existing).

---

## Activation

The layer is **off by default** (fail-open). To activate:

```bash
# In .env or docker-compose
USE_TOOL_INTELLIGENCE=true
```

When disabled, `get_hints_for_planner()` returns `{}` — planner behavior is strictly unchanged.

---

## Commits (in order)

```
2904acc feat: tool_observer.py — observation layer, JSON fallback
f374d24 feat: tool_scorer.py — effectiveness scoring 0-1 + hints
e625379 feat: anti_spam.py — streak/limit protection fail-open
019735a feat: planner_hints.py — hints injection for planner
8486524 fix: planner.py — inject tool_intelligence_hints (fail-open, 6 lines)
fd7c664 test: test_tool_intelligence.py — 11 tests
```

---

## Activation prod — conditions requises (2026-03-25)

Conditions pour passer `USE_TOOL_INTELLIGENCE=true` en production :

- [ ] `workspace/tool_intelligence/observations.json` alimenté sur **≥ 10 missions réelles**
- [ ] Aucune boucle détectée : streak < 4 dans `anti_spam.py` sur 48h continus
- [ ] Score moyen stable sur 48h (pas de dérive > 0.2 entre fenêtres 24h)
- [ ] Suite tests **12/12** toujours verte (test_tool_intelligence.py)
- [ ] Aucun impact négatif sur latence planner (p95 < 200ms ajout)

### Vérification observationnelle (exemple)

```bash
docker exec jarvis_core python -c "
from core.tool_intelligence.tool_observer import record_tool_call
record_tool_call('shell_execution', True, 1.2, 0, 'test_mission_obs')
import json, pathlib
p = pathlib.Path('/app/workspace/tool_intelligence/observations.json')
data = json.loads(p.read_text()) if p.exists() else []
print(f'observations.json: {len(data)} entries, last={data[-1] if data else None}')
"
```

### Merge

- `claude/tool-intelligence-v1` → `master` : **MERGÉ** le 2026-03-25 (fast-forward)
- Tests VPS : **12/12** passent
