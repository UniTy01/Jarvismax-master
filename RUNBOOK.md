# RUNBOOK — Jarvis Max

**Last updated:** 2026-04-01
**Status:** Internal Alpha — E2E proven on canonical path (verify_boot.sh passes)

---

## 1. What This Project Actually Is

Jarvis Max is a Python-based AI agent orchestration framework. It exposes a REST API (FastAPI, port 8000) that accepts a natural-language "mission" goal, routes it through a MetaOrchestrator, calls an LLM provider (OpenAI, Anthropic, or OpenRouter), and returns a result. It includes a mission state machine (CREATED → PLANNED → RUNNING → REVIEW → DONE), a circuit breaker, a vector memory layer (Qdrant), and a background self-improvement daemon.

## 2. What It Is Not

- It is not a production-ready product.
- It is not an autonomous AI OS that operates without a human in the loop.
- The self-improvement loop has not been validated end-to-end with real LLM calls.
- The business layer (billing, plans, usage limits) is structural code only — no payment integration exists.
- Several subsystems (n8n, Ollama, Langfuse, Open WebUI) are optional components in the full stack, not part of the core runtime.

---

## 3. Minimum Requirements

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.10+ | 3.12 used in Docker image |
| Docker + Compose v2 | Any recent | For containerized startup |
| Qdrant | ≥ 1.7 | Vector store, required at runtime |
| LLM API key | — | At least one of: OpenAI, Anthropic, OpenRouter |

**Not required for dev:**
- Redis (sessions degrade gracefully)
- PostgreSQL (mission persistence falls back to in-memory)
- Ollama (only needed if MODEL_STRATEGY=ollama)
- n8n, Langfuse, Caddy, Open WebUI (optional services)

---

## 4. Dev Startup (Python direct) — PROVEN PATH

This is the exact sequence verified to produce a passing `verify_boot.sh` run.

### Path A — Anthropic (proven 2026-04-01, ~40s to COMPLETED)

```bash
# 1. Clone and install
git clone <repo> && cd Jarvismax-master
pip install -r requirements.txt
pip install langchain-anthropic   # required for Anthropic path

# 2. Copy and configure env
cp .env.example .env
# Edit .env — set at minimum:
#   ANTHROPIC_API_KEY=sk-ant-...
#   ANTHROPIC_MODEL=claude-haiku-4-5-20251001
#   MODEL_STRATEGY=anthropic
#   MODEL_FALLBACK=anthropic
#   JARVIS_SECRET_KEY=$(openssl rand -hex 32)
#   JARVIS_ADMIN_PASSWORD=<your admin password>
#   QDRANT_HOST=localhost

# 3. Start Qdrant
# Option A — Docker (simplest):
docker run -d --name qdrant -p 6333:6333 qdrant/qdrant:v1.9.7
# Option B — Native binary (no Docker required):
wget https://github.com/qdrant/qdrant/releases/download/v1.9.7/qdrant-x86_64-unknown-linux-musl.tar.gz
tar xzf qdrant-*.tar.gz && ./qdrant &

# 4. Start the API
python main.py

# 5. Run boot verification (must exit 0)
JARVIS_ADMIN_PASSWORD=<your admin password> bash scripts/verify_boot.sh
```

### Path B — OpenRouter (proven 2026-04-01, ~60s to COMPLETED)

```bash
pip install -r requirements.txt
pip install langchain-openai      # required for OpenRouter provider

# Edit .env:
#   OPENROUTER_API_KEY=sk-or-...
#   MODEL_STRATEGY=openrouter
#   MODEL_FALLBACK=anthropic      # optional: fallback if OpenRouter rejects
#   JARVIS_SECRET_KEY=$(openssl rand -hex 32)
#   JARVIS_ADMIN_PASSWORD=<your admin password>
#   QDRANT_HOST=localhost

./qdrant &
python main.py
JARVIS_ADMIN_PASSWORD=<your admin password> bash scripts/verify_boot.sh
```

The API is reachable at `http://localhost:8000`.
Expected verify_boot.sh output: `=== BOOT VERIFICATION PASSED ===`.

**Provider selection logic:**
All agent roles in `core/llm_factory.py` default to OpenRouter. Without `OPENROUTER_API_KEY`,
the factory falls through to `MODEL_FALLBACK`. Setting `MODEL_FALLBACK=anthropic` ensures
`langchain_anthropic.ChatAnthropic` is selected for all roles when only an Anthropic key is present.

**Invalid key behavior (proven):**
With an invalid API key and no valid fallback, missions correctly reach `FAILED` state in ~9s
with `failure_reason: all_agents_failed: 0/N agents produced output`. No ghost-DONE.

