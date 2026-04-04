# JARVIS MAX — Engineering Hardening Report
**Date:** 2026-03-31
**Scope:** 12-phase principal-architect directive
**Engineer:** Claude (autonomous pass)

---

## Executive Summary

JarvisMax is a real, functional multi-agent AI platform. The orchestration core, security layer, self-improvement pipeline, and test suite are all substantive and coherent. The codebase is not vapor — it runs.

The platform was, however, suffering from several compounding problems that made it fragile in CI, misleading in documentation, and unsafe at the edges: the deploy pipeline never fired on any push (wrong branch), K1 architecture enforcement was breaking on its own valid code (scanner bug), v3 API silently fell back to legacy routing by default, and test infrastructure was contaminating itself with mock isolation failures.

All four of those bugs are now fixed. The repo is meaningfully more production-ready than it was 48 hours ago. It is still an **internal alpha** that requires a full Docker stack (Qdrant, Redis, Postgres) for any real workload. That is now clearly stated in the README.

---

## Changes by Phase

### Phase 1 — Ground Truth Reconstruction
**README.md — corrected claims**

| Before | After |
|--------|-------|
| Vague "hundreds of tests" | `227 test files, ~6 100 tests` |
| Listed `/api/v2/tasks/{id}/approve` | Removed — endpoint does not exist |
| No Docker requirement stated | Added maturity note: Docker required for all features |
| Default branch ambiguity | Confirmed: default branch is `main` |

### Phase 2 — Truthfulness
- Added "internal alpha" maturity note to README
- Accurately reflects that business autonomy is human-gated
- `_use_canonical()` in `convergence.py` now defaults to `True` — v3 routes actually use the canonical orchestrator bridge instead of falling back to legacy silently

### Phase 3 — Repo Hygiene
- **106+ historical audit/report docs archived** from `docs/` → `docs/archive/`
- `docs/` reduced from 156 files to ~30 live reference documents
- `pytest-cache-files-*/` added to `.gitignore` (stale cache dirs were committed)
- `pytest-cache-files-av4180pw/` removed from git tracking

### Phase 4 — Runtime Path + Executor + Capability Routing

**`api/routes/convergence.py`** — `_use_canonical()` defaulted to `False`, meaning every v3 API call was silently routed to legacy `MissionSystem` instead of `MetaOrchestrator`. Fixed: default is now `True`, opt-out via `JARVIS_USE_CANONICAL_ORCHESTRATOR=0`.

**`api/routes/missions.py`** — Bare `except Exception: pass` in mission completion recovery block silently swallowed errors. Fixed: now logs `mission_completion_failed` with error details.

**`core/capability_routing/scorer.py`** — Audit: deterministic, weighted multi-dimension scoring (readiness 25%, reliability 30%, confidence 15%, risk 10%, cost 5%, latency 5%, type_preference 10%). Hard-block gates for status/risk/reliability thresholds. Assessment: **solid, no changes needed**.

### Phase 5 — Self-Improvement Safety

Audit of the full SI pipeline:

- `core/self_improvement/protected_paths.py` — 3-tier protection (exact file matches + directory prefixes + substring patterns). The self-improvement loop cannot touch auth, security, kernel contracts, or its own protection files. **Solid.**
- `core/self_improvement/safety_boundary.py` — Staging → syntax validation → backup → promote pipeline with rollback. Max file size 50KB. **Solid.**
- `core/self_improvement/human_gate.py` — Slack/Telegram notification for REVIEW decisions. Log-only fallback when no channel configured. **Solid.**
- `core/self_improvement/improvement_loop.py` — ExperimentResult, CriticReview (checks for benchmark gaming, policy bypass risk, executor safety regression), AdoptionDecision. Structured and auditable. **Solid.**

**One gap noted (not fixed — warrants separate PR):** `safety_boundary.is_path_allowed()` uses a smaller allowlist than `protected_paths.is_protected()`. The promotion pipeline should call `is_protected()` first, then verify `is_path_allowed()`. Currently both exist independently and may diverge.

### Phase 6 — Business Layer

Audit of `business/layer.py` and subdirectories:

