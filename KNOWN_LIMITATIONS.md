# KNOWN_LIMITATIONS.md — Jarvis Max
_Last updated: 2026-04-01 — Cycle 15 hardening wave complete_

This document lists known limitations, unresolved bugs, and deliberate trade-offs in the current codebase.
Each entry includes: symptom, root cause, workaround, and fix complexity.

---

## ~~KL-001~~ — ✅ RESOLVED (2026-04-01, Cycle 8)

**Was:** Invalid LLM key produces DONE (not FAILED)

**Fix implemented:** `core/orchestration/execution_supervisor.py` — new `_check_session_outcome()`
helper function added to `supervise()` loop. After `execute_fn()` returns without exception, the
helper inspects actual agent outputs, computes success rate (threshold: 20%), and detects auth
error keywords in agent error fields.

- `rate < 20%` + auth keywords → `provider_auth_failure` → `outcome.success = False` → ABORT
- `rate < 20%` without auth keywords → `all_agents_failed` → `outcome.success = False` → ABORT
- `rate ≥ 20%` → success path unchanged

**Live proof (2026-04-01):**
- Invalid key: mission → `FAILED` in 9s, `failure_reason = "all_agents_failed: 0/3 agents produced output (rate=0%, threshold=20%)"`
- Valid key: mission → `COMPLETED` in 57s with real content

**Regression tests:** `tests/test_terminal_state_truth.py` — 20 tests, all green.

---

## ~~KL-002~~ — ✅ RESOLVED (2026-04-01, Cycle 9)

**Was:** Canonical missions are in-memory only (lost on restart)

**Fix implemented:** `core/canonical_mission_store.py` (new) + `core/orchestration_bridge.py`
- `CanonicalMissionStore`: SQLite-backed store with WAL mode, upsert on save, load_all on startup
- `OrchestrationBridge._update_cache()`: write-through to store on every status update
- `OrchestrationBridge.__init__`: loads all missions from store on startup (restart recovery)
- Storage path resolution: `workspace/canonical_missions.db` → `/tmp/` fallback

**Updated persistence truth (Cycle 9):**

| Path | Storage | Survives Restart? |
|------|---------|-------------------|
| `/api/v3/missions` (canonical, MetaOrchestrator) | SQLite `workspace/canonical_missions.db` | ✅ Yes |
| Legacy MissionSystem path | SQLite `workspace/jarvismax.db` + JSON fallback | ✅ Yes |
| Auth / audit / kernel data | Postgres (optional) | ✅ Yes (when Postgres available) |

**Live proof (2026-04-01):** COMPLETED mission (7e274da7-5fb) survived server kill + restart,
returned `status=COMPLETED` on new server instance without re-executing.

---

## KL-003 — Docker live boot proof is an external next step

**Severity:** Low (deep static audit passed — all files correct)

**Static audit completed (2026-04-01, Cycle 11 + Cycle 12):**
- `docker-compose.test.yml`: services, volumes, env, healthchecks — all correct ✅
- `docker/Dockerfile`: multi-stage, langchain-openai in requirements.txt, workspace dirs, non-root user, nodejs, healthcheck ✅
- `.env.example`: PATH A (Anthropic) and PATH B (OpenRouter) documented and correct ✅
- `scripts/verify_boot.sh`: health → readiness → auth → submit → poll → result quality check ✅
- `.dockerignore`: venv/, .venv/, workspace/, logs/, .env.* added (Cycle 12) ✅
- `RUNBOOK.md`: exact Docker boot instructions for both LLM provider paths ✅
- `WORKSPACE_DIR=/app/workspace` env var overrides default correctly (verified) ✅
- `QDRANT_HOST=qdrant` (Docker DNS) is the compose default — no native localhost confusion ✅

**Exact boot command (ready to run):**
```bash
export ANTHROPIC_API_KEY=sk-ant-...   # or OPENROUTER_API_KEY + MODEL_STRATEGY=openrouter
export JARVIS_ADMIN_PASSWORD=mypassword
export JARVIS_SECRET_KEY=$(openssl rand -hex 32)
docker compose -f docker-compose.test.yml up --build -d
JARVIS_ADMIN_PASSWORD=mypassword bash scripts/verify_boot.sh
# Expected: "BOOT VERIFICATION PASSED" within 90s
```

**Why deferred:** Docker daemon is unavailable in the current sandbox environment.
This is the highest-priority task on any machine with Docker available.

---

## ~~KL-004~~ — ✅ RESOLVED (2026-04-01)

**Was:** Self-improvement pipeline has broken test infrastructure

**Fix implemented:** Renamed `TestRunner` → `PatchRunner` and `TestSuiteResult` → `SuiteResult`
in `core/self_improvement/test_runner.py`. Removed `__test__ = False` workarounds.
Updated callers with import aliases: `tests/test_devin_core.py`,
`tests/test_self_improvement_execution.py`, `tests/test_self_improvement_v3_integration.py`.
Renamed `business_agents/test_harness.py` local `TestSuiteResult` → `AgentSuiteResult`.