---

## 5. Docker Startup (Minimal — Recommended for First Test)

Use `docker-compose.test.yml` for the smallest possible stack (Qdrant + API only):

```bash
# Copy env template
cp .env.example .env
# Edit .env — set at minimum: OPENAI_API_KEY or ANTHROPIC_API_KEY

# Start minimal stack
docker compose -f docker-compose.test.yml up --build

# Verify readiness
curl http://localhost:8000/api/v3/system/readiness
```

**Full stack** (Postgres, Redis, Ollama, n8n, Caddy):
```bash
docker compose up -d
```
Note: The full stack requires all mandatory env vars in `.env` (see section 6).
First startup takes 3–5 minutes (Ollama health check + model warm-up).

---

## 6. Required Environment Variables

Minimum set for a passing `verify_boot.sh` run:

| Variable | Required | Proven default | Notes |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | One LLM key required | — | Proven path. Accepts `sk-ant-...` keys. |
| `ANTHROPIC_MODEL` | If using Anthropic | `claude-haiku-4-5-20251001` | Haiku is fast/cheap; use Sonnet for quality. |
| `MODEL_STRATEGY` | Yes | `anthropic` | `openai`/`anthropic`/`openrouter`/`ollama` |
| `MODEL_FALLBACK` | Yes | `anthropic` | Fallback when primary provider has no key. **Must be `anthropic` when using Anthropic path.** |
| `QDRANT_HOST` | Yes | `localhost` | Use service name (`qdrant`) inside Docker. |
| `QDRANT_PORT` | Yes | `6333` | Default Qdrant HTTP port. |
| `JARVIS_SECRET_KEY` | Yes | — | Hard-fail in production if default value. Generate: `openssl rand -hex 32` |
| `JARVIS_ADMIN_PASSWORD` | Yes | — | Used by `/auth/token` and `verify_boot.sh`. |

**Alternative LLM keys (use one or more):**
- `OPENROUTER_API_KEY` — preferred for production; routes to 200+ models via OpenAI-compatible API
- `OPENAI_API_KEY` — direct OpenAI access
- No key needed if `MODEL_STRATEGY=ollama` (local inference via Ollama)

**If running with `JARVIS_PRODUCTION=1`**, these additional vars are also enforced:
- `JARVIS_API_TOKEN` (min 32 chars)
- Postgres must be reachable (startup blocks if not)

---

## 7. Optional Environment Variables

| Variable | Default | Notes |
|---|---|---|
| `MODEL_STRATEGY` | `openai` | `openai` / `anthropic` / `openrouter` / `ollama` |
| `JARVIS_PRODUCTION` | unset | Set to `1` to enable hard-fail on insecure defaults |
| `JARVIS_REQUIRE_AUTH` | unset | Set to `1` to enforce API token on all endpoints |
| `JARVIS_API_TOKEN` | unset | Static bearer token for API auth |
| `DRY_RUN` | `false` | Set to `true` to disable LLM calls (returns stubs) |
| `JARVIS_SKIP_IMPROVEMENT_GATE` | unset | Set to `1` to skip self-improvement cooldown (tests) |
| `JARVIS_USE_CANONICAL_ORCHESTRATOR` | `1` | Set to `0` to force legacy MissionSystem routing |
| `QDRANT_PORT` | `6333` | Qdrant HTTP port |
| `QDRANT_API_KEY` | unset | Qdrant API key (recommended for production) |
| `POSTGRES_HOST` | `postgres` | `localhost` if running Postgres outside Docker |
| `REDIS_HOST` | `redis` | `localhost` if running Redis outside Docker |
| `OLLAMA_HOST` | `http://ollama:11434` | Ollama endpoint, if using local LLM |
| `LANGFUSE_ENABLED` | `false` | Set to `true` to enable LLM observability |
| `SELF_IMPROVE_ENABLED` | `true` | Background self-improvement daemon |
| `JARVIS_MODE` | `local` | `local` (2 agents max) or `vps` (5 agents max) |

---

## 8. Ports

| Port | Service | Bound to |
|---|---|---|
| `8000` | Jarvis Core API | `127.0.0.1:8000` (Docker), `0.0.0.0:8000` (dev) |
| `6333` | Qdrant (dev only) | `127.0.0.1:6333` (disabled in prod) |
| `5678` | n8n | `0.0.0.0:5678` |
| `3001` | Open WebUI | `0.0.0.0:3001` |
| `3002` | Langfuse | `0.0.0.0:3002` |
| `80/443` | Caddy (prod only) | public |

---

## 9. External Services Required

