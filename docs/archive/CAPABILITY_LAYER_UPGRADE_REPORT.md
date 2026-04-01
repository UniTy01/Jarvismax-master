# Capability Layer Upgrade Report

## Before
- CapabilityRequest/Result contracts
- CapabilityDispatcher (native/plugin/MCP routing)
- Single dispatch path

## After
1. **Capability health tracking**: `executor/capability_health.py`
   - Per-capability: success rate, avg latency, last error
   - is_healthy() for planning decisions
   - unhealthy_capabilities() for MetaOrchestrator avoidance
   - Singleton, thread-safe

## Unified model (UNCHANGED)
- CapabilityType: NATIVE_TOOL | PLUGIN | MCP_TOOL
- All types flow through same request/result contracts
- Single dispatch point in CapabilityDispatcher

## What was NOT copied
- Plugin auto-discovery (explicit registration = safer)
