# Executor Upgrade Report

## Before
- ExecutionResult contract (11 ErrorClass categories)
- Retry policy (retryable classification)
- Execution engine (thread-safe task queue)

## After (what changed)
1. **Observation contract** (OpenHands-inspired): `executor/observation.py`
   - Typed observations: tool_output, llm_response, error, timeout, approval_required
   - Cost tracking per observation: tokens_in, tokens_out, cost_usd
   - Provenance: source_tool, source_step

2. **Execution Budget**: `executor/observation.py`
   - Multi-dimensional limits: tokens, cost, steps, duration
   - Enforcement: is_exceeded() checks all dimensions
   - Remaining budget percentage for adaptive behavior

3. **Output Validation** (OpenHands-inspired): `executor/output_validator.py`
   - Secret leak detection: OpenAI keys, GitHub tokens, AWS keys, passwords
   - Error masking detection: output says "success" but contains tracebacks
   - JSON format validation
   - Auto-redaction of sensitive data

4. **Capability Health Tracking**: `executor/capability_health.py`
   - Per-capability success rate, avg latency, last error
   - is_healthy() check for planning decisions
   - unhealthy_capabilities() for MetaOrchestrator

## Canonical contracts (unchanged)
- ExecutionResult: one contract, one taxonomy, one retry policy
- CapabilityRequest/Result: one dispatch path
- ErrorClass: 11 categories (unchanged)

## Tests: 30 covering all new modules
