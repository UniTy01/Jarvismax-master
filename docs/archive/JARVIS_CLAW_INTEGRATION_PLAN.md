# Jarvis Integration Plan — Selected Patterns

Only patterns with LOW/MEDIUM complexity and clear value are selected.

---

## 1. Value-Based Task Prioritization
- **Target module**: MetaOrchestrator (mission_classifier)
- **Implementation**: Add `value_score` field to MissionClassification. Compute from urgency × complexity × user-facing impact.
- **Expected benefit**: Better resource allocation
- **Risk**: LOW

## 2. Adaptive Planning Depth Enforcement
- **Target module**: MetaOrchestrator (run_mission)
- **Implementation**: Use classification.complexity to set planning_depth. Direct answer for trivial, skip planning for simple, full plan for complex.
- **Expected benefit**: 30-50% latency reduction for simple tasks
- **Risk**: LOW

## 3. Execution Strategy Switching
- **Target module**: core/orchestration/execution_supervisor
- **Implementation**: On first failure, if error_class suggests strategy mismatch, switch to alternative strategy (e.g., decompose task, use different tool).
- **Expected benefit**: Higher failure recovery rate
- **Risk**: LOW

## 4. Pre-Execution Confidence Estimation
- **Target module**: MetaOrchestrator (before execute)
- **Implementation**: Estimate confidence BEFORE execution based on: skill match quality, memory match quality, tool availability, past failure patterns. If low → use cautious strategy.
- **Expected benefit**: Fewer wasted executions
- **Risk**: LOW

## 5. Tool Reliability Integration in Planning
- **Target module**: context_assembler
- **Implementation**: Query capability_health_tracker during assembly. Exclude unhealthy tools from suggested_tools. Add health info to planning context.
- **Expected benefit**: Avoid known-broken tools
- **Risk**: LOW

## 6. Pre-Execution Failure Pattern Check
- **Target module**: MetaOrchestrator (between assemble and execute)
- **Implementation**: Before execution, search failure memory for similar past failures. If match found, inject warning + alternative approach into planning.
- **Expected benefit**: Stop repeating mistakes
- **Risk**: LOW

---

## DEFERRED (too complex or risky for this phase)

- Cost-aware model routing (needs LLM abstraction layer change)
- Objective persistence across sessions (needs resume logic)
- Reusable capability compositions (needs executable chain model)
- Context compression (needs summarization LLM call)
