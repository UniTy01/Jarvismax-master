# Capability Selection Consolidation

## Status: COHERENT ✅

- 3 types: NATIVE_TOOL | PLUGIN | MCP_TOOL
- Health tracking per capability (success rate, latency)
- Pre-execution checks query health before execution
- Unhealthy tools excluded from suggestions
- Business missions route to skill-based reasoning (no tool bypass)
- All capability invocations flow through CapabilityDispatcher
