# INDEPENDENT_BRANCH_AUDIT.md

> Independent merge audit — 2026-03-26
> Scope: all stabilization work from 0130e38 to 761654d (12 merges)

## Branch vs Master Comparison

| Metric | Value |
|--------|-------|
| Commits | 12 merge commits |
| Files changed | 166 |
| Lines added | +2,113 |
| Lines deleted | -10,550 |
| Net | **-8,437 lines** |
| Files deleted | 72 |
| Files added | 22 |
| Files moved | 27 |

## Verified Improvements

### ✅ GOOD — Confirmed by direct code inspection

| Change | Evidence |
|--------|----------|
| Single entrypoint (main.py) | 120 lines, no Telegram, pure FastAPI |
| api/control_api.py deleted | Zero importers verified before deletion |
| Duplicate router mounts removed | monitoring_router + dashboard_router each mounted once |
| Flutter port 7070 → 8000 | All 3 profiles, settings, dashboard |
| SSE stream route alias | /api/v1/missions/{id}/stream added |
| Health check ports fixed | action_executor + handlers: 7070 → 8000 |
| Path casing normalized | /opt/Jarvismax → /opt/jarvismax (8 files) |
| CORS hardened | Wildcard * → explicit whitelist + env var |
| shell=True hardened | 5 sites in agents/ converted to shlex.split |
| Dead dirs deleted | scheduler/, experiments/, archive/ — zero imports confirmed |
| self_improve/ deleted | 15 files, 5979 lines — only bot used it |
| self_improvement/ merged | 5 files moved to core/self_improvement/ |
| Telegram removed from runtime | main.py, requirements, settings, Docker, README |
| Branch cleanup | 26 stale branches deleted |
| LICENSE added | MIT |
| Branch protection | master requires CI test job |

### ⚠️ FOUND AND FIXED DURING AUDIT

| Bug | Severity | Fix |
|-----|----------|-----|
| 5 broken imports in core/self_improvement/ | **CRITICAL** | `from self_improvement.` → `from core.self_improvement.` |
| telegram_card() methods in 7 production files | MEDIUM | Renamed to summary_card() |
| Stale Telegram comment in docker-compose.yml | LOW | Removed |
| Default deployment_mode "telegram" in trade_ops | LOW | Changed to "api" |

### Risky Areas

| Area | Risk | Mitigation |
|------|------|------------|
| core/orchestrator.py _run_improve redirect | MEDIUM | Changed from self_improve.engine to core.self_improvement_engine — verify at runtime |
| api/main.py still 1800 lines | LOW | Documented but not split — planned for dedicated refactor |
| Pre-existing test failure (TestDomainManager) | LOW | Confirmed pre-existing, not a regression |

### Incomplete Areas

| Area | Status |
|------|--------|
| api/main.py route extraction | Documented but not executed — too risky for stabilization pass |
| core/orchestrator.py deprecation | Documented, not started — MetaOrchestrator delegate still |
| business/ overlap with core | Not addressed — low priority |

## Classification Summary

| Change Category | Verdict |
|----------------|---------|
| Dead code deletion | GOOD |
| Security fixes (CORS, shell, tokens, IPs) | GOOD |
| Startup consolidation | GOOD |
| API consolidation | GOOD |
| Telegram removal | GOOD (after audit fix) |
| Self-improvement merge | GOOD (after audit fix) |
| Documentation | GOOD |
| Tests | GOOD (190+ new, 0 regressions) |
| Executor hardening | GOOD |
| Observability (trace.py) | GOOD |
