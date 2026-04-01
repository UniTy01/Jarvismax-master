# ARCHITECTURE_REALITY.md — Runtime Truth

> Updated: 2026-03-26 (Convergence Final)

## Canonical Runtime Flow

```
python main.py
  │
  ├── FastAPI (api/main.py, port 8000) ← PRIMARY
  │     ├── 15 routers (each mounted exactly once)
  │     ├── /api/v2/missions/submit → MetaOrchestrator.run()
  │     ├── /api/v2/tasks/{id}/approve|reject
  │     ├── /api/v2/status, /api/v2/agents, /api/v2/metrics
  │     ├── /api/v1/missions/{id}/stream (SSE for Flutter)
  │     ├── /api/v2/self-improve/run → V2 engine
  │     └── Static dashboard: /dashboard.html, /cockpit.html
  │
  └── Telegram bot (OPTIONAL, fail-open)
        └── jarvis_bot/bot.py
```

## Module Classification

### CANONICAL
| Module | Purpose |
|--------|---------|
| `main.py` | Single entrypoint (Docker CMD) |
| `api/main.py` | Single API (FastAPI, 53+ routes) |
| `core/meta_orchestrator.py` | Single orchestration entry point |
| `core/state.py` | Single MissionStatus definition |
| `core/tool_executor.py` | Canonical execution engine |
| `core/memory_facade.py` | Memory access facade |
| `core/self_improvement_engine.py` | V2 self-improvement (for new dev) |
| `core/canonical_types.py` | Canonical status types |
| `config/settings.py` | Configuration |

### ACTIVE LEGACY (delegate/compat)
| Module | Used By | Role |
|--------|---------|------|
| `core/orchestrator.py` | MetaOrchestrator | V1 delegate |
| `core/orchestrator_v2.py` | MetaOrchestrator | Budget/DAG delegate |
| `self_improve/` (15 files) | bot.py, orchestrator | V0 engine |
| `self_improvement/` (6 files) | api/main.py | V1 failure analysis |
| `executor/` | agent_loop, orchestrator | Desktop env + runner |
| `jarvis_bot/` | main.py (optional) | Telegram interface |
| `night_worker/` | orchestrator | Background jobs |

### ACTIVE SUPPORT
| Module | Purpose |
|--------|---------|
| `memory/` (13 files) | Backend stores (vault, decision, vector, etc.) |
| `agents/` (31 files) | Agent implementations + registry |
| `business/` (23 files) | Business agents (venture, offer, trade, etc.) |
| `modules/` (7 files) | Multimodal + voice |
| `monitoring/` (2 files) | Metrics |
| `observer/` (2 files) | System watcher |
| `observability/` (2 files) | Langfuse tracing |
| `risk/` (2 files) | Risk engine |
| `learning/` (6 files) | Knowledge engine |
| `workflow/` (2 files) | Workflow engine |
| `adapters/` (3 files) | OpenHands client |
| `tools/` (7 files) | Browser, n8n bridge |

### DEPRECATED (shims only)
| Module | Status |
|--------|--------|
| `start_api.py` | Prints warning, delegates to main.py |
| `jarvis.py` | Marked EXPERIMENTAL, CLI runner |

### DELETED
`api/control_api.py`, `scheduler/`, `experiments/`, `archive/`,
`send_telegram.py`, `send_telegram_v5.py`

## Identified Inconsistencies — RESOLVED
- ~~Split-brain API (control_api vs api/main)~~ → control_api deleted
- ~~Duplicate router mounts~~ → removed duplicates
- ~~Flutter port 7070~~ → all profiles use 8000
- ~~Missing SSE stream route~~ → alias added
- ~~Broken executor imports~~ → lazy imports + files restored
- ~~Dead tests importing ControlAPI~~ → test blocs removed
