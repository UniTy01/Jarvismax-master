# Rejected Patterns

## 1. Cost-Aware Model Routing
**Reason**: Requires changes to LLMFactory abstraction layer. High complexity. Deferred.

## 2. Objective Persistence Across Sessions
**Reason**: Needs resume logic with state recovery. Medium-high risk of partial execution bugs. Deferred.

## 3. Reusable Capability Compositions
**Reason**: Requires executable tool chain model. Skills capture steps but not runnable chains. Too much new infrastructure. Deferred.

## 4. Context Compression
**Reason**: Requires LLM call for summarization (adds cost and latency). Working memory token budget is sufficient for now.

## 5. Multi-Orchestrator Systems
**Reason**: Architecture violation. ONE MetaOrchestrator is non-negotiable.

## 6. Recursive Agent Spawning
**Reason**: Uncontrolled sprawl risk. Bounded mission loop is a core safety property.

## 7. Speculative AGI Abstractions
**Reason**: "Claw-type" project names (Qclaw, Clawcash, MaxClaw, IronClaw, AutoClaw) do not correspond to real open-source systems. Analysis used real frameworks instead.

## 8. Graph-Based Workflow DSL
**Reason**: LangGraph's graph DSL adds complexity. Jarvis linear pipeline is sufficient and simpler.