| Service | When Required | Why |
|---|---|---|
| Qdrant | Always (at runtime) | Vector memory — missions fail gracefully without it at startup, but memory operations fail |
| OpenAI / Anthropic / OpenRouter | Always | LLM calls — no key = no mission execution |
| PostgreSQL | Optional | Mission persistence. Falls back to in-memory on failure |
| Redis | Optional | Session state. Degrades gracefully |
| Ollama | Only if MODEL_STRATEGY=ollama | Local LLM inference |

---

## 10. Verify Readiness

```bash
# Basic health (import check only — always 200 if server is up)
curl http://localhost:8000/health

# Real readiness (checks LLM key, Qdrant TCP, MetaOrchestrator init)
curl http://localhost:8000/api/v3/system/readiness
```

**Expected response when ready (HTTP 200):**
```json
{
  "ok": true,
  "data": {
    "ready": true,
    "status": "ready",
    "probes": {
      "llm_key": true,
      "qdrant": true,
      "orchestrator": true
    }
  }
}
```

**HTTP 503 means one of the three probes failed.** Check the `probes` dict to identify which one.

---

## 11. Submit a Test Mission

```bash
# Minimal mission (no auth configured)
curl -X POST http://localhost:8000/api/v3/missions \
  -H "Content-Type: application/json" \
  -d '{"goal": "Write a one-sentence summary of the Pythagorean theorem."}'
```

**Expected response (HTTP 201):**
```json
{
  "ok": true,
  "data": {
    "mission_id": "m-abc123...",
    "status": "CREATED",
    "goal": "Write a one-sentence summary..."
  }
}
```

The mission is submitted asynchronously. Poll for status:
```bash
curl http://localhost:8000/api/v3/missions/{mission_id}
```

Wait for `status` to reach `DONE` or `FAILED`. The `result` field will contain the LLM output.

**With API token authentication:**
```bash
curl -X POST http://localhost:8000/api/v3/missions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-token-here" \
  -d '{"goal": "Explain Docker in one sentence."}'
```

---

## 12. Observe Progress

**Structured logs** (stdout, JSON-ish via structlog):
```bash
docker logs -f jarvis_core
```

Key log events to look for:
- `kernel_booted` — kernel runtime initialized
- `api_ready` — startup complete, accepting requests
- `mission_submitted` — mission accepted by orchestrator
- `mission_completed` / `mission_failed` — terminal state
- `circuit_breaker_opened` — 5 consecutive LLM failures, orchestrator suspended
- `improvement_daemon_started` — background SI loop running

**System status endpoint:**
```bash
curl http://localhost:8000/api/v3/system/status
```

**WebSocket event stream** (real-time):
```bash
# Requires a WS client
wscat -c ws://localhost:8000/ws/stream
```

---

## 13. Common Startup Failures

**"PRODUCTION STARTUP BLOCKED"**
→ `JARVIS_PRODUCTION=1` is set and at least one required secret is the default value.  
Fix: Set `JARVIS_SECRET_KEY`, `JARVIS_ADMIN_PASSWORD`, and `JARVIS_API_TOKEN` in `.env`.

**Readiness probe: `"llm_key": false`**
→ No LLM API key is configured.  
Fix: Set `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` or `OPENROUTER_API_KEY` in `.env`.

**Readiness probe: `"qdrant": false`**
→ TCP connection to `QDRANT_HOST:QDRANT_PORT` failed (default: `qdrant:6333`).  
Fix: Start Qdrant. In dev: `docker run -p 6333:6333 qdrant/qdrant`. Set `QDRANT_HOST=localhost`.

**Readiness probe: `"orchestrator": false`**
→ MetaOrchestrator failed to initialize. Check logs for the root error.

**`kernel_boot_skipped`** in logs
→ Non-fatal. The kernel extension layer failed to load. The core API and MetaOrchestrator still function.  
This typically happens when an optional dependency (sentence-transformers, Qdrant client) is unavailable.

**`vector_store_boot_skipped`** in logs
→ Qdrant is unreachable at startup. Missions will fail when they try to use memory. Start Qdrant.

**Container restarts with exit code 1**
→ Check `docker logs jarvis_core`. Most likely cause: missing mandatory env var, import error.

**`circuit_breaker_opened`** in logs
→ 5 consecutive mission failures. The orchestrator is suspended for 60 seconds.  
Root cause is almost always a bad or expired LLM API key.

---

## 14. What "Working" Means Right Now

