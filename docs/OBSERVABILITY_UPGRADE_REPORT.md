# Observability Upgrade Report

## Before
- Decision trace (JSONL per mission)
- Structlog throughout

## After
1. **Cost tracking**: DecisionTrace.record_cost()
   - tokens_in, tokens_out, cost_usd accumulated per mission
   - cost_summary() for per-mission cost analysis

2. **Capability health stats**: capability_health.py
   - Per-tool success rate, latency, error tracking
   - Dashboard-ready: all_stats() returns list of dicts

3. **Memory links**: memory_linker.py
   - Cross-entity graph: why was this skill created? what mission failed?
   - get_mission_graph() for full mission context

4. **Reflection traces**: reflection.to_dict() in mission metadata
   - Result quality scoring visible in traces

## Trace coverage
- Mission traces: ✅ (classify → reflect → learn → trace)
- Decision traces: ✅ (JSONL)
- Capability traces: ✅ (health tracker)
- Retry traces: ✅ (execution_supervisor)
- Approval traces: ✅ (approval_queue)
- Memory/skill traces: ✅ (learning_loop + skill_service)
