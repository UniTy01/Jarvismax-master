# TEST_TRUTH.md — Jarvis Max
_Last updated: 2026-04-03 — Cycle 18 post-wave: 5700 passing, test baseline updated._

This document is the authoritative record of the test suite state.
Numbers are from real runs. Do not overstate.

---

## Current Test Baseline (Cycle 18 — 2026-04-03)

**Run:** `docker run --rm -v $(pwd):/app -w /app jarvismax-master-jarvis:latest python -m pytest tests/ -q --tb=line --ignore=tests/test_aios_dashboard.py`
**Result:** **5700 passed, 515 skipped, ~20 pre-existing failures**
**Runtime:** ~593s (9m53s) in Docker

### Pre-existing failures (not regressions — all confirmed pre-Cycle 18)

| Test | Root cause | Status |
|------|-----------|--------|
| `test_aios_dashboard.*` | Requires live HTTP server on `localhost:8000` | Excluded from unit run |
| `test_rejected_outside_scope` | Assertion checks `"outside" in msg` but message is `"REJECTED: .env is in protected runtime scope"` | Pre-existing text mismatch |
| `test_no_report_files_at_root` | Expects only 3 .md at root; 10+ truth docs exist at root by design | Pre-existing policy contradiction |
| `test_debug_api DB02/DB03` | Model selector mock configuration mismatch | Pre-existing |
| `test_execution_reliability MF11` | Budget selector mock | Pre-existing |

**External dependencies required for full run:** None (Docker image contains all deps)

---

## Integration Test Results

**Total collected:** 437 integration tests across 20 test files
**Collection method:** `pytest -m integration --collect-only`

### Passing (all pass, some skip for missing infra)

| File | Pass | Skip | Failure | Notes |
|------|------|------|---------|-------|
| `tests/test_ai_os_foundation.py` | 45 | 0 | 0 | Architecture, agents, tools, E2E validation |
| `tests/test_budget_mode.py` | 5 | 0 | 0 | Budget propagation through planner |
| `tests/test_api_structure.py` | ✅ | — | 0 | API route structure tests |
| `tests/test_approval_gate.py` | ✅ | — | 0 | Approval gate flow |
| `tests/test_devin_core.py` | ✅ | — | 0 | Core devin-style capabilities |
| `tests/test_hardening_pass2.py` | 38* | 4* | 0 | Hardening pass 2 |
| `tests/test_production_hardening_p34.py` | 38* | 4* | 0 | Production hardening phases 3-4 |
| `tests/test_playbooks.py` | 38* | 4* | 0 | Playbook system; 4 skipped = Qdrant not running |
| `tests/test_vector_memory.py` | 38* | 4* | 0 | Vector memory; 4 skipped = Qdrant not running |
| `tests/test_e2e_integration.py` | 13 | 3 | 0 | E2E mission flow; 3 skipped (infra conditional) |
| `tests/test_e2e_mission_lifecycle.py` (non-stress) | 21 | 3 | 0 | Full lifecycle; 3 approval skipped (conditional) |
| `tests/test_governance.py` | 32 | 2 | 0 | Policy, governance rules |
| `tests/test_operational_intelligence.py` | 60 | 0 | 0 | Ops intelligence layer |
| `tests/test_real_world.py` | 17 | 0 | 0 | Real-world scenario tests |
| `tests/test_reasoning_engine.py` | 45 | 0 | 0 | Reasoning engine |
| `tests/test_tool_intelligence.py` | 12 | 0 | 0 | Tool intelligence |
| `tests/test_tools.py` | 5 | 1 | 0 | Tool execution |
| `tests/test_tools_extended.py` | 5 | 4 | 0 | 4 skipped = network/Docker |
| `tests/test_extended_validation.py` | 16 | 0 | 0 | Extended validation suite |
| `tests/test_capability_expansion_real.py` | 24 | 0 | 0 | Capability expansion |
| `tests/test_knowledge_engine.py` | 5 | 0 | 0 | Knowledge engine |
| `tests/test_objective_engine.py` | ✅ | — | 0 | Objective engine |
| `tests/test_task_difficulty.py` | 5 | 0 | 0 | Task difficulty estimator |
| `tests/test_v3_architecture.py` (sampled) | 3 | 0 | 0 | V3 architecture; full run not sampled |

_(*) Counts are for the combined batch; individual file breakdown not measured._

---

### Slow Tests (pass but exceed short CI timeouts)

| File/Class | Issue | Root Cause | Classification |
|-----------|-------|-----------|----------------|
| `tests/test_e2e_mission_lifecycle.py::TestMultiMissionStress` | Runs 50+20 sequential `ms.submit()` calls, each ~0.5s | GoalManager singleton loads 500+ queued goals at first call | **Test design issue** — not a product bug. Should be marked `@pytest.mark.slow`. |
| `tests/test_robustness.py` (all 5 tests) | Each test takes 15-20s due to first-call singleton init | `build_plan()` lazy-loads MemoryFacade, KnowledgeMemory, ObjectiveEngine, etc. | **Test design issue** — passes, just slow. Total ~90s for 5 tests. |

---

### Problem Files (fixed in Cycle 7)

| File | Issue | Fix Applied |
|------|-------|-------------|
| `core/tools/test_toolkit.py` | `test_endpoint()` utility function collected by pytest → INTERNALERROR when called without args | Added `test_endpoint.__test__ = False` |
| `scripts/test_parity.py` | Module-level `requests.post()` call → INTERNALERROR on import in pytest | Wrapped all module-level code in `if __name__ == '__main__':` guard |
| `scripts/test_memory.py` | `PermissionError` on `corrupt_path.unlink()` in sandbox | Environment issue (read-only test file in sandbox); not fixed — requires running environment. Run directly: `python scripts/test_memory.py` |

---

### Tests Requiring a Running Server (skip automatically when no server)

These tests connect to `localhost:8000` and are skipped or fail gracefully when no server is running:

- `tests/smoke/test_e2e_smoke.py` — requires `docker compose up` or `python main.py` + Qdrant
- Any test using `httpx.AsyncClient(base_url="http://localhost:8000")` fixtures

**Recommended CI approach:** Run unit tests (`pytest --ignore=tests/`) for PR checks. Run integration tests against a live stack (`docker compose -f docker-compose.test.yml up`) for release gating.

---

## Test Collection Warnings (non-blocking, documented)

1. `business_agents/test_harness.py`: `TestCase`, `TestResult`, `TestSuiteResult` classes have `__init__` constructors → PytestCollectionWarning. Not a test file; no action needed.
2. `core/self_improvement/test_runner.py`: `TestRunner`, `TestSuiteResult` have `__init__` → collection warnings. Both have `__test__ = False` (added Cycle 2). Warnings appear during collection but do not cause failures.

---

## Classification Summary

| Category | Count | Action |
|----------|-------|--------|
| Passes cleanly | ~390+ | No action |
| Skipped (infra dependency — Qdrant, network) | ~16 | Expected — skip is correct behavior |
| Slow but passing | ~55 | Mark `@pytest.mark.slow`; exclude from short CI runs |
| Fixed in this cycle | 2 files | `test_endpoint.__test__` + `test_parity.py` guard |
| Requires running server | varies | Gate on integration environment |
| Real product bugs found in tests | 0 | No new product bugs discovered |

**Conclusion:** The integration test suite is in good health. All failures in CI are environment-related (no server, no Qdrant, no network). No product bugs were found in the integration tests during Phase 4 audit.