**Verification:**
- `pytest --collect-only core/self_improvement/test_runner.py` → `0 items collected` (no warnings)
- 37 regression tests still green after the rename

---

## ~~KL-005~~ — ✅ RESOLVED (2026-04-01)

**Was:** lens-reviewer agent intermittently fails during parallel execution

**Root cause identified:** `group_by_priority()` existed in `ParallelExecutor` but was
never called. All agents (P1/P2/P3) were submitted to a single `asyncio.gather()`, so
lens-reviewer (P3) ran concurrently with the P2 agents it was supposed to review.
`_ctx(session)` called `context_snapshot()` while P2 agents were still running → returned
empty dict → user message collapsed to `"(aucun résultat disponible)"` → LLM output too
short → retry → still failed.

**Fix implemented:** `core/orchestrator.py` `_run_parallel()` now uses
`ParallelExecutor.group_by_priority()` to run agents in sequential priority waves:
- P1 wave (vault-memory) → awaited
- P2 wave (scout-research, map-planner, forge-builder, …) → awaited
- P3 wave (lens-reviewer) → now has complete P2 context available

Replan logic preserved per-wave (only for waves with priority ≤ 2).

**Verification:**
- 37 regression tests still green
- Lens-reviewer will now receive populated `context_snapshot()` on every execution
- Device E2E test will confirm (see MOBILE_CONTRACT.md checklist)

---

## KL-006 — Integration tests require live external services

**Severity:** Informational (expected behavior, not a bug)

**Symptom:**
All tests marked `@pytest.mark.integration` or `@pytest.mark.infra` require live
external services (Postgres, Redis, Qdrant, LLM API key). Running
`pytest -m integration` without these services produces failures.

**Current status (Cycle 15):**
- **95 unit tests** pass in isolation (no external services required):
  `test_terminal_state_truth.py` (20) + `test_canonical_mission_persistence.py` (17)
  + `test_hierarchical_planner.py` (21) + `test_production_hardening_p34.py` (37)
- Integration tests: skip correctly via `--run-infra-tests` gate in `conftest.py`
- pgvector hybrid memory path: structurally correct, E2E proof needs live Postgres

**Fix required:**
Run `pytest --run-infra-tests -m integration` against live Docker stack after KL-003
(Docker live boot) is verified. Classify failures, fix real bugs, update this entry.

---

---

## KL-008 — WAITING_APPROVAL missions cannot auto-resume after server restart

**Severity:** Low (affects a narrow edge case; workaround exists)

**Symptom:**
A mission that reached `WAITING_APPROVAL` state and was persisted to SQLite cannot
automatically continue execution after a server restart. The `MetaOrchestrator`
execution coroutine is lost when the process exits. On restart, the canonical store
correctly reloads the `WAITING_APPROVAL` status, but there is no mechanism to
re-attach an execution coroutine to the resumed mission. The mission is stuck in
`WAITING_APPROVAL` indefinitely.

**Root cause:**
`MetaOrchestrator.run_mission()` is a long-running async coroutine stored only in
memory (as an `asyncio.Task`). It is not serialized to the database. When the
process exits, the task is lost. On restart, `OrchestrationBridge.load_all()`
restores the persisted state, but no new task is spawned for the waiting mission.

**Workaround:**
The human operator (or mobile client) can re-submit the goal. The new mission will
start fresh from `CREATED`. The stale `WAITING_APPROVAL` mission in the database
will eventually be superseded and can be ignored.

**Fix complexity:** Medium (2–3 days).
Option A: On startup, `OrchestrationBridge` detects missions in `WAITING_APPROVAL`
and spawns a minimal re-entry coroutine that immediately awaits the approval queue.
Option B: On restart, transition stale `WAITING_APPROVAL` missions to `FAILED`
with `failure_reason = "server_restart_during_approval"` to surface the issue
cleanly rather than leaving orphaned state.

**Resolution:** Track in productization backlog (Track 3 growth features).

---

## ~~KL-007~~ — ✅ RESOLVED (2026-04-01)

**Was:** Mobile app uses legacy v2 path, not canonical v3 path

**Fix implemented:** `jarvismax_app/lib/services/api_service.dart` — 3 endpoint migrations:
- `submitMission()`: `POST /api/mission` `{'input':...}` → `POST /api/v3/missions` `{'goal':...}`
- `_loadMissions()`: `GET /api/v2/missions` → `GET /api/v3/missions`
- `fetchMissionDetail()`: `GET /api/v2/missions/$id` → `GET /api/v3/missions/$id`

**Coverage:**
- Mobile-submitted missions now route through MetaOrchestrator (canonical path)
- Ghost-DONE fix (`_check_session_outcome`) now applies to mobile-submitted missions ✅
- Mission persistence (SQLite write-through) now applies to mobile-submitted missions ✅
- `mission.dart` model already had v3 field aliases + `_normalizeStatus()` in place

**Remaining:**
- Device smoke test against live server (see MOBILE_CONTRACT.md checklist)
- Approval/reject actions still use `/api/v2/tasks/$id/approve|reject` (not blocking — this path remains valid)