- Correctly labeled: "Ne remplace PAS le Core Orchestrator — s'y branche comme une extension"
- R9 annotation present: "business layer never bypasses kernel.policy()"
- Finance module gated through `security.layer` before execution
- Intent routing is keyword-based (deterministic), not LLM-hallucinated
- **Assessment: appropriately scoped as "assisted orchestration". No fantasy automation claims. No changes needed.**

### Phase 7 — Security

Audit of `security/`, `api/auth.py`, `api/_deps.py`:

- `SecurityLayer`: PolicyRuleSet + RiskProfileRegistry + AuditTrail (append-only). All sensitive actions go through it. R3/R10 enforced.
- `api/auth.py`: Uses `hmac.compare_digest` for constant-time password comparison (no timing side-channel). JARVIS_ADMIN_PASSWORD preferred, JARVIS_SECRET_KEY fallback with explicit warning.
- Protected path check is comprehensive: auth dirs, security dirs, .env, docker-compose, self-improvement pipeline files all locked.

**One gap noted:** When `JARVIS_ADMIN_PASSWORD` is not set, the system falls back to `JARVIS_SECRET_KEY` as the admin password. In a production deployment this means the JWT signing secret doubles as the admin password — a credential reuse risk. Recommend setting `JARVIS_ADMIN_PASSWORD` explicitly and disabling the fallback in non-dev environments.

### Phase 8 — Testing

**Coverage by area:**

| Area | Files | Assessment |
|------|-------|------------|
| Architecture / integration | 5 | Strong — 31/31 R1-R10 checks pass |
| Self-improvement | 3 | Solid safety loop coverage |
| Auth / RBAC | 3 | Covers denial, session, role enforcement |
| Business / finance | 2 | Happy path coverage |
| Cognitive / security | 4 | Guards and intelligence layer |
| MCP / critical wiring | 2 | Runtime enforcement |

**Known weakness:** Tests that call `build_plan()` or initialize memory facades hang ~16 seconds each when Qdrant is unreachable (4 retries × ~4s). These pass eventually but bloat CI time. In CI without a real Qdrant container these should either mock the vector store or use `@pytest.mark.skip` with a connectivity check.

**Fixed in this pass:**
- `tests/test_integration_kernel_security_business.py`: `def test(name, fn)` was being collected by pytest as a fixture test → renamed to `_run_test` + added proper pytest wrapper
- `conftest.py`: Pre-loads real modules before collection to prevent mock contamination across test files

### Phase 9 — CI/CD

**Critical bug fixed: deploy pipeline never triggered on any push.**

`.github/workflows/deploy.yml`:
```yaml
# Before (broken):
on:
  push:
    branches: [master]     ← default branch is 'main'
...
    if: github.ref == 'refs/heads/master'   ← never true

# After (fixed):
on:
  push:
    branches: [main]
...
    if: github.ref == 'refs/heads/main'
```

`.github/workflows/kernel_ci.yml` — K1 scanner was raising `AttributeError: 'Module' has no attribute 'col_offset'` because it checked `col_offset` on all AST nodes including the module root. Fixed by checking `isinstance(node, (ast.ImportFrom, ast.Import))` before accessing `col_offset`. All 6 CI steps now pass.

### Phase 10 — API Cleanup

57 route files. No BROKEN/TODO markers found in route files. Some `pass` statements in exception handlers are expected (silent fallback on optional features like observability hooks, capability expansion). The `pass` instances in `kernel.py` (lines 284–331) are inside import try/except stubs for optional dependencies — appropriate.

**Remaining technical debt** (not fixed, logged for next sprint):
- `api/routes/debug.py` — debug endpoints should require admin-only auth, not just the standard token
- WebSocket `/ws/stream` in `convergence.py` — no rate limiting or max connection limit

### Phase 11 — Observability

`core/observability/`: `event_envelope.py` + `trace_intelligence.py`. Present and functional but minimal. The `convergence.py` system status endpoint already aggregates from observability, mission system, capability expansion, and intelligence hooks. Adequate for alpha. Not a blocker.

### Phase 12 — Architecture Consolidation