A fully working state means:
1. `GET /api/v3/system/readiness` returns HTTP 200 with all three probes true.
2. `POST /api/v3/missions` with a real goal creates a mission and returns `mission_id`.
3. Polling the mission status eventually shows `DONE` (not `FAILED`).
4. The `result` field contains a real LLM-generated response.
5. The structured logs show `mission_completed` without errors.

---

## 15. What Is Still Not Production-Ready

**Persistence:**
- PostgreSQL connection failure is non-fatal in dev mode. Missions are in-memory and lost on restart.
- No production enforcement exists unless `JARVIS_PRODUCTION=1` is set. That env var is not currently wired to a persistence check — it only enforces secret validation at boot.
- Recommended: treat all missions as ephemeral until Postgres persistence is validated end-to-end.

**Terminal failure behavior:**
- With an invalid LLM key, agents hit `RuntimeError` from `LLMFactory.get()`, which propagates up but is caught as a generic exception in some paths. The mission may reach FAILED or may hang in RUNNING depending on which agent fails first.
- No explicit "LLM auth failure" terminal state exists — all LLM errors map to generic FAILED.
- `verify_boot.sh` does not yet distinguish LLM auth failure from infrastructure failure.

**Self-improvement loop:**
- The `ImprovementDaemon` has never generated and applied a real patch under observation. Architecturally correct but operationally unverified.
- `SELF_IMPROVE_ENABLED=true` is the default but this background process has not been tested with a real key.

**HumanGate / approval flow:**
- MEDIUM and HIGH risk missions trigger an approval gate. The notification mechanism (Slack/Telegram) requires tokens not in `.env.example`.
- The approve/reject API endpoints exist and are tested but the notification delivery path is unverified.

**Docker:**
- `docker-compose.test.yml` env propagation has not been run in this environment. Static alignment is done; live Docker test is pending.
- Full-stack `docker-compose.yml` references Caddy — the `Caddyfile` may not exist in the repo.

**Multi-agent parallelism:**
- `JARVIS_MODE=vps` enables 5 concurrent agents but has never been load-tested.

**Integration test suite:**
- The `@pytest.mark.integration` tests require Qdrant + a real LLM key. Classification of failures pending (Phase 4).

---

## E2E Proof — Real Runtime (VERIFIED 2026-04-01)

The following sequence was verified to exit 0 from `verify_boot.sh` in ~39 seconds:

```
Stack: Qdrant v1.9.7 (native binary) + FastAPI/uvicorn, port 8000
LLM:   claude-haiku-4-5-20251001 via langchain_anthropic.ChatAnthropic

GET  /health                              → 200 {"status":"ok","service":"jarvismax"}
GET  /api/v3/system/readiness             → 200 ready=true, all probes OK
POST /auth/token (admin/<password>)       → 200 JWT access_token
POST /api/v3/missions {"goal":"Return only the number 42."}
                                          → 201 mission_id
  BackgroundTask: mo.run_mission(goal, mission_id)
  MetaOrchestrator: CREATED → PLANNED → RUNNING
  Parallel agents: scout-research (done), forge-builder (done), lens-reviewer (failed/partial)
  Synthesizer → RUNNING → REVIEW → DONE → canonical status: COMPLETED
GET  /api/v3/missions/{id}                → 200 status=COMPLETED (~39s)
```

**Minimum env for reproduction:**
```bash
ANTHROPIC_API_KEY=<valid key>
ANTHROPIC_MODEL=claude-haiku-4-5-20251001
MODEL_STRATEGY=anthropic
MODEL_FALLBACK=anthropic
QDRANT_HOST=localhost
JARVIS_SECRET_KEY=<32-char secret>
JARVIS_ADMIN_PASSWORD=<password>
```

**Bugs fixed to reach this proof (Cycles 5–7):**
1. `/api/v3/system/readiness` was missing from `_PUBLIC_PATHS` → 401 on healthcheck
2. `verify_boot.sh` never authenticated → all mission calls returned 401 silently
3. `convergence.py submit_mission` lacked `BackgroundTasks` → mission never executed
4. `orchestration_bridge.list_missions()` missing → AttributeError on listing
5. Bridge `get_mission_canonical` returned stale READY cache → poll always showed READY
6. `get_orchestrator` alias missing from `meta_orchestrator.py` → ImportError at startup
7. `datetime.UTC` incompatible with Python 3.10 → AttributeError in `observer/watcher.py`
8. `memory_bus.store` method shadowed the `@property store` accessor → `search()` AttributeError
9. Bridge `_TERMINAL_STATUSES`/`_LIVE_STATUSES` used `"DONE"` but canonical enum value is `"COMPLETED"`
10. `verify_boot.sh` polled for `"DONE"` but API returns `"COMPLETED"` → script never detected success
