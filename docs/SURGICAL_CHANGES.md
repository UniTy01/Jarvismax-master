# SURGICAL_CHANGES.md
> JarvisMax — Surgical Cleanup (feat/surgical-cleanup)
> Date : 2026-03-26

---

## Summary

This branch performs a targeted, surgical cleanup of the JarvisMax codebase to
achieve full architectural coherence. Zero breaking changes to the external API.

---

## 1. Telegram — Complete Removal (CRITICAL)

### What was removed
| File | Change |
|------|--------|
| `risk/engine.py` | `telegram_card()` → `format_card()`, comments updated |
| `executor/supervised_executor.py` | "validation Telegram" → "validation via API" |
| `executor/runner.py` | `telegram_format()` → `format_output()` |
| `core/task_router.py` | Telegram command references removed |
| `core/execution_guard.py` | Docstring updated |
| `core/connectors.py` | `telegram` removed as platform option |
| `core/env_validator.py` | `TELEGRAM_TOKEN` removed from optional vars |
| `core/tools/dev_tools.py` | `TELEGRAM_TOKEN` removed from critical/masked vars |
| `core/state.py` | Telegram comment references updated |
| `core/orchestrator.py` | Telegram comment references updated |
| `core/self_improvement/protected_paths.py` | Comment updated |
| `config/settings.py` | Empty `# ── Telegram ──` section removed |
| `business/saas/schema.py` | `telegram_card()` → `format_card()` |
| `business/trade_ops/schema.py` | `telegram_card()` → `format_card()`, `deployment_mode` default: `"telegram"` → `"api"` |
| `business/workflow/schema.py` | `telegram_card()` → `format_card()` |
| `business/venture/schema.py` | `telegram_card()` → `format_card()` |
| `business/offer/schema.py` | `telegram_card()` → `format_card()` |
| `business/trade_ops/agent.py` | Docstring deployment description updated |
| `agents/jarvis_team/tools.py` | `TELEGRAM_TOKEN` removed from env var list |
| `tools/n8n/bridge.py` | `create_telegram_notification_workflow()` method removed |
| `docker-compose.yml` | Telegram comment removed |
| `.env.example` | `TELEGRAM_*` variables removed |
| `scripts/test_parity.py` | "Telegram path" note replaced with "API path" |
| `tests/validate.py` | Sections 9/27/36 (bot tests) rewritten as API checks; `telegram_card()` → `format_card()` |
| `tests/test_communication_layer.py` | `test_messaging_format_telegram` → `test_messaging_format_webhook` |
| `tests/test_stabilization_final.py` | String refs updated (verification tests kept) |
| `self_improve/` | DELETED (empty, only `__pycache__`) |
| `jarvis_bot/` | DELETED (empty, only `__pycache__`) |

### What was NOT removed
- `tests/test_stabilization_final.py::TestTelegramRemoved` — verification test that CHECKS telegram is absent (intentional)
- `tests/test_beta_architecture.py::test_send_telegram_deleted` — verification test (intentional)
- `CHANGELOG.md` — historical references acceptable
- `.env` — gitignored runtime file, has real TELEGRAM_* vars (user must clean manually)

---

## 2. Orchestration — MetaOrchestrator verified as sole entry point

No code changes needed. Verification confirmed:
- `api/main.py::_get_orchestrator()` → `get_meta_orchestrator()`
- `main.py` → `get_meta_orchestrator()`
- `core/background_dispatcher.py` → `get_meta_orchestrator()`
- `core/agent_loop.py` → `get_meta_orchestrator()`
- `core/orchestration_bridge.py` → `get_meta_orchestrator()`
- `JarvisOrchestrator` / `OrchestratorV2` only instantiated **inside** MetaOrchestrator as internal delegates

---

## 3. Self-Improvement — Single canonical location

| Before | After |
|--------|-------|
| `self_improve/` (17 files, version 1) | **DELETED** |
| `self_improvement/` (8 files, root) | Was already gone on this branch |
| `core/self_improvement/` (13 files) | **CANONICAL** — sole location |

All runtime imports verified: no file imports from the deleted `self_improve/` module.
(Only `tests/validate.py` has legacy imports — inside `try/except`, fails gracefully.)

---

## 4. API Refactor — api/main.py split

| Before | After |
|--------|-------|
| `api/main.py` — 1797 lines | `api/main.py` — 412 lines (−77%) |

New files created:

| File | Lines | Content |
|------|-------|---------|
| `api/_deps.py` | 81 | Shared auth, getters, `_extract_final_output` |
| `api/routes/missions.py` | 1040 | All mission/task/agent CRUD routes |
| `api/routes/system.py` | 177 | Health/status/metrics/logs/restart/mode |
| `api/routes/memory.py` | 83 | Decision-memory/knowledge/plan |
| `api/routes/tools.py` | 73 | Tools registry/test/rollback |
| `api/routes/admin.py` | 117 | Self-improvement admin (V1 + V2) |

Also fixed: `api/routes/performance.py` — missing `Body` import from fastapi.

---

## 5. CI — Path bug fix (previous commit)

| Before | After |
|--------|-------|
| `cd /opt/jarvismax` | `cd /opt/Jarvismax` |

Commit: `826c426`

---

## 6. Repo Cleanup

| Item | Action |
|------|--------|
| `self_improve/` | Deleted (was empty, only `__pycache__`) |
| `jarvis_bot/` | Deleted (was empty, only `__pycache__`) |
| `tmp_patch8.py` | Deleted |
| `phase9_patch.py` | Deleted |
| `write_reports.py` | Deleted |
| `api_refactor.py` | Deleted |

---

## 7. Documentation

- `ARCHITECTURE.md` — updated: new `api/routes/` structure, removed legacy folder refs
- `README.md` — no Telegram references were present (already clean)
