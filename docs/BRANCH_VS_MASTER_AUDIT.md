# BRANCH VS MASTER AUDIT — feat/surgical-cleanup
**Date**: 2026-03-26
**Scope**: full factual comparison — what improved, what is partial, what is missing, what blocks merge

---

## CE QUI EST MIEUX QUE MASTER

### 1. api/main.py refactored (CONFIRMED)
- Master: ~1800 lines monolithic
- Branch: 411 lines, routes split into api/routes/
- Evidence: wc -l /opt/Jarvismax/api/main.py = 411
- New routers: admin.py (117), memory.py (83), missions.py (890), system.py (177), tools.py (73)
- Dependency injection centralized in api/_deps.py (81 lines)

### 2. Telegram completely removed (CONFIRMED)
- 0 occurrences in requirements, runtime code, env files, docker-compose
- jarvis_bot/ directory: NOT PRESENT
- docker-compose.yml: -1 line (Telegram env var removed)
- Verified via 7 independent grep checks (see PRE_MERGE_PROOF.md section 2)

### 3. self_improve/ legacy module removed (PARTIAL — see blockers)
- Old self_improve/ directory: exists but EMPTY
- core/self_improvement/ canonical module: 13 files present
- Anti-loop guards documented in core/self_improvement/__init__.py:
  MAX_IMPROVEMENTS_PER_RUN=1, COOLDOWN_HOURS=24, MAX_CONSECUTIVE_FAILURES=3

### 4. API split into versioned routers (CONFIRMED)
- 198 routes registered across versioned namespaces (v1, v2, v3)
- Routes visible at /docs endpoint
- GET /api/v2/health returns JSON with 6 component statuses

### 5. n8n bridge cleaned (CONFIRMED)
- tools/n8n/bridge.py: -37 lines removed
- Simplified integration surface

### 6. MetaOrchestrator as canonical entry point (CONFIRMED)
- from core.meta_orchestrator import get_meta_orchestrator — imports OK
- OrchestratorV2 (thin wrapper) → JarvisOrchestrator delegation chain intact

---

## CE QUI EST PARTIELLEMENT AMELIORE

### 1. self_improve/ removal
- Expected: directory deleted
- Actual: directory EXISTS but is empty (os.path.isdir(self_improve) == True)
- Fix: rmdir self_improve/
- Impact: test_no_self_improve_dir FAILS

### 2. core/self_improvement internal imports
- 4 files use wrong import path:
  - improvement_planner.py:17 — from self_improvement.failure_collector import FailureEntry
  - deployment_gate.py:11 — from self_improvement.patch_builder import PatchCandidate
  - patch_builder.py:14 — from self_improvement.improvement_planner import ImprovementProposal
  - validation_runner.py:247,253 — from self_improvement.improvement_planner / failure_collector
- Correct path should be: from core.self_improvement.X or relative imports
- Impact: self_improvement subsystem partially broken at runtime

### 3. Documentation at root
- 3 new .md files placed at root: FINAL_ARCHITECTURE_STATE.md, FINAL_REPO_AUDIT.md, SURGICAL_CHANGES.md
- Test expects only README.md, ARCHITECTURE.md, CHANGELOG.md at root
- Fix: move to docs/ directory
- Impact: test_no_report_files_at_root FAILS

### 4. API route coherence with existing tests
- test_v2_tasks_approve_exists expects /api/v2/tasks/{task_id}/approve — NOT in routes
- test_v1_stream_route_exists, test_v2_missions_submit_exists, test_v2_status_exists — FAIL
- Routes were moved/renamed in refactor but tests not updated
- Impact: 4 TestAPICoherence tests FAIL

---

## CE QUI N EST PAS ENCORE RESOLU

### 1. engine.py missing in core/self_improvement/
- from core.self_improvement.engine import SelfImprovementEngine — ModuleNotFoundError
- engine.py does not exist in core/self_improvement/
- The old self_improve/engine.py was deleted but no equivalent created in the new location
- Impact: SelfImprovementEngine cannot be instantiated from canonical path

### 2. scheduler module removed without replacement
- test_scheduler.py (7 tests): ModuleNotFoundError: No module named scheduler
- scheduler/night_scheduler.py does not exist
- Impact: scheduled task functionality has no runtime module

### 3. LLMFactory.get_llm missing
- /api/v2/health: llm status=degraded — LLMFactory object has no attribute get_llm
- Pre-existing issue but not fixed in this branch
- Impact: LLM calls may be degraded

### 4. Async test infrastructure
- 26 tests fail with: Failed: async def function without pytest-asyncio decorator
- Affects: test_circuit_breaker.py (5), test_circuit_breaker_edge.py (4), test_execution_guard.py (6), test_validator.py (4), test_observability_helpers.py (4), others
- pytest.ini or conftest.py does not have asyncio_mode=auto
- Impact: these tests never run properly regardless of branch

---

## CE QUI DEVRAIT BLOQUER LE MERGE

| Issue | Severity | Reason |
|-------|----------|--------|
| self_improve/ empty dir exists | MUST FIX | test_no_self_improve_dir fails — cleanup incomplete |
| engine.py missing in core/self_improvement/ | MUST FIX | SelfImprovementEngine import broken at runtime |
| Broken internal imports in 4 self_improvement files | MUST FIX | self_improvement subsystem partially non-functional |
| FINAL_*.md files at root | SHOULD FIX | violates docs policy, failing test |
| scheduler module missing | EVALUATE | determine if scheduler is needed in production |

### NOT blocking
- LLMFactory degraded: pre-existing, not regressed
- Async test infrastructure: pre-existing test infra issue
- tests/validate.py legacy imports: test-only, try/except wrapped
- _uncensored_state in api.main: moved to routes, test update needed
