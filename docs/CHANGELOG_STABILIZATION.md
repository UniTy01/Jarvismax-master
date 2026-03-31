# CHANGELOG_STABILIZATION.md

> Engineering log — Full Convergence (2026-03-26)

## API Consolidation
- DELETE `api/control_api.py` (627 lines, zero importers)
- FIX `api/main.py` docstring: "WIP" → "Canonical API"
- FIX duplicate `monitoring_router` mount (was mounted 2×)
- FIX duplicate `dashboard_router` mount (was mounted 2×)
- ADD `/api/v1/missions/{id}/stream` route alias (Flutter SSE fix)

## Entrypoint Consolidation
- DEPRECATE `start_api.py` — now delegates to main.py
- MARK `jarvis.py` as EXPERIMENTAL
- CONFIRM `main.py` as single Docker CMD

## Execution Hardening
- FIX `core/agent_loop.py` — executor.desktop_env imports → lazy (fail-open)
- RESTORE `executor/` files (runner, supervised_executor, etc.)
- VERIFY shell=True paths are properly guarded

## App-First Architecture
- FIX Flutter `api_config.dart` profiles: all ports 7070 → 8000
- FIX Flutter `settings_screen.dart` preset buttons: 7070 → 8000
- FIX Flutter `dashboard_screen.dart` preset buttons: 7070 → 8000
- ADD SSE stream route alias for Flutter compatibility

## Telegram Isolation
- MOVE `jarvis_bot` Docker service to `profiles: ["telegram"]`
- CONFIRM `main.py` Telegram startup is fail-open (try/except)

## Dead Code Removal
- DELETE `api/control_api.py` (split-brain API eliminated)
- DELETE `scheduler/` (zero imports)
- DELETE `experiments/` (zero production imports)
- DELETE `archive/` (stale scripts)
- DELETE `core/memory/` (empty directory)
- UNTRACK `workspace/*.py` (runtime artifacts)

## Documentation
- UPDATE `ARCHITECTURE.md` — app-first, API mission flow
- UPDATE `README.md` — canonical quick start
- UPDATE `background_dispatcher.py` docstring — MetaOrchestrator not V2
- MOVE 6 report .md files from root to `docs/`
- CREATE `jarvis_bot/README.md` — marked legacy
- CREATE `self_improve/README.md`, `self_improvement/README.md`

## CI/CD
- FIX `.github/workflows/deploy.yml` — run specific test suites
- ADD `pytest>=7.0.0` to `requirements.txt`
- REMOVE Telegram deploy notification from CI

## Tests
- CREATE `tests/test_stabilization_final.py` (31 tests)
- VERIFY all 7 test suites pass (220+ tests, 0 failures)

## Convergence Final

### Dead Test Removal
- REMOVE test_control_layer.py Blocs 5+6 (ControlAPI tests, 363 lines)
- REMOVE test_improvements.py Test 8 (ControlAPI handler tests, 137 lines)
- VERIFY remaining tests pass: 63 PASS in control_layer, 31 PASS in improvements

### Documentation Cleanup
- ARCHIVE 15 historical audit/convergence docs to docs/archive/
- CREATE docs/ARCHITECTURE_REALITY.md — true runtime map
- CREATE docs/CONSOLIDATION_ACTIONS.md — what was done
- CREATE docs/STABILITY_STATUS.md — current level + risks + next steps

## Final Convergence

### Runtime Bugs Fixed
- FIX core/action_executor.py: health check URL http://localhost:7070 → :8000
- FIX executor/handlers.py: health check URL http://localhost:7070 → :8000
- FIX api/main.py docstring: removed stale "ControlAPI en fallback" reference

### Transitional Artifacts Removed
- DELETE jarvismax_app/android_scaffold_backup/ (19 files, scaffold no longer needed)

### Zero Remaining Inconsistencies
- Zero references to port 7070 in production code
- Zero references to ControlAPI in production code
- Zero Telegram-first language in canonical docs
- Zero references to deleted modules (scheduler, experiments, archive)
