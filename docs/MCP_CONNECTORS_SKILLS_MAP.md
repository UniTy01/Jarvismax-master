# MCP / Connectors / Skills Integration Map
_Last updated: 2026-04-04_

> Single source of truth for external MCP servers, connectors, and skill/tool
> integrations in Jarvis Max.
>
> Rule: every integration is **optional**, **behind a feature flag**,
> **testable**, and **removable without breaking core**.

---

## Status Classification

| Status | Meaning |
|--------|---------|
| **PROVEN** | Used in production, tested end-to-end |
| **CODE READY** | Code exists, not yet deployed/enabled in production |
| **STUB** | File exists, core logic not implemented (TODO present) |
| **DISABLED BY DEFAULT** | Wired via env var, off unless explicitly enabled |
| **NOT WIRED** | Dependency installed but not connected to runtime |
| **LEGACY** | Superseded, kept for reference |

---

## Integration Table

| Component | File | Status | Activate |
|-----------|------|--------|---------|
| Jarvis MCP server | `mcp/jarvis_mcp_server.py` | **CODE READY** | `MCP_SERVER_ENABLED=true` |
| GitHub MCP sidecar | `mcp/github_mcp_adapter.py` | **CODE READY** | `GITHUB_MCP_ENABLED=true` + deploy sidecar |
| Qdrant MCP sidecar | `mcp/qdrant_mcp_adapter.py` | **CODE READY** | `QDRANT_MCP_ENABLED=true` + deploy sidecar |
| Composio connector | `connectors/composio_adapter.py` | **STUB** | `COMPOSIO_ENABLED=true` (implement execute() first) |
| GitHub connector (gh CLI) | `connectors/github_connector.py` | **PROVEN** | Default — no flag needed |
| HTTP connector | `connectors/http_connector.py` | **PROVEN** | Default — no flag needed |
| Filesystem connector | `connectors/filesystem_connector.py` | **CODE READY** | Used internally |
| MCP registry/adapter | `integrations/mcp/` | **CODE READY** | Auto-initialised at boot |
| n8n bridge | `N8N_HOST` env var | **DISABLED BY DEFAULT** | Set `N8N_HOST` in .env |
| Qdrant vector memory | `qdrant-client` in requirements | **NOT WIRED** | Not yet connected to `memory/vector_memory.py` |
| LangGraph | `langgraph>=0.2.0` in requirements | **CODE READY** | Used for human-in-loop interrupt() |
| mcp-server-fetch | `mcp-server-fetch` in requirements | **CODE READY** | Invoked via npx/uvx |
| mcp-server-sqlite | `mcp-server-sqlite` in requirements | **CODE READY** | Invoked via npx/uvx |

---

## Architecture Map

```
Jarvis Core
     │
     ├── mcp/                          ← Jarvis as MCP server (expose to clients)
     │   ├── jarvis_mcp_server.py      ← FastMCP: memory_search, mission_status [CODE READY]
     │   ├── qdrant_mcp_adapter.py     ← Qdrant sidecar registration [CODE READY]
     │   ├── github_mcp_adapter.py     ← GitHub sidecar registration [CODE READY]
     │   └── hexstrike-ai/             ← Security research sidecar [CODE READY]
     │
     ├── integrations/mcp/             ← Jarvis as MCP client (call external tools)
     │   ├── mcp_registry.py           ← In-memory registry of servers+tools
     │   ├── mcp_adapter.py            ← HTTP dispatcher for tool calls
     │   └── mcp_models.py             ← MCPServer / MCPTool data models
     │
     ├── connectors/
     │   ├── github_connector.py       ← gh CLI [PROVEN]
     │   ├── http_connector.py         ← HTTP [PROVEN]
     │   ├── composio_adapter.py       ← Composio 250+ integrations [STUB]
     │   └── filesystem_connector.py   ← Local FS [CODE READY]
     │
     └── memory/vector_memory.py       ← numpy fallback (Qdrant: NOT WIRED)
```

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
| `COMPOSIO_API_KEY` | (empty) | Composio API key (.env only, never committed) |
| `N8N_HOST` | (empty) | n8n webhook base URL |

---

## Security Notes

| Component | Risk | Note |
|-----------|------|------|
| `jarvis_mcp_server.py` | Low | Read-only tools, no state mutation via MCP |
| `qdrant::search` | Low | Read-only vector search |
| `qdrant::upsert` | Medium | Writes to shared memory |
| `github::push_files` | **High** | `requires_approval=True` enforced |
| `github::create_pr` | **High** | `requires_approval=True` enforced |
| `composio_adapter` | Varies | High-risk actions flagged in stub |
| `GITHUB_TOKEN` | Critical | Must stay in sidecar env only — never in Jarvis core |
| `COMPOSIO_API_KEY` | High | `.env` only — never committed |

---

## How to Enable an Integration

All integrations are **off by default**. To enable:

```bash
# Jarvis as MCP server (for Claude Desktop etc.)
MCP_SERVER_ENABLED=true

# Qdrant MCP sidecar
QDRANT_MCP_ENABLED=true
# Also deploy: uvx mcp-server-qdrant

# GitHub MCP sidecar
GITHUB_MCP_ENABLED=true
# Also deploy: ghcr.io/github/github-mcp-server

# n8n bridge
N8N_HOST=http://n8n:5678
```

To re-disable: unset or set to `false`.

---

## Roadmap

- [ ] Wire `qdrant-client` to `memory/vector_memory.py` (add `QDRANT_MEMORY_ENABLED` flag)
- [ ] Implement `composio_adapter.py::_execute_composio()` (STUB → CODE READY)
- [ ] E2E test for `jarvis_mcp_server.py` with Claude Desktop
