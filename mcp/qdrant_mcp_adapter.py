"""
mcp/qdrant_mcp_adapter.py — Qdrant MCP sidecar adapter.

Registers the qdrant-mcp-server sidecar (qdrant/mcp-server-qdrant) into
Jarvis's existing MCPRegistry so that agents can query/upsert vectors
via the standard MCP tool invocation path.

Feature flag : QDRANT_MCP_ENABLED=true
Sidecar repo : https://github.com/qdrant/mcp-server-qdrant
Sidecar URL  : QDRANT_MCP_URL (default: http://qdrant-mcp:8000)

How it works:
  1. register_qdrant_mcp(registry, settings) is called at startup
     (in api/startup_checks.py or main.py when QDRANT_MCP_ENABLED=true)
  2. The MCPServer entry points to the qdrant-mcp sidecar HTTP endpoint
  3. MCPTools "qdrant::search" and "qdrant::upsert" are registered
  4. Agents invoke them via MCPAdapter.invoke_tool("qdrant::search", {...})

Docker compose (add to docker-compose.override.yml):
  qdrant-mcp:
    image: python:3.12-slim
    command: uvx mcp-server-qdrant
    environment:
      QDRANT_URL: http://qdrant:6333
      QDRANT_API_KEY: ${QDRANT_API_KEY:-}
      COLLECTION_NAME: jarvis_memory
      QDRANT_LOCAL_PATH: ""  # empty = use QDRANT_URL
    ports:
      - "8001:8000"

Security notes:
  - risk_level=medium (vector data may contain sensitive context)
  - requires_approval=False (read: search, write: upsert by design)
  - disable: set QDRANT_MCP_ENABLED=false (default)
"""
from __future__ import annotations

import structlog

log = structlog.get_logger("mcp.qdrant_adapter")


def register_qdrant_mcp(registry, settings) -> bool:
    """
    Register the Qdrant MCP sidecar in the Jarvis MCPRegistry.

    Args:
        registry: MCPRegistry instance (from integrations.mcp.mcp_registry)
        settings: Settings instance (from config.settings)

    Returns:
        True if registered, False if disabled or already registered.
    """
    if not getattr(settings, "qdrant_mcp_enabled", False):
        log.debug("qdrant_mcp_disabled", reason="QDRANT_MCP_ENABLED not set")
        return False

    # Avoid double registration
    if registry.get_server("qdrant-mcp") is not None:
        log.debug("qdrant_mcp_already_registered")
        return True

    from integrations.mcp.mcp_models import MCPServer, MCPTool

    url = getattr(settings, "qdrant_mcp_url", "http://qdrant-mcp:8000")

    # Register sidecar server
    server = MCPServer(
        server_id="qdrant-mcp",
        name="Qdrant Vector Memory (MCP)",
        endpoint=url,
        transport="http",
        capabilities=["search", "upsert", "delete"],
        health_status="unknown",
        risk_level="medium",
        requires_approval=False,
        metadata={
            "provider": "qdrant/mcp-server-qdrant",
            "collection": "jarvis_memory",
            "docs": "https://github.com/qdrant/mcp-server-qdrant",
        },
    )
    registry.register_server(server)

    # Register search tool
    registry.register_tool(MCPTool(
        tool_id="qdrant::search",
        server_id="qdrant-mcp",
        name="qdrant_search",
        description=(
            "Search Jarvis's Qdrant vector memory. "
            "Returns the top_k most similar documents to the query."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language search query",
                },
                "collection": {
                    "type": "string",
                    "description": "Qdrant collection name",
                    "default": "jarvis_memory",
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of results to return",
                    "default": 5,
                    "minimum": 1,
                    "maximum": 50,
                },
            },
            "required": ["query"],
        },
        risk_level="low",
        requires_approval=False,
        tags=["memory", "search", "qdrant", "vector"],
    ))

    # Register upsert tool
    registry.register_tool(MCPTool(
        tool_id="qdrant::upsert",
        server_id="qdrant-mcp",
        name="qdrant_upsert",
        description=(
            "Store a document in Jarvis's Qdrant vector memory. "
            "The document is embedded and persisted for future searches."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Document text to store",
                },
                "metadata": {
                    "type": "object",
                    "description": "Optional metadata (source, tags, mission_id, ...)",
                    "default": {},
                },
                "collection": {
                    "type": "string",
                    "description": "Qdrant collection name",
                    "default": "jarvis_memory",
                },
            },
            "required": ["text"],
        },
        risk_level="medium",
        requires_approval=False,
        tags=["memory", "upsert", "qdrant", "vector"],
    ))

    log.info(
        "qdrant_mcp_registered",
        server_id="qdrant-mcp",
        url=url,
        tools=["qdrant::search", "qdrant::upsert"],
    )
    return True


def unregister_qdrant_mcp(registry) -> bool:
    """Remove Qdrant MCP registration (e.g. on settings change or shutdown)."""
    return registry.unregister_server("qdrant-mcp")
