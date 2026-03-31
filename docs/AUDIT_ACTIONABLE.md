# AUDIT_ACTIONABLE.md — Architecture Reality Map

> Updated: 2026-03-26 (Deep Stabilization)

## Canonical Paths

| Layer | Canonical Module | Notes |
|-------|-----------------|-------|
| Entrypoint | `main.py` | Docker CMD, launches FastAPI + optional Telegram |
| API | `api/main.py` (FastAPI, port 8000) | 53+ routes, all routers mounted once |
| Orchestration | `core/meta_orchestrator.py` → MetaOrchestrator | Delegates to JarvisOrchestrator/V2 internally |
| Execution | `core/tool_executor.py` | Shell-hardened, shlex.split default |
| Memory | `core/memory_facade.py` → backends in `memory/` | Facade pattern, clean separation |
| Self-Improvement | `core/self_improvement_engine.py` (V2) for new dev | V0 in bot, V1 in API failure analysis |
| Status Enum | `core/state.py` → `MissionStatus` | Single source, re-exported everywhere |
| App Interface | `jarvismax_app/` → connects to port 8000 | All profiles use canonical port |

## Active Legacy (kept for backward compat)

| Component | Used By | Future |
|-----------|---------|--------|
| `core/orchestrator.py` (JarvisOrchestrator) | MetaOrchestrator delegate | Deprecate when MetaOrchestrator proven |
| `core/orchestrator_v2.py` (OrchestratorV2) | MetaOrchestrator delegate | Deprecate with V1 |
| `self_improve/` (V0 engine) | bot.py, orchestrator.py | Replace with V2 when bot migrates |
| `self_improvement/` (V1 controller) | api/main.py failure analysis | Merge into V2 |
| `jarvis_bot/` (Telegram) | Optional, Docker profile | May remove entirely |
| `night_worker/` | orchestrator.py | Keep if night jobs needed |

## Deleted (this stabilization)

| Item | Reason |
|------|--------|
| `api/control_api.py` (627 lines) | Zero importers after start_api.py deprecated |
| `scheduler/` | Zero imports |
| `experiments/` | Zero production imports |
| `archive/` | Legacy scripts, no dependencies |
| `workspace/*.py` (tracked) | Runtime artifacts, gitignored |

## Remaining Technical Debt

1. **Bot token in git history** — MUST ROTATE via @BotFather
2. **4 self-improvement systems** — should converge to V2
3. **core/orchestrator.py (1053 lines)** — deprecated but still delegate
4. **`business/` (23 files)** — 6 agents imported but may overlap with core
5. **`start_api.py`** — deprecated shim, remove in next release
6. **`jarvis.py`** — experimental CLI, consider removing
