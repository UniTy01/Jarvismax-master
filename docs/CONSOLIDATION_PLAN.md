# CONSOLIDATION_PLAN.md

> Deep Stabilization — 2026-03-26

## What Was Unified

### API → ONE truth
- `api/main.py` is the single canonical API
- `api/control_api.py` deleted (zero importers)
- Duplicate router mounts removed (monitoring×2, dashboard×2)
- Outdated "WIP" docstring replaced with "Canonical API"

### Entrypoint → ONE truth
- `main.py` is the single canonical entrypoint (Docker CMD)
- `start_api.py` deprecated (delegates to main.py via os.execvp)
- `jarvis.py` marked EXPERIMENTAL

### Orchestration → ONE truth
- `MetaOrchestrator` is the single entry point for all missions
- `JarvisOrchestrator` and `OrchestratorV2` are internal delegates only
- No production code directly instantiates V1 or V2

### Interface → App-first
- Flutter app profiles updated to port 8000
- SSE stream route alias added for Flutter compatibility
- Telegram moved to Docker profile (opt-in)
- Telegram startup is fail-open in main.py

## What Was Removed

| Item | Lines | Reason |
|------|-------|--------|
| `api/control_api.py` | 627 | Dead — zero production importers |
| `scheduler/` | 348 | Dead — zero imports |
| `experiments/` | 631 | Dead — zero production imports |
| `archive/` | ~170 | Legacy scripts, no value |
| Duplicate router mounts | ~12 | monitoring_router, dashboard_router mounted 2× each |
| workspace/*.py (tracked) | 8 files | Runtime artifacts, gitignored |

## What Was Deprecated

| Item | Status | Replacement |
|------|--------|-------------|
| `start_api.py` | Prints warning, forwards to main.py | `python main.py` |
| `jarvis.py` | Marked EXPERIMENTAL | App + API |
| `jarvis_bot` Docker service | Profile-gated (`--profile telegram`) | Telegram in main.py (optional) |

## What Remains Temporarily for Compatibility

| Item | Why | When to Remove |
|------|-----|----------------|
| `self_improve/` (V0) | bot.py uses SelfImproveEngine 5× | When bot migrates to V2 or is removed |
| `self_improvement/` (V1) | api/main.py uses failure collector 8× | When merged into V2 |
| `core/orchestrator.py` | MetaOrchestrator delegate | When MetaOrchestrator absorbs the logic |
| `core/orchestrator_v2.py` | MetaOrchestrator delegate | Same |
| `executor/` | core/agent_loop.py imports desktop_env | When agent_loop is modernized |

## Why Each Decision Improves Coherence

- **Deleting control_api** eliminates split-brain API behavior entirely
- **Removing duplicate mounts** prevents route conflicts and confusing OpenAPI docs
- **Port 8000 everywhere** means one truth for the Flutter app
- **SSE stream alias** fixes a real runtime bug (Flutter couldn't stream)
- **CI with specific test suites** prevents false-green CI runs
- **pytest in requirements** makes CI reproducible
