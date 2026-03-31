# REPO_STRUCTURE_AFTER.md

> Final repository structure after stabilization

```
Jarvismax/
├── main.py                    # CANONICAL entrypoint (Docker CMD)
├── start_api.py               # DEPRECATED (delegates to main.py)
├── jarvis.py                  # EXPERIMENTAL (CLI runner)
├── LICENSE                    # MIT
├── README.md                  # App-first documentation
├── ARCHITECTURE.md            # Runtime architecture
├── CHANGELOG.md               # Release history
├── requirements.txt           # Python deps (includes pytest)
├── docker-compose.yml         # Stack (jarvis_bot profile-gated)
├── .github/workflows/         # CI: test + deploy
│
├── api/                       # CANONICAL API
│   ├── main.py               # FastAPI app (1800 lines, 53+ routes)
│   ├── routes/               # 15 routers (each mounted once)
│   ├── ws.py, ws_hub.py      # WebSocket support
│   ├── stream_router.py      # SSE streaming
│   └── auth.py, models.py    # Auth + schemas
│
├── core/                      # Core engine (137 files)
│   ├── meta_orchestrator.py  # CANONICAL orchestrator
│   ├── state.py              # CANONICAL MissionStatus
│   ├── tool_executor.py      # CANONICAL executor
│   ├── memory_facade.py      # Memory access facade
│   ├── self_improvement_engine.py  # V2 self-improvement
│   ├── orchestrator.py       # Legacy delegate (V1)
│   ├── orchestrator_v2.py    # Legacy delegate (budget/DAG)
│   └── ...                   # Planning, governance, connectors, etc.
│
├── memory/                    # Backend stores (13 files)
├── agents/                    # Agent implementations (31 files)
├── executor/                  # Desktop env + runner (15 files)
├── self_improve/              # V0 engine (legacy, bot compat)
├── self_improvement/          # V1 controller (legacy, API compat)
├── business/                  # Business agents (23 files)
├── modules/                   # Multimodal + voice (7 files)
├── tools/                     # Browser, n8n bridge (7 files)
├── risk/                      # Risk engine (2 files)
├── monitoring/                # Metrics (2 files)
├── observer/                  # System watcher (2 files)
├── observability/             # Langfuse tracer (2 files)
├── learning/                  # Knowledge engine (6 files)
├── workflow/                  # Workflow engine (2 files)
├── adapters/                  # OpenHands client (3 files)
├── night_worker/              # Background jobs (3 files)
├── config/                    # Settings (2 files)
│
├── jarvis_bot/                # LEGACY Telegram (optional)
├── jarvismax_app/             # Flutter app (primary interface)
├── static/                    # Dashboard HTML (2 files)
├── docker/                    # Dockerfile
├── scripts/                   # Install/update scripts
├── tests/                     # 90 test files
├── docs/                      # Active docs (13 files)
│   ├── archive/              # Historical docs (15 files)
│   └── ...
├── openclaw/                  # Agent SOUL configs
└── workspace/                 # Runtime artifacts (gitignored)
```

## Key Numbers
- **Active Python files**: ~350
- **Test files**: 90
- **Active docs**: 13
- **Archived docs**: 15
- **Git branches**: 12 (master + 11 feature)
