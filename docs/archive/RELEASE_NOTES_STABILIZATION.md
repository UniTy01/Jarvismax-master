# RELEASE_NOTES — Production Stabilization

_Date: 2026-03-26_  
_Version: 2.1.0-stable_

---

## Security Fixes (Critical)

- **DELETED** `send_telegram.py` and `send_telegram_v5.py` — contained plaintext Telegram bot token
  - **ACTION REQUIRED**: Revoke and rotate the bot token `8729616478:AAH...`
- **REMOVED** hardcoded production IP `77.42.40.146:8000` from Flutter app
  - Replaced with configurable emulator default `10.0.2.2:8000`
- **HARDENED** all `shell=True` subprocess calls in `agents/jarvis_team/`
  - Converted to `shlex.split()` + `shell=False` (5 call sites)
- **REMOVED** 235MB of APK binaries from git history tracking

## Architecture Corrections

- **Unified orchestrator path**: `main.py` and `jarvis_bot/bot.py` now use `MetaOrchestrator` as canonical orchestrator (with fallback to `JarvisOrchestrator`)
- **Deprecated** `start_api.py` — now prints deprecation warning, directs to `main.py`
- **Canonical API** clarified: `api/main.py` (FastAPI, port 8000)

## Repo Cleanup

- Archived 4 dead code directories to `archive/`:
  - `executor/` (2000+ lines, never integrated)
  - `self_improve/` (superseded by core engine)
  - `self_improvement/` (superseded)
  - `experiments/` (never imported)
- Moved 7 outdated root-level reports to `docs/archive/`
- Archived Windows batch scripts (hardcoded local paths)
- Renamed `.env.production` → `.env.production.example`
- Updated `.gitignore` (APKs, env files)

## Tests

- All existing test suites pass: 0 regressions
- Test suites verified:
  - `test_status_memory_consolidation` (35 tests)
  - `test_e2e_mission_lifecycle` (40 tests)
  - `test_hardening_safety` (56 tests)
  - `test_external_action_self_improvement` (43 tests)
  - `test_integration_deep`, `test_architecture_coherence` (legacy)

## Residual Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Bot token may still be in git history | HIGH | Rotate token immediately |
| `core/orchestrator.py` still large (1053 lines) | LOW | Gradual deprecation |
| `business/` directory still duplicates `core/business_pipeline.py` | LOW | Future consolidation |
| `memory/` directory still duplicates `core/memory/` | LOW | Future consolidation |
| Some tests are structural-only (check file existence) | LOW | Gradual test improvement |
| CI runs all 86 test files, many require deps | MEDIUM | Add pytest markers |

## Recommended Next Steps

1. **URGENT**: Rotate Telegram bot token (compromised in git history)
2. Consider `git filter-branch` or BFG to purge token from history
3. Consolidate `business/` → `core/business_pipeline.py`
4. Consolidate `memory/` → `core/memory/`
5. Add pytest markers (`@pytest.mark.integration`, `@pytest.mark.unit`)
6. Set up CI to only run unit tests by default
7. Consider removing `core/orchestrator.py` once MetaOrchestrator is proven stable
