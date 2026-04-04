# MCP / Connectors / Skills Integration Map
_Last updated: 2026-04-04 — Integration Cycle 1_

> Single source of truth for external MCP servers, connectors, and skill/tool
> integrations in Jarvis Max.
>
> Rule: every integration is **optional**, **behind a feature flag**,
> **testable**, and **removable without breaking core**.

---

## Decision Summary

| # | Project | Decision | Integration Type | Status |
|---|---------|----------|-----------------|--------|
| 1 | modelcontextprotocol/python-sdk | **INTEGRATE NOW** | Direct dep — FastMCP server | `mcp>=1.0.0` in requirements.txt |
| 2 | github/github-mcp-server | **INTEGRATE LATER** | MCP sidecar (Docker) | Adapter ready, sidecar not deployed |
| 3 | qdrant/mcp-server-qdrant | **INTEGRATE LATER** | MCP sidecar (Docker) | Adapter ready, sidecar not deployed |
| 4 | ComposioHQ/composio | **OPTIONAL** | Connector adapter (stub) | Stub ready, enable with flag |
| 5 | ComposioHQ/composio-base-py | **OPTIONAL** | (same as #4) | Part of composio-core |
| 6 | n8n-io/n8n | **ALREADY IN SETTINGS** | Docker sidecar | n8n_host in settings, no code change |
| 7 | crewAIInc/crewAI-tools | **REFERENCE ONLY** | (no integration) | Jarvis has native tool system |
| 8 | pydantic/pydantic-ai | **INTEGRATE LATER** | Agent wrapper | Pydantic v2 already present |
| 9 | langchain-ai/langgraph | **ALREADY INTEGRATED** | Direct dep | `langgraph>=0.2.0` in requirements |
| 10 | langchain-ai/langgraph-supervisor-py | **REFERENCE ONLY** | (no integration) | MetaOrchestrator covers this |
| 11 | modelcontextprotocol/inspector | **OPTIONAL** | Dev tooling only | Use in dev, not production |
| 12 | modelcontextprotocol/registry | **REFERENCE ONLY** | (no integration) | Jarvis has custom MCPRegistry |
| 13 | ComposioHQ/awesome-claude-skills | **REFERENCE ONLY** | (no integration) | Inspiration only |
| 14 | FlowiseAI/Flowise | **REJECT** | (no integration) | Too heavy, separate product |

---

## Architecture Map

```
Jarvis Core (frozen — backend contract v3)
     │
     ├── integrations/mcp/         ← MCP client (invoke external tools)
     │   ├── MCPRegistry           ← In-memory registry of servers+tools
     │   ├── MCPAdapter            ← HTTP dispatcher for tool calls
     │   ├── MCPServer / MCPTool   ← Data models
     │   └── (new) auto-register  ← on startup if flag=true
     │
     ├── mcp/                      ← MCP server (expose Jarvis as MCP endpoint)
     │   ├── jarvis_mcp_server.py  ← FastMCP server (NEW)
     │   ├── qdrant_mcp_adapter.py ← Registers Qdrant sidecar (NEW)
     │   ├── github_mcp_adapter.py ← Registers GitHub sidecar (NEW)
     │   └── hexstrike-ai/         ← Security research sidecar (existing)
     │
     ├── connectors/
     │   ├── github_connector.py   ← gh CLI (existing, still default)
     │   ├── composio_adapter.py   ← Composio stub (NEW)
     │   └── http_connector.py     ← HTTP (existing)
     │
     ├── memory/
     │   └── vector_memory.py      ← Local numpy fallback (existing)
     │       └── qdrant-client     ← Already in requirements (unused by default)
     │
     └── config/settings.py        ← All feature flags (NEW flags added)
```

---

## Layer Details

### MCP Layer

**Jarvis as MCP Server** (`mcp/jarvis_mcp_server.py`)
- Transport: stdio (default) + SSE optional
- Exposes: `memory_search`, `mission_status`, `list_missions`
- Read-only — no state mutation via MCP
- Activate: `MCP_SERVER_ENABLED=true`

```json
{
  "mcpServers": {
    "jarvis": {
      "command": "python3",
      "args": ["/app/mcp/jarvis_mcp_server.py"],
      "env": { "PYTHONPATH": "/app" }
    }
  }
}
```

**Qdrant MCP Sidecar** (`mcp/qdrant_mcp_adapter.py`)
- Tools: `qdrant::search` (low risk), `qdrant::upsert` (medium risk)
- Activate: `QDRANT_MCP_ENABLED=true` + deploy `qdrant/mcp-server-qdrant` sidecar
- Sidecar: `uvx mcp-server-qdrant` (Python, no Node.js required)

**GitHub MCP Sidecar** (`mcp/github_mcp_adapter.py`)
- Tools: search_code, list_issues (read) + create_issue, create_pr, push_files (approval required)
- Activate: `GITHUB_MCP_ENABLED=true` + deploy `ghcr.io/github/github-mcp-server`
- `GITHUB_TOKEN` must be in sidecar env ONLY — never in Jarvis core

### Connector Layer

**Composio** (`connectors/composio_adapter.py`)
- Status: stub (not implemented)
- Activate: `COMPOSIO_ENABLED=true` + `COMPOSIO_API_KEY=...` + `pip install composio-core`
- High-risk actions (send_email, create_issue) flagged for approval
- See `_execute_composio()` for implementation TODO

**n8n** (settings.py `n8n_host`)
- Already configured via `N8N_HOST` env var
- No code integration needed — Jarvis calls n8n webhooks via http_connector

### Memory Layer

**Qdrant** (already in requirements)
- `qdrant-client>=1.9.0` installed
- Not yet wired to `memory/vector_memory.py` (uses numpy fallback)
- Next step: add `QDRANT_MEMORY_ENABLED=true` flag to switch vector_memory backend

### Skill / Tool Layer

**LangGraph** (already in requirements)
- `langgraph>=0.2.0` — upper bound relaxed to `<0.4.0`
- Used for human-in-loop `interrupt()` pattern
- No change needed

**crewAI-tools**: REFERENCE ONLY
- Jarvis has native tool system in `tools/` and `agents/`
- crewAI-tools patterns are good reference for new tool development

**PydanticAI**: INTEGRATE LATER
- Could wrap individual agents with Pydantic-AI for type-safe I/O
- Implementation: `agents/pydantic_skill_wrapper.py` (not yet created)
- Dependency: `pydantic-ai>=0.0.14` (not yet in requirements)

---

## Feature Flags

| Env Var | Default | Effect |
|---------|---------|--------|
| `MCP_SERVER_ENABLED` | false | Start `mcp/jarvis_mcp_server.py` on startup |
| `MCP_SERVER_PORT` | 8765 | Port for MCP server (SSE transport) |
| `MCP_SERVER_HOST` | 0.0.0.0 | Host for MCP server |
| `QDRANT_MCP_ENABLED` | false | Register Qdrant sidecar in MCPRegistry |
| `QDRANT_MCP_URL` | http://qdrant-mcp:8000 | Qdrant MCP sidecar endpoint |
| `GITHUB_MCP_ENABLED` | false | Register GitHub sidecar in MCPRegistry |
| `GITHUB_MCP_URL` | http://github-mcp:3000 | GitHub MCP sidecar endpoint |
| `COMPOSIO_ENABLED` | false | Enable Composio connector |
| `COMPOSIO_API_KEY` | (empty) | Composio API key (keep in .env only) |

---

## Security Notes

| Component | Risk | Note |
|-----------|------|------|
| `jarvis_mcp_server.py` | Low | Read-only tools, no mutation |
| `qdrant::search` | Low | Read-only vector search |
| `qdrant::upsert` | Medium | Writes to shared memory |
| `github::push_files` | **High** | requires_approval=True enforced |
| `github::create_pr` | **High** | requires_approval=True enforced |
| `composio_adapter` | Varies | High-risk actions flagged in code |
| GITHUB_TOKEN | Critical | Must stay in sidecar env, never in Jarvis core |
| COMPOSIO_API_KEY | High | .env only, never committed |

---

## How to Disable Any Integration

All integrations are off by default. To explicitly disable:

```bash
# Disable Qdrant MCP sidecar
QDRANT_MCP_ENABLED=false  # (already default)

# Disable GitHub MCP sidecar
GITHUB_MCP_ENABLED=false  # (already default)

# Disable Composio
COMPOSIO_ENABLED=false    # (already default)

# Disable Jarvis MCP server
MCP_SERVER_ENABLED=false  # (already default)
```

To remove code completely:
- Delete `mcp/qdrant_mcp_adapter.py` — no other file imports it
- Delete `mcp/github_mcp_adapter.py` — no other file imports it
- Delete `connectors/composio_adapter.py` — no other file imports it
- Delete `mcp/jarvis_mcp_server.py` — standalone, not imported by core

---

## Production Readiness

| Component | Status | Notes |
|-----------|--------|-------|
| `mcp>=1.0.0` in requirements | ✅ Production-ready | Standard SDK, well-maintained |
| `mcp/jarvis_mcp_server.py` | ⚡ Experimental | Read-only, safe to test |
| `mcp/qdrant_mcp_adapter.py` | ⚡ Experimental | Needs sidecar deployed first |
| `mcp/github_mcp_adapter.py` | ⚡ Experimental | Needs sidecar deployed first |
| `connectors/composio_adapter.py` | 🚧 Stub | Not implemented yet |
| Settings feature flags | ✅ Production-ready | All default to false |
| Test suite (16 tests) | ✅ All passing | 16/16 green |

---

## Rejected Projects

| Project | Reason |
|---------|--------|
| FlowiseAI/Flowise | Full Node.js visual builder — separate product, not backend integration |
| crewAIInc/crewAI-tools | Jarvis has native tool system; adding crewAI adds heavy dep for no gain |
| langchain-ai/langgraph-supervisor-py | MetaOrchestrator already covers this pattern, no benefit to adopt external supervisor |
| modelcontextprotocol/registry | Jarvis has custom MCPRegistry; official registry not needed yet |
| ComposioHQ/awesome-claude-skills | Reference/inspiration only, no code integration |

---

## Next 10 Tasks

1. **Wire Qdrant sidecar to docker-compose.override.yml** — add `qdrant-mcp` service when `QDRANT_MCP_ENABLED=true`
2. **Wire GitHub MCP sidecar to docker-compose.override.yml** — add `github-mcp` service when `GITHUB_MCP_ENABLED=true`
3. **Auto-register adapters on startup** — call `register_qdrant_mcp()` / `register_github_mcp()` in `api/startup_checks.py` based on flags
4. **Switch vector_memory backend to Qdrant** — add `QDRANT_MEMORY_ENABLED=true` path in `memory/vector_memory.py`
5. **Implement ComposioAdapter._execute_composio()** — when COMPOSIO_ENABLED is needed, implement with composio-core SDK
6. **Add MCP server to docker-compose** — optional service for `mcp/jarvis_mcp_server.py` (SSE transport)
7. **PydanticAI agent wrapper** — `agents/pydantic_skill_wrapper.py` for type-safe agent I/O
8. **LangGraph version bump** — test with `langgraph>=0.2.0,<0.4.0` (upper bound now relaxed)
9. **MCP Inspector integration** — add `mcp-inspector` as dev-only Docker service for debugging
10. **Observability** — add MCP tool call traces to Langfuse when `LANGFUSE_ENABLED=true`
