# JarvisMax Kernel Specification v0.1

## Overview

The kernel is the minimal, stable, domain-agnostic cognitive OS core.
Everything else (business logic, tools, UI, agents) is an extension.

## Kernel Responsibilities

1. **Contract enforcement** — typed domain objects for all communication
2. **Event journaling** — canonical events for replay and audit
3. **Capability routing** — route work by capability, not agent identity
4. **Memory management** — typed memory with categories and lifecycle
5. **Policy enforcement** — risk → policy → approval separation
6. **Runtime lifecycle** — boot, initialize, expose handle

## Domain Contracts (`kernel/contracts/`)

| Contract | Purpose | Key Fields |
|----------|---------|------------|
| `Goal` | Structured objective | description, constraints, priority |
| `Mission` | Top-level work unit | mission_id, goal, status, plan_id |
| `Plan` | Execution blueprint | plan_id, steps[], risk_level |
| `PlanStep` | Single execution step | step_id, type, target_id, inputs |
| `Action` | Discrete system action | action_type, target, risk_level |
| `Decision` | System/human decision | decision_type, confidence, reason |
| `Observation` | Execution perception | source, content, confidence |
| `ExecutionResult` | Action outcome | ok, output, error, artifacts |
| `PolicyDecision` | Policy engine output | allowed, requires_approval, reason |
| `MemoryRecord` | Typed memory entry | memory_type, content, ttl |
| `SystemEvent` | Journal entry | event_type, summary, payload |

### Contract Invariants
- All IDs are globally unique (uuid4 hex prefix)
- Mission status transitions are validated (invalid transitions return False)
- Goal description is required (validation enforced)
- MemoryRecord TTL: 0 = permanent, >0 = expires after N seconds
- SystemEvent requires event_type and summary

## Capability Model (`kernel/capabilities/`)

12 kernel capabilities:

| Capability | Category | Providers |
|-----------|----------|-----------|
| plan_generation | planning | ceo, architect |
| plan_validation | planning | architect, reviewer |
| decision_evaluation | planning | ceo, reviewer |
| skill_execution | execution | analyst |
| tool_invocation | execution | operator |
| code_generation | execution | engineer |
| quality_review | execution | reviewer |
| artifact_generation | execution | analyst, engineer |
| memory_write | memory | system |
| memory_recall | memory | system |
| risk_evaluation | policy | system |
| policy_check | policy | system |

Agents are bundles of capabilities. Routing is capability-first.

## Event Model (`kernel/events/`)

28 canonical event types across 8 domains:

- **mission.\*** — lifecycle (created, planning, executing, completed, failed, cancelled)
- **plan.\*** — lifecycle (generated, validated, approved, rejected)
- **step.\*** — execution (started, completed, failed, needs_approval, approved)
- **tool.\*** — invocation (invoked, completed, failed)
- **skill.\*** — execution (prepared, completed)
- **memory.\*** — persistence (written, recalled)
- **policy.\*** — enforcement (evaluated, blocked)
- **approval.\*** — human gate (requested, granted, denied)
- **kernel.\*** — system (booted, shutdown)

All events delegate to the existing cognitive event journal.

## Memory Model (`kernel/memory/`)

5 typed memory categories:

| Type | Purpose | Persistence | TTL |
|------|---------|-------------|-----|
| working | Current mission context | In-memory | Configurable (default 1h) |
| episodic | What happened and when | Delegated | Permanent |
| execution | Plan run history | JSON file | Permanent |
| procedural | Learned approaches | Delegated | Permanent |
| semantic | Facts and knowledge | Delegated | Permanent |

## Policy Model (`kernel/policy/`)

Three-stage pipeline:

```
Action
  → RiskEngine.evaluate()     → RiskLevel (low/medium/high/critical)
  → PolicyEngine.evaluate()   → PolicyDecision (allowed, requires_approval)
  → ApprovalGate.request()    → (if needed) human approval
  → Execute or Block
```

- Risk engine: purely computes risk (no policy decisions)
- Policy engine: decides based on risk + rules (no approval handling)
- Approval gate: manages human approval flow (no risk/policy logic)

## Boot Lifecycle

```python
from kernel.runtime.boot import boot_kernel

runtime = boot_kernel()
# 1. Validate contracts (type smoke test)
# 2. Load capabilities (12 kernel capabilities)
# 3. Initialize policy engine + risk engine + approval gate
# 4. Initialize memory interfaces
# 5. Initialize event emitter
# 6. Emit kernel.booted event
# 7. Return KernelRuntime handle

runtime.status()  # {"booted": True, "version": "0.1.0", ...}
```

Standalone: `python -m kernel`

## Invariants

1. Kernel modules have ZERO dependency on FastAPI, UI, or business logic
2. All kernel emissions are fail-open (kernel never crashes on event failure)
3. Contract validation is strict but optional (validate() returns errors, doesn't throw)
4. Mission status transitions are enforced (can_transition → transition)
5. Memory TTL is enforced on read (expired records return None)
6. Policy decisions are deterministic for same inputs
7. All IDs use uuid4 hex prefix for global uniqueness
