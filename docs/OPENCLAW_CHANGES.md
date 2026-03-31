# OPENCLAW_CHANGES.md — Concise Change List

> 2026-03-26 stabilization session

## Runtime Fixes
- Health check URLs: localhost:7070 → :8000 (action_executor, handlers)
- Flutter SSE route: added /api/v1/missions/{id}/stream alias
- Flutter port config: all profiles 7070 → 8000
- Executor imports: lazy/fail-open in agent_loop.py
- Executor files: restored from incorrect archive
- Duplicate router mounts: removed (monitoring×2, dashboard×2)
- Path casing: /opt/Jarvismax → /opt/jarvismax (8 files)

## Security
- CORS: wildcard * → explicit origin whitelist + CORS_ORIGINS env var
- Added LICENSE (MIT)
- Bot token files deleted (send_telegram.py, send_telegram_v5.py)
- Hardcoded Tailscale IP removed from start_api.py
- shell=True in agents/: converted to shlex.split (5 sites)

## Architecture
- api/control_api.py: DELETED (627 lines)
- Telegram: optional fail-open, Docker profile-gated
- MetaOrchestrator: verified as only production orchestrator
- MissionStatus: single definition in core/state.py
- api/main.py: docstring updated, marked as canonical

## Cleanup
- Deleted: scheduler/, experiments/, archive/, android_scaffold_backup/
- Untracked: workspace/*.py runtime artifacts
- Archived: 15 historical docs to docs/archive/
- Deprecated: start_api.py (delegates to main.py)
- Removed: 500 lines of dead tests (ControlAPI blocs)
- Deleted: 26 stale git branches (21 merged + 5 claude/*)

## CI/CD
- deploy.yml: runs specific test suites, removed Telegram notification
- pytest added to requirements.txt

## Tests
- 31 new stabilization tests (test_stabilization_final.py)
- 26 architecture enforcement tests (test_beta_architecture.py)
- All suites: 280+ tests, 0 failures