Architecture is coherent. Three-layer model (kernel → core → api/agents) is enforced by K1 rule in CI. MetaOrchestrator is the single entry point. Business layer is properly subordinate. Security layer wraps (never replaces) kernel policy.

---

## Fixes Summary

| # | File | Type | Description |
|---|------|------|-------------|
| 1 | `README.md` | Truthfulness | Accurate file counts, removed ghost endpoints, maturity note |
| 2 | `api/routes/convergence.py` | Bug | `_use_canonical()` defaulted False → True |
| 3 | `api/routes/missions.py` | Reliability | Bare `except: pass` → logs completion failure |
| 4 | `.github/workflows/deploy.yml` | Critical | `branches: [master]` → `[main]`; deploy condition fixed |
| 5 | `.github/workflows/kernel_ci.yml` | Critical | K1 scanner AttributeError on ast.Module; lazy import false positives |
| 6 | `tests/test_integration_kernel_security_business.py` | Test infra | `def test(name,fn)` collected as fixture → renamed + wrapper added |
| 7 | `conftest.py` | Test infra | Created — pre-loads real modules before collection |
| 8 | `.gitignore` | Hygiene | Added `pytest-cache-files-*/` |
| 9 | `docs/` | Hygiene | 106+ historical docs archived to `docs/archive/` |

---

## Remaining Gaps (Next Sprint)

1. **`JARVIS_ADMIN_PASSWORD` enforcement** — Disable `JARVIS_SECRET_KEY` fallback when `JARVIS_PRODUCTION=true`. One-line guard in `api/auth.py`.

2. **`safety_boundary.py` ↔ `protected_paths.py` sync** — `is_path_allowed()` and `is_protected()` are maintained independently. The promotion pipeline should call `is_protected()` (the more comprehensive check) as the primary gate.

3. **Qdrant-dependent test isolation** — Add a `pytest.fixture` that mocks `QdrantClient` for unit tests. The 16-second hang on unreachable Qdrant is not a bug but it makes CI unpredictable.

4. **`/api/routes/debug.py` auth hardening** — Debug endpoints should require admin role, not just a valid token.

5. **WebSocket rate limiting** — `/ws/stream` has no max-connections guard. Low risk for alpha, medium risk for any public deployment.

6. **`CHANGELOG.md` update** — This engineering pass should be recorded as `[Pass 32] — 2026-03-31`.

---

## Production Readiness Judgment

**Verdict: INTERNAL ALPHA — NOT PRODUCTION READY**

The codebase is coherent, tested, and now deploys to CI correctly. However:

- Requires full Docker stack (Qdrant, Redis, Postgres, Ollama) — no graceful degradation without them
- Admin password fallback to JWT secret is a security risk in production
- WebSocket endpoints have no rate limiting
- Self-improvement allowed scope (`config/`, `workspace/`) vs protected scope has a potential gap
- No load testing, no SLOs, no circuit breaker telemetry export

**For a production-grade hardening pass**, the 5 remaining gaps above should be addressed and the Docker stack should have health-check probes and graceful startup ordering.

---

## The Next 10 Tasks (Ordered by Value/Risk)

1. Set `JARVIS_ADMIN_PASSWORD` in `.env.example` and add startup check that refuses to start in production without it
2. Sync `safety_boundary.is_path_allowed()` with `protected_paths.is_protected()` — single source of truth
3. Mock `QdrantClient` in `conftest.py` for unit tests (skip if `JARVIS_INTEGRATION=true`)
4. Add admin-role check to `api/routes/debug.py`
5. Add `max_connections` guard to WebSocket route in `convergence.py`
6. Update `CHANGELOG.md` with this engineering pass
7. Add `JARVIS_PRODUCTION` env var guard that hard-fails on missing required secrets
8. Create `docs/GAPS.md` that tracks the remaining gaps with owner + ETA
9. Add `@pytest.mark.integration` marker to qdrant-dependent tests; CI runs unit tests only by default
10. Wire `kernel_ci.yml` to also run `deploy.yml` test jobs on PR to master/main (dry-run gate)

---

*Generated by autonomous engineering pass — 2026-03-31*
