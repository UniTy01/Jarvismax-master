# CONSOLIDATION_ACTIONS.md

> Convergence Final — 2026-03-26

## Unified

| What | From | To |
|------|------|----|
| API | api/main.py + api/control_api.py | api/main.py only |
| Entrypoint | main.py + start_api.py + jarvis.py | main.py only |
| Orchestrator | MetaOrchestrator + direct V1/V2 usage | MetaOrchestrator only |
| Status enum | 3 definitions | 1 in core/state.py |
| Flutter port | mix of 7070/8000 | 8000 everywhere |
| Docker bot | default service | opt-in profile |

## Removed

| What | Lines | Reason |
|------|-------|--------|
| `api/control_api.py` | 627 | Zero importers, split-brain eliminated |
| `scheduler/` | 348 | Zero imports |
| `experiments/` | 631 | Zero production imports |
| `archive/` | ~170 | Stale scripts |
| `send_telegram.py` + `send_telegram_v5.py` | 69 | Hardcoded bot token |
| `workspace/*.py` (tracked) | 262 | Runtime artifacts |
| Test blocs for ControlAPI | ~500 | Testing deleted code |
| 15 historical docs → `docs/archive/` | ~3000 | Outdated audit notes |

## Deprecated

| What | Replacement | Action |
|------|------------|--------|
| `start_api.py` | `python main.py` | Prints warning, delegates |
| `jarvis.py` | App + API | Marked EXPERIMENTAL |
| `jarvis_bot` Docker service | Telegram in main.py | Profile-gated |

## Simplified

- Router mount section: removed 2 duplicate mounts (monitoring, dashboard)
- `api/main.py` docstring: "WIP" → "Canonical API"
- `core/background_dispatcher.py` docstring: says MetaOrchestrator (truth)
- Root: only README, ARCHITECTURE, CHANGELOG remain
- docs/: 15 historical files archived, 13 active remain
