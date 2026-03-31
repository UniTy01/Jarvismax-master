# JarvisMax — Architecture

> The primary interface is the Jarvis App (mobile + web), backed by the AI OS core.

## 6-Layer AI Operating System

```
┌──────────────────────────────────────────────────────────────┐
│                     CONTROL LAYER                             │
│  Approval gating · Logging · Observability · Health           │
│  core/cognitive_events/ · core/mission_guards.py              │
│  core/tool_permissions.py · api/routes/observability.py       │
├──────────────────────────────────────────────────────────────┤
│                     COGNITION LAYER                           │
│  MetaOrchestrator · Capability routing · Decision confidence  │
│  core/meta_orchestrator.py · core/capability_routing/         │
│  core/cognitive_bridge.py · core/decision_confidence.py       │
├──────────────────────────────────────────────────────────────┤
│                     PLANNING LAYER                            │
│  Execution plans · Validation · Workflow templates             │
│  core/planning/ · business/workflows/                         │
├──────────────────────────────────────────────────────────────┤
│                     SKILLS LAYER                              │
│  Domain skills · Quality checks · Skill chains                │
│  core/skills/ · business/skills/                              │
├──────────────────────────────────────────────────────────────┤
│                     EXECUTION LAYER                           │
│  Tool executor · Business actions · Artifact generation       │
│  core/tools_operational/ · core/business_actions.py           │
│  executor/ · core/tool_executor.py                            │
├──────────────────────────────────────────────────────────────┤
│                     MEMORY LAYER                              │
│  Execution history · Skill feedback · Decision traces         │
│  core/planning/execution_memory.py · core/skills/feedback.py │
│  core/cognitive_events/ · core/learning_traces.py             │
└──────────────────────────────────────────────────────────────┘
```

## Agent Roles (6 canonical)

| Role | Module | Responsibility |
|------|--------|----------------|
| CEO | agents/jarvis_team/ (orchestration) | Goal decomposition, prioritization, delegation |
| Architect | agents/jarvis_team/architect.py | System design, dependency awareness |
| Engineer | agents/jarvis_team/coder.py | Code generation and modification |
| Analyst | business/ agents (venture, offer, saas) | Research, evaluation, business analysis |
| Operator | core/tools_operational/tool_executor.py | Safe tool usage and execution |
| Reviewer | agents/jarvis_team/reviewer.py | Quality validation, self-improvement review |

## Key Modules

### Canonical (actively used)
- `core/meta_orchestrator.py` — Mission orchestration (CRITICAL, protected)
- `core/tool_executor.py` — Internal tool execution (CRITICAL, protected)
- `core/llm_factory.py` — LLM provider routing
- `core/cognitive_bridge.py` — Wires 8 cognitive modules
- `core/capability_routing/` — Capability-first provider selection
- `core/planning/` — Execution plans, validation, templates, memory
- `core/tools_operational/` — External tool registry and execution
- `core/skills/` — Domain skill system
- `core/self_improvement/` — V3 self-improvement with promotion pipeline
- `core/cognitive_events/` — Unified event journal
- `core/self_model/` — Runtime self-awareness

### Business Domain
- `business/skills/` — 10 domain skills (market, offer, persona, etc.)
- `business/tools/` — Tool definition files (n8n, etc.)
- `business/workflows/` — Reusable workflow templates
- `business/venture/`, `business/offer/`, `business/saas/`, `business/workflow/` — Agent logic

### Protected Paths (never auto-modified)
- core/meta_orchestrator.py, core/tool_executor.py, core/policy_engine.py
- api/auth.py, api/main.py, config/settings.py
- .env, docker-compose.yml, Dockerfile

## Data Flow

```
User Goal
  → MetaOrchestrator.run_mission()
    → Capability routing (resolve → score → select provider)
    → Plan construction (ExecutionPlan with steps)
    → For each step:
        → Skill preparation (build_prompt_context)
        → Business action execution (produce artifacts)
        → Tool execution (if approved)
    → Cognitive event journal (record everything)
    → Execution memory (store for reuse)
  → Results + artifacts
```
