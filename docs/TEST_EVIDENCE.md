# TEST EVIDENCE — feat/surgical-cleanup
**Date**: 2026-03-26
**Command**: docker exec jarvis_core python3 -m pytest tests/ -v --tb=short
**Duration**: 83.38s (1 minute 23 seconds)

---

## RESULTATS GLOBAUX

| Metric | Count |
|--------|-------|
| Total tests | 1530 |
| PASSED | 1456 |
| FAILED | 61 |
| SKIPPED | 13 |
| Pass rate | 95.9% |

---

## TESTS PASSES PAR SUITE (1456 passing)

### test_stabilization_final.py — TestTelegramRemoved (4/5 pass)
- test_no_telegram_in_requirements — PASS
- test_no_telegram_in_main_py — PASS
- test_no_telegram_in_readme — PASS
- test_no_self_improve_dir — FAIL (self_improve/ empty dir still exists)
- test_canonical_self_improvement_exists — PASS

### test_beta_architecture.py — TestNoMockExecution
- test_send_telegram_deleted — PASS
- test_api_main_uses_orchestrator — FAIL (api/main.py structure changed)
- Other tests in this suite largely pass

### test_v3_architecture.py — broadly passing
- test_memory_store_ttl and related — PASS

### test_communication_layer.py — 2 FAIL
- test_messaging_format_webhook — FAIL
- test_messaging_content_limit — FAIL
- Other communication tests — PASS

---

## TESTS ECHOUES PAR CATEGORIE (61 failing)

### Category 1: Missing module — scheduler (7 tests)
Affected: tests/test_scheduler.py (all 7 tests)
Error: ModuleNotFoundError: No module named scheduler
Tests: test_scheduled_task_manual_is_due, test_scheduled_task_interval_is_due,
       test_scheduled_task_interval_not_due, test_scheduled_task_cron_window,
       test_scheduled_task_disabled, test_night_scheduler_add_and_list,
       test_night_scheduler_remove
Root cause: scheduler/ module removed from codebase, tests not updated/removed

### Category 2: Async test infrastructure (26 tests)
Affected: test_circuit_breaker.py (5), test_circuit_breaker_edge.py (4),
          test_execution_guard.py (6), test_validator.py (4),
          test_observability_helpers.py (4), others
Error: Failed: async def function without a pytest-asyncio decorator
Root cause: pytest.ini missing asyncio_mode=auto, pre-existing issue
NOT introduced by this branch

### Category 3: API route renames (4 tests)
Affected: tests/test_stabilization_final.py::TestAPICoherence
- test_v1_stream_route_exists — FAIL
- test_v2_missions_submit_exists — FAIL
- test_v2_status_exists — FAIL
- test_v2_tasks_approve_exists — FAIL (expects /api/v2/tasks/{task_id}/approve, not in routes)
Root cause: routes moved/renamed in surgical refactor, tests use old paths

### Category 4: Structural cleanup tests (2 tests)
Affected: tests/test_stabilization_final.py
- TestTelegramRemoved::test_no_self_improve_dir — FAIL (empty dir exists)
- TestDocumentation::test_no_report_files_at_root — FAIL (3 .md files at root)
Root cause: incomplete cleanup (empty dir) and docs placement policy

### Category 5: Import changes (3 tests)
Affected: tests/test_uncensored.py (3 tests)
Error: AttributeError: module api.main has no attribute _uncensored_state
Root cause: _uncensored_state moved to api/routes/system.py, tests not updated

### Category 6: Runtime behavior (remaining ~19 tests)
Affected: test_agent_specialization, test_architecture_coherence,
          test_capability_intelligence, test_convergence, test_e2e_convergence,
          test_integration_deep, test_multi_mission_intelligence,
          test_operating_assistant, test_orchestration_convergence,
          test_stabilization, test_tools
Root cause: Mix of behavior assertions that changed with refactor

---

## COUVERTURE PAR COMPOSANT

| Component | Test Coverage | Evidence |
|-----------|--------------|----------|
| Startup / boot | YES | test_v3_architecture, test_stabilization pass |
| Telegram removal | YES — full | 4 dedicated tests, all pass |
| API routes (v2/health, v2/status) | PARTIAL | health/status reachable, some route paths stale |
| MetaOrchestrator | PARTIAL | import OK, orchestration behavior tests partial |
| SupervisedExecutor | PARTIAL | import OK, async execution tests fail (infra issue) |
| core/self_improvement (canonical) | PARTIAL | module exists, engine.py missing, internal imports broken |
| self_improve/ removal | PARTIAL | telegram tests pass, self_improve dir test FAIL |
| scheduler | NONE | module missing, all 7 tests fail |
| Circuit breaker | NONE (infra) | async decorator missing |
| n8n bridge | PARTIAL | file modified, not specifically tested |

---

## GAPS IDENTIFIES

1. **No test validates core/self_improvement internal imports** — the 4 broken files (improvement_planner, deployment_gate, patch_builder, validation_runner) have no dedicated import test.

2. **engine.py missing, no test catches it** — SelfImprovementEngine import failure is only detectable via direct docker exec (not in pytest suite).

3. **scheduler module removed, 7 tests orphaned** — either restore scheduler/ or mark tests as xfail/skip.

4. **Async test infra missing asyncio_mode=auto** — 26 tests that test async behavior effectively never run. Fix: add asyncio_mode = auto to pytest.ini.

5. **TestAPICoherence has stale route paths** — 4 tests reference old route names that were renamed in refactor. Either update routes or update tests.

6. **No integration test for api/routes/missions.py (890 lines)** — the largest new file has no dedicated test file.
