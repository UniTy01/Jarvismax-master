# FINAL_ARCHITECTURE_STATE.md
> JarvisMax — État architectural final
> Branch: feat/surgical-cleanup
> Date: 2026-03-26

---

## Orchestration

**Seul entry point : `core/meta_orchestrator.py::get_meta_orchestrator()`**

Tous les chemins d'exécution passent par MetaOrchestrator :
- `api/routes/missions.py::submit_task` → `_get_orchestrator()` → `get_meta_orchestrator()`
- `main.py` → `get_meta_orchestrator()`
- `core/background_dispatcher.py` → `get_meta_orchestrator()`
- `core/agent_loop.py` → `get_meta_orchestrator()`
- `core/orchestration_bridge.py` → `get_meta_orchestrator()`

`JarvisOrchestrator` et `OrchestratorV2` ne sont instanciés que *à l'intérieur* de MetaOrchestrator
comme implémentations déléguées. Aucun code externe ne les instancie directement.

---

## API

### Structure post-refactor

```
api/
├── _deps.py                 # Shared: _check_auth, getters, _extract_final_output
├── main.py                  # 412 lignes: setup, CORS, includes, auth, websocket
└── routes/
    ├── missions.py          # POST/GET/DELETE /api/v2/task*, /missions*, /agents*
    ├── system.py            # GET/POST /api/v2/health, /status, /metrics, /logs, /mode*
    ├── memory.py            # GET /api/v2/decision-memory/*, /knowledge/*, /plan/*
    ├── tools.py             # GET/POST /api/v2/tools/*
    ├── admin.py             # GET/POST /api/v2/self-improvement/*, /self-improve/*
    ├── mission_control.py   # Mission SSE/stream
    ├── monitoring.py        # /api/v2/system/health, /metrics, /debug
    ├── performance.py       # Performance intelligence
    ├── self_improvement.py  # /api/v2/self-improvement/status,report,run (existing)
    ├── learning.py          # Learning endpoints
    ├── multimodal.py        # /api/v2/multimodal/*
    ├── rag.py               # RAG endpoints
    ├── agent_builder.py     # Agent builder
    ├── browser.py           # Browser automation
    ├── voice.py             # Voice endpoints
    ├── objectives.py        # Objective engine
    ├── dashboard.py         # Dashboard
    ├── approval.py          # Approval flow
    ├── convergence.py       # Orchestration bridge
    └── cockpit.py           # Cockpit UI
```

### Authentification

Toutes les routes protégées acceptent `X-Jarvis-Token` header.
Token défini par `JARVIS_API_TOKEN` env var.
Implémenté dans `api/_deps.py::_check_auth()`.

---

## Approbation (Approval Flow)

```
Mission soumise → RiskEngine.evaluate()
  └── LOW     → AUTO exécuté
  └── MEDIUM  → PENDING_VALIDATION
               → POST /api/v2/tasks/{id}/approve  (Flutter/API client)
               → ou auto-approved si dry_run=True
  └── HIGH    → PENDING_VALIDATION (obligatoire)
               → POST /api/v2/tasks/{id}/approve  (Flutter/API client)
               → backup automatique avant exécution
```

**Telegram supprimé.** L'approbation passe exclusivement par l'API REST.

---

## Self-Improvement

**Seul module canonique : `core/self_improvement/`**

```
core/self_improvement/
├── __init__.py              # get_self_improvement_manager()
├── candidate_generator.py
├── deployment_gate.py
├── failure_collector.py
├── improvement_memory.py
├── improvement_planner.py
├── improvement_scorer.py
├── legacy_adapter.py
├── patch_builder.py
├── protected_paths.py       # Fichiers protégés (MetaOrchestrator, etc.)
├── safe_executor.py
├── validation_runner.py
└── weakness_detector.py
```

Modules supprimés : `self_improve/` (legacy v1), `self_improvement/` (intermediate)

---

## Mémoire

Deux modules canoniques :

| Module | Rôle |
|--------|------|
| `memory/knowledge_memory.py` | Solutions, patterns, réutilisation |
| `memory/decision_memory.py` | Décisions, outcomes, apprentissage |

Modules legacy (toujours présents, dépréciés) :
- `memory/store.py` — utilisé par JarvisOrchestrator (deprecated)
- `memory/vector_memory.py` — Qdrant (feature-flagged)
- `memory/vault_memory.py` — utilisé par action_executor, coherence_checker

---

## Feature Flags

| Flag | Default | Comportement |
|------|---------|--------------|
| `USE_LANGGRAPH` | `false` | Post-processing LangGraph |
| `USE_KNOWLEDGE` | `false` | Knowledge memory injection |
| `USE_SELF_IMPROVE` | `false` | Self-improvement loop |
| `USE_TOOL_INTELLIGENCE` | `false` | Tool affinity scoring |

Tous default `false`. Le système fonctionne sans aucun flag.

---

## Variables d'environnement requises

| Variable | Obligatoire | Description |
|----------|------------|-------------|
| `JARVIS_ROOT` | ✅ | Chemin racine |
| `OPENAI_API_KEY` | ✅ (ou Ollama) | LLM principal |
| `JARVIS_API_TOKEN` | ✅ (prod) | Auth API |
| `ANTHROPIC_API_KEY` | ⚪ | LLM alternatif |
| `QDRANT_URL` | ⚪ | Vector search |
| `REDIS_URL` | ⚪ | Cache |
| `GITHUB_TOKEN` | ⚪ | Git ops |
| `CORS_ORIGINS` | ⚪ | CORS (défaut: localhost) |

**Supprimés :** `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ALLOWED_USER_ID`, `TELEGRAM_CHAT_ID`

---

## Tests

| Suite | Fichiers | Statut |
|-------|---------|--------|
| `tests/test_integration_stability.py` | 18 tests | ✅ PASS (Phase 8) |
| `tests/test_beta_architecture.py` | ~25 tests | ✅ PASS |
| `tests/test_stabilization_final.py` | ~20 tests | ✅ PASS |
| `tests/test_hardening_safety.py` | ~15 tests | ✅ PASS |
| `tests/validate.py` | legacy | ⚠️ sections bot skippées (jarvis_bot supprimé) |

CI cible : `test_beta_architecture.py test_stabilization_final.py test_hardening_safety.py test_status_memory_consolidation.py`
