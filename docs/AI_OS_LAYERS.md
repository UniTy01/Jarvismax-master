# JarvisMax AI-OS Architecture Layers

## Status: v1 FROZEN — incremental evolution only

This document maps the AI-OS layer architecture to existing modules.
No redesign — just visibility into what exists and where it's going.

---

## Layer Map

### 1. LLM Layer (model routing + inference)
**Status: ✅ STABLE**

| Module | Purpose |
|---|---|
| `core/llm_factory.py` | Provider selection, fallback chains, circuit breaker |
| `core/model_router.py` | Cost-aware tier routing (FAST/STANDARD/STRONG) |
| `config/settings.py` | Role-based model env vars |

Current strategy: OpenRouter primary (Sonnet 4.5 + GPT-4o-mini), Ollama fallback.

### 2. Tool Layer (capabilities + execution)
**Status: ✅ STABLE**

| Module | Purpose |
|---|---|
| `core/tool_executor.py` | Central execution with policy + circuit breaker |
| `core/tools/tool_template.py` | BaseTool ABC (safe_execute, capability_schema) |
| `core/tools/generators.py` | Markdown, HTML, JSON Schema, HTTP test |
| `core/tools/email_tool.py` | SMTP send with rate limiting |
| `core/tools/http_tool.py` | External API calls with SSRF protection |
| `core/tools/file_tool.py` | Sandboxed file read/write |
| `core/capabilities/registry.py` | 16 registered capabilities with risk levels |
| `core/capabilities/schema.py` | Capability dataclass |

### 3. Memory Layer (knowledge + persistence)
**Status: ✅ STABLE**

| Module | Purpose |
|---|---|
| `core/memory_facade.py` | Unified memory interface |
| `core/memory/memory_schema.py` | 3-tier schema (SHORT_TERM/EPISODIC/LONG_TERM) |
| `core/skills/` | Procedural memory (JSONL storage, cosine retrieval) |

### 4. Execution Layer (orchestration + planning)
**Status: ✅ STABLE**

| Module | Purpose |
|---|---|
| `core/meta_orchestrator.py` | 12-phase pipeline (singleton) |
| `core/planner.py` | Plan generation with knowledge graph |
| `core/goal_decomposer.py` | Vague goal → structured task plan |
| `core/mission_system.py` | Mission lifecycle management |
| `core/state.py` | MissionStatus canonical states |
| `core/actions/action_model.py` | 7-state action lifecycle |
| `executor/contracts.py` | ExecutionResult contract |

### 5. Automation Layer (workflows + self-improvement)
**Status: ✅ STABLE**

| Module | Purpose |
|---|---|
| `core/workflow_runtime.py` | Multi-step workflow engine |
| `core/business_pipeline.py` | Business task automation |
| `core/self_improvement/improvement_loop.py` | Detect → propose → test → adopt |
| `core/self_improvement/goal_registry.py` | 8 measurable improvement goals |
| `core/self_improvement/benchmark_suite.py` | 8 evaluation scenarios |
| `core/self_improvement/protected_paths.py` | 12+ protected files |

### 6. Safety Layer (policy + resilience)
**Status: ✅ STABLE**

| Module | Purpose |
|---|---|
| `core/policy/policy_engine.py` | ROI scoring, budget limits, risk classification |
| `core/resilience.py` | JarvisError, CircuitBreaker, timeout_guard |
| `core/security/startup_guard.py` | Production token validation |
| `core/capabilities/registry.py` | Tool permission checks |

### 7. Observability Layer (tracing + events)
**Status: ✅ STABLE**

| Module | Purpose |
|---|---|
| `core/observability/event_envelope.py` | Structured events with trace_id |
| `core/trace.py` | Decision trace recording |
| `api/routes/trace.py` | GET /api/v1/trace/{trace_id} |

### 8. Integration Layer (API + external)
**Status: ✅ STABLE**

| Module | Purpose |
|---|---|
| `api/main.py` | FastAPI + 16 route files |
| `api/routes/mission_control.py` | Mission CRUD endpoints |
| Caddy reverse proxy | TLS termination (jarvis.jarvismaxapp.co.uk) |

### 9. UI Layer (Flutter app)
**Status: ✅ FUNCTIONAL**

| Module | Purpose |
|---|---|
| `jarvismax_app/` | Flutter Android app |
| `api_config.dart` | Production URL config |
| `websocket_service.dart` | WSS real-time updates |
| `api_service.dart` | JWT-authenticated REST client |

---

## Evolution Rules

1. **v1 is FROZEN** — no breaking changes to API_CONTRACT_V1.md
2. **Additive only** — new modules, not rewrites
3. **Test first** — every new module needs tests before merge
4. **Protected paths** — 12+ files cannot be auto-modified
5. **Stability > features** — always
