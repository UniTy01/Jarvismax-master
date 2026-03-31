"""
JARVIS MAX — Orchestration Intelligence Layer
================================================
Deterministic mission brain upgrades for MetaOrchestrator.

This module provides:
1. CapabilityDispatcher — capability-first mission routing
2. MissionPlanner — plan validation (dependency, redundancy, impossibility)
3. MemoryInjector — early memory-aware context injection
4. OrchestrationTracer — structured trace for every mission
5. MissionCheckpointer — long-task continuity with resume/replan

Non-invasive: MetaOrchestrator calls these helpers.
Fail-open: every function returns a result or safe default.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

try:
    import structlog
    log = structlog.get_logger(__name__)
except ImportError:
    import logging
    log = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# 1. CAPABILITY DISPATCHER
# ═══════════════════════════════════════════════════════════════

class CapabilityType(str, Enum):
    CODE_GENERATION = "code_generation"
    CODE_REVIEW = "code_review"
    ANALYSIS = "analysis"
    RESEARCH = "research"
    PLANNING = "planning"
    WRITING = "writing"
    DATA_PROCESSING = "data_processing"
    SYSTEM_ADMIN = "system_admin"
    CONVERSATION = "conversation"
    UNKNOWN = "unknown"


# Keyword → capability mapping (deterministic, no LLM needed)
_CAPABILITY_KEYWORDS: dict[str, list[str]] = {
    CapabilityType.CODE_GENERATION: [
        "write code", "implement", "create function", "build", "code",
        "develop", "program", "script", "generate code", "add feature",
        "create module", "create file", "refactor",
    ],
    CapabilityType.CODE_REVIEW: [
        "review code", "audit", "check code", "find bugs", "security review",
        "code quality", "lint", "analyze code",
    ],
    CapabilityType.ANALYSIS: [
        "analyze", "investigate", "diagnose", "examine", "assess",
        "evaluate", "measure", "compare", "benchmark",
    ],
    CapabilityType.RESEARCH: [
        "research", "find information", "search", "look up", "learn about",
        "investigate", "explore", "discover",
    ],
    CapabilityType.PLANNING: [
        "plan", "design", "architect", "strategy", "roadmap",
        "outline", "organize", "schedule", "prioritize",
    ],
    CapabilityType.WRITING: [
        "write", "document", "draft", "compose", "summarize",
        "explain", "describe", "report",
    ],
    CapabilityType.DATA_PROCESSING: [
        "process data", "transform", "parse", "extract", "convert",
        "aggregate", "filter", "sort", "merge data",
    ],
    CapabilityType.SYSTEM_ADMIN: [
        "deploy", "configure", "install", "setup", "restart",
        "monitor", "backup", "migrate", "docker", "server",
    ],
    CapabilityType.CONVERSATION: [
        "hello", "hi", "hey", "thanks", "help", "what is",
        "tell me", "how are", "explain",
    ],
}


@dataclass
class CapabilityMatch:
    """Result of capability dispatch."""
    capability: str
    confidence: float   # 0.0-1.0
    keywords_matched: list[str]
    fallback: bool = False

    def to_dict(self) -> dict:
        return {
            "capability": self.capability,
            "confidence": round(self.confidence, 3),
            "keywords_matched": self.keywords_matched[:5],
            "fallback": self.fallback,
        }


class CapabilityDispatcher:
    """
    Routes missions to capabilities using deterministic keyword matching.
    Replaces loose text heuristics with explicit capability mapping.
    """

    def dispatch(self, goal: str) -> CapabilityMatch:
        """Match a goal to the best capability."""
        goal_lower = goal.lower().strip()
        scores: dict[str, tuple[float, list[str]]] = {}

        for cap, keywords in _CAPABILITY_KEYWORDS.items():
            matched = []
            for kw in keywords:
                if kw in goal_lower:
                    matched.append(kw)
            if matched:
                # Score: longer keyword matches count more
                score = sum(len(kw) for kw in matched) / max(len(goal_lower), 1)
                scores[cap] = (min(1.0, score * 3), matched)

        if not scores:
            return CapabilityMatch(
                capability=CapabilityType.CONVERSATION,
                confidence=0.2,
                keywords_matched=[],
                fallback=True,
            )

        # Pick highest scoring
        best = max(scores.items(), key=lambda x: x[1][0])
        return CapabilityMatch(
            capability=best[0],
            confidence=best[1][0],
            keywords_matched=best[1][1],
        )


# ═══════════════════════════════════════════════════════════════
# 2. MISSION PLANNER
# ═══════════════════════════════════════════════════════════════

@dataclass
class PlanStep:
    """A single step in a mission plan."""
    id: int
    action: str
    description: str
    depends_on: list[int] = field(default_factory=list)
    estimated_duration_s: float = 30.0
    capability_required: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id, "action": self.action,
            "description": self.description[:100],
            "depends_on": self.depends_on,
            "estimated_duration_s": self.estimated_duration_s,
            "capability_required": self.capability_required,
        }


@dataclass
class PlanValidation:
    """Result of plan validation."""
    valid: bool = True
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    redundant_steps: list[int] = field(default_factory=list)
    missing_deps: list[tuple[int, int]] = field(default_factory=list)
    impossible_steps: list[int] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "valid": self.valid,
            "warnings": self.warnings[:10],
            "errors": self.errors[:10],
            "redundant_steps": self.redundant_steps,
            "missing_deps": self.missing_deps,
            "impossible_steps": self.impossible_steps,
        }


class MissionPlanner:
    """
    Validates and improves mission plans.

    Detects:
    - Missing dependencies between steps
    - Redundant/duplicate steps
    - Impossible steps (unknown capability)
    - Unbounded plans (too many steps)
    - Circular dependencies
    """

    MAX_STEPS = 20
    KNOWN_ACTIONS = {
        "read", "write", "analyze", "search", "execute",
        "test", "deploy", "review", "plan", "generate",
        "transform", "validate", "monitor", "report",
    }

    def create_plan(self, goal: str, capability: CapabilityMatch) -> list[PlanStep]:
        """Create a minimal plan from goal + capability."""
        cap = capability.capability
        plans = {
            CapabilityType.CODE_GENERATION: [
                PlanStep(1, "analyze", "Understand requirements", capability_required="analysis"),
                PlanStep(2, "generate", "Generate code", depends_on=[1], capability_required="code_generation"),
                PlanStep(3, "test", "Validate output", depends_on=[2], capability_required="code_review"),
            ],
            CapabilityType.CODE_REVIEW: [
                PlanStep(1, "read", "Read target code", capability_required="analysis"),
                PlanStep(2, "analyze", "Analyze quality and issues", depends_on=[1], capability_required="code_review"),
                PlanStep(3, "report", "Generate review report", depends_on=[2], capability_required="writing"),
            ],
            CapabilityType.ANALYSIS: [
                PlanStep(1, "read", "Gather data", capability_required="analysis"),
                PlanStep(2, "analyze", "Analyze findings", depends_on=[1], capability_required="analysis"),
                PlanStep(3, "report", "Produce report", depends_on=[2], capability_required="writing"),
            ],
            CapabilityType.RESEARCH: [
                PlanStep(1, "search", "Search for information", capability_required="research"),
                PlanStep(2, "analyze", "Analyze findings", depends_on=[1], capability_required="analysis"),
                PlanStep(3, "report", "Summarize results", depends_on=[2], capability_required="writing"),
            ],
            CapabilityType.PLANNING: [
                PlanStep(1, "analyze", "Analyze requirements", capability_required="analysis"),
                PlanStep(2, "plan", "Create plan", depends_on=[1], capability_required="planning"),
                PlanStep(3, "validate", "Validate plan", depends_on=[2], capability_required="analysis"),
            ],
            CapabilityType.SYSTEM_ADMIN: [
                PlanStep(1, "analyze", "Check current state", capability_required="system_admin"),
                PlanStep(2, "plan", "Plan changes", depends_on=[1], capability_required="planning"),
                PlanStep(3, "execute", "Apply changes", depends_on=[2], capability_required="system_admin"),
                PlanStep(4, "validate", "Verify result", depends_on=[3], capability_required="analysis"),
            ],
        }

        return plans.get(cap, [
            PlanStep(1, "analyze", "Understand request", capability_required="analysis"),
            PlanStep(2, "execute", "Execute task", depends_on=[1], capability_required=cap),
        ])

    def validate(self, steps: list[PlanStep]) -> PlanValidation:
        """Validate a plan for correctness."""
        v = PlanValidation()

        if not steps:
            v.errors.append("Plan has no steps")
            v.valid = False
            return v

        if len(steps) > self.MAX_STEPS:
            v.errors.append(f"Plan too large: {len(steps)} steps (max {self.MAX_STEPS})")
            v.valid = False

        step_ids = {s.id for s in steps}

        # Check missing dependencies
        for step in steps:
            for dep in step.depends_on:
                if dep not in step_ids:
                    v.missing_deps.append((step.id, dep))
                    v.errors.append(f"Step {step.id} depends on missing step {dep}")

        if v.missing_deps:
            v.valid = False

        # Check circular dependencies
        if self._has_cycle(steps):
            v.errors.append("Plan has circular dependencies")
            v.valid = False

        # Check redundant steps (same action + same description)
        seen = set()
        for step in steps:
            key = f"{step.action}:{step.description}"
            if key in seen:
                v.redundant_steps.append(step.id)
                v.warnings.append(f"Step {step.id} appears redundant")
            seen.add(key)

        # Check impossible steps (action not in known set)
        for step in steps:
            if step.action not in self.KNOWN_ACTIONS:
                v.impossible_steps.append(step.id)
                v.warnings.append(f"Step {step.id} has unknown action: {step.action}")

        # Check ordering (depends_on must reference earlier steps)
        id_order = {s.id: i for i, s in enumerate(steps)}
        for step in steps:
            for dep in step.depends_on:
                if dep in id_order and id_order[dep] >= id_order[step.id]:
                    v.warnings.append(f"Step {step.id} depends on later step {dep}")

        return v

    def _has_cycle(self, steps: list[PlanStep]) -> bool:
        """Detect circular dependencies via DFS."""
        adj = {s.id: s.depends_on for s in steps}
        visited = set()
        in_stack = set()

        def dfs(node):
            if node in in_stack:
                return True
            if node in visited:
                return False
            visited.add(node)
            in_stack.add(node)
            for dep in adj.get(node, []):
                if dfs(dep):
                    return True
            in_stack.discard(node)
            return False

        return any(dfs(s.id) for s in steps if s.id not in visited)


# ═══════════════════════════════════════════════════════════════
# 3. MEMORY INJECTOR
# ═══════════════════════════════════════════════════════════════

@dataclass
class MemoryContext:
    """Relevant memory injected into mission planning."""
    project_context: list[str] = field(default_factory=list)
    user_preferences: list[str] = field(default_factory=list)
    past_missions: list[str] = field(default_factory=list)
    relevant_lessons: list[str] = field(default_factory=list)
    total_items: int = 0

    def to_dict(self) -> dict:
        return {
            "project_context": self.project_context[:3],
            "user_preferences": self.user_preferences[:3],
            "past_missions": self.past_missions[:3],
            "relevant_lessons": self.relevant_lessons[:3],
            "total_items": self.total_items,
        }

    def as_prompt_context(self) -> str:
        """Format as text for prompt injection."""
        parts = []
        if self.project_context:
            parts.append("Project context: " + "; ".join(self.project_context[:2]))
        if self.user_preferences:
            parts.append("User preferences: " + "; ".join(self.user_preferences[:2]))
        if self.past_missions:
            parts.append("Related past work: " + "; ".join(self.past_missions[:2]))
        if self.relevant_lessons:
            parts.append("Lessons learned: " + "; ".join(self.relevant_lessons[:2]))
        return "\n".join(parts) if parts else ""


class MemoryInjector:
    """
    Retrieves relevant memory BEFORE planning, not just during execution.
    Memory affects strategy selection and plan construction.
    """

    def inject(self, goal: str, capability: str = "") -> MemoryContext:
        """Pull relevant memory for a mission goal."""
        ctx = MemoryContext()

        # Source 1: MemoryFacade search
        try:
            from core.memory_facade import MemoryFacade
            mem = MemoryFacade()
            results = mem.search(goal, limit=5)
            for r in results:
                content = r.get("content", "") if isinstance(r, dict) else str(r)
                if content:
                    ctx.project_context.append(content[:150])
                    ctx.total_items += 1
        except Exception:
            pass

        # Source 2: Lesson memory from improvement loop
        try:
            from core.self_improvement_loop import LessonMemory
            lessons = LessonMemory()
            found = lessons.search(goal, limit=3)
            for lesson in found:
                text = f"{lesson.problem}: {lesson.lessons_learned}"
                ctx.relevant_lessons.append(text[:150])
                ctx.total_items += 1
        except Exception:
            pass

        # Source 3: Evaluation insights
        try:
            from core.evaluation_engine import AgentEvaluationEngine
            engine = AgentEvaluationEngine()
            trend = engine.get_trend(last_n=3)
            if trend:
                latest = trend[-1]
                if latest.get("score", 10) < 7:
                    weakness = latest.get("top_weakness", "")
                    if weakness and weakness != "none":
                        ctx.relevant_lessons.append(
                            f"Current weakness: {weakness} (score {latest.get('score', '?')}/10)")
                        ctx.total_items += 1
        except Exception:
            pass

        return ctx


# ═══════════════════════════════════════════════════════════════
# 4. ORCHESTRATION TRACER
# ═══════════════════════════════════════════════════════════════

@dataclass
class OrchestrationTrace:
    """Structured trace for mission orchestration."""
    mission_id: str = ""
    intent: str = ""
    capability: str = ""
    confidence: float = 0.0
    strategy: str = ""    # v1, v2, budget
    plan_steps: int = 0
    plan_valid: bool = True
    memory_items: int = 0
    execution_path: list[str] = field(default_factory=list)
    outcome: str = ""
    outcome_reason: str = ""
    duration_ms: float = 0.0
    started_at: float = 0.0
    completed_at: float = 0.0

    def to_dict(self) -> dict:
        return {
            "mission_id": self.mission_id,
            "intent": self.intent[:200],
            "capability": self.capability,
            "confidence": round(self.confidence, 3),
            "strategy": self.strategy,
            "plan_steps": self.plan_steps,
            "plan_valid": self.plan_valid,
            "memory_items": self.memory_items,
            "execution_path": self.execution_path[:10],
            "outcome": self.outcome,
            "outcome_reason": self.outcome_reason[:200],
            "duration_ms": round(self.duration_ms, 1),
        }


class OrchestrationTracer:
    """Records structured traces for every mission."""

    def __init__(self):
        self._traces: dict[str, OrchestrationTrace] = {}

    def start(self, mission_id: str, goal: str) -> OrchestrationTrace:
        trace = OrchestrationTrace(
            mission_id=mission_id,
            intent=goal,
            started_at=time.time(),
        )
        self._traces[mission_id] = trace
        return trace

    def record_capability(self, mission_id: str, match: CapabilityMatch) -> None:
        t = self._traces.get(mission_id)
        if t:
            t.capability = match.capability
            t.confidence = match.confidence
            t.execution_path.append(f"capability:{match.capability}")

    def record_plan(self, mission_id: str, steps: list[PlanStep],
                    validation: PlanValidation) -> None:
        t = self._traces.get(mission_id)
        if t:
            t.plan_steps = len(steps)
            t.plan_valid = validation.valid
            t.execution_path.append(f"plan:{len(steps)}_steps")

    def record_memory(self, mission_id: str, ctx: MemoryContext) -> None:
        t = self._traces.get(mission_id)
        if t:
            t.memory_items = ctx.total_items
            if ctx.total_items > 0:
                t.execution_path.append(f"memory:{ctx.total_items}_items")

    def record_strategy(self, mission_id: str, strategy: str) -> None:
        t = self._traces.get(mission_id)
        if t:
            t.strategy = strategy
            t.execution_path.append(f"strategy:{strategy}")

    def record_step(self, mission_id: str, step_name: str) -> None:
        t = self._traces.get(mission_id)
        if t:
            t.execution_path.append(step_name)

    def complete(self, mission_id: str, outcome: str, reason: str = "") -> OrchestrationTrace | None:
        t = self._traces.get(mission_id)
        if t:
            t.outcome = outcome
            t.outcome_reason = reason
            t.completed_at = time.time()
            t.duration_ms = (t.completed_at - t.started_at) * 1000
        return t

    def get(self, mission_id: str) -> OrchestrationTrace | None:
        return self._traces.get(mission_id)

    def get_recent(self, limit: int = 10) -> list[dict]:
        traces = sorted(self._traces.values(),
                        key=lambda t: t.started_at, reverse=True)
        return [t.to_dict() for t in traces[:limit]]


# ═══════════════════════════════════════════════════════════════
# 5. MISSION CHECKPOINTER
# ═══════════════════════════════════════════════════════════════

@dataclass
class Checkpoint:
    """A mission checkpoint for resume/replan."""
    mission_id: str
    step_id: int
    step_action: str
    state: str        # pending, completed, failed, skipped
    result: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "mission_id": self.mission_id, "step_id": self.step_id,
            "action": self.step_action, "state": self.state,
            "result": self.result[:200], "timestamp": self.timestamp,
        }


class MissionCheckpointer:
    """
    Tracks step-level progress for long-running missions.
    Enables resume from last successful checkpoint and replan on failure.
    """

    def __init__(self):
        self._checkpoints: dict[str, list[Checkpoint]] = {}

    def checkpoint(self, mission_id: str, step: PlanStep, state: str,
                   result: str = "") -> None:
        if mission_id not in self._checkpoints:
            self._checkpoints[mission_id] = []
        self._checkpoints[mission_id].append(Checkpoint(
            mission_id=mission_id,
            step_id=step.id,
            step_action=step.action,
            state=state,
            result=result,
        ))

    def get_checkpoints(self, mission_id: str) -> list[Checkpoint]:
        return self._checkpoints.get(mission_id, [])

    def get_last_completed(self, mission_id: str) -> int:
        """Return the ID of the last completed step, or 0 if none."""
        cps = self._checkpoints.get(mission_id, [])
        completed = [cp for cp in cps if cp.state == "completed"]
        return completed[-1].step_id if completed else 0

    def get_resume_point(self, mission_id: str) -> int:
        """Return the step ID to resume from (first non-completed)."""
        last = self.get_last_completed(mission_id)
        return last + 1

    def needs_replan(self, mission_id: str) -> bool:
        """Check if a mission needs replanning (>1 consecutive failures)."""
        cps = self._checkpoints.get(mission_id, [])
        if len(cps) < 2:
            return False
        recent = cps[-2:]
        return all(cp.state == "failed" for cp in recent)

    def get_drift_score(self, mission_id: str, original_steps: int) -> float:
        """Measure execution drift (0=on track, 1=fully drifted)."""
        cps = self._checkpoints.get(mission_id, [])
        if not cps or original_steps == 0:
            return 0.0
        completed = sum(1 for cp in cps if cp.state == "completed")
        failed = sum(1 for cp in cps if cp.state == "failed")
        # Drift increases with failures relative to plan size
        return min(1.0, failed / max(original_steps, 1))

    def clear(self, mission_id: str) -> None:
        self._checkpoints.pop(mission_id, None)


# ═══════════════════════════════════════════════════════════════
# UNIFIED ORCHESTRATION BRAIN
# ═══════════════════════════════════════════════════════════════

class OrchestrationBrain:
    """
    Unified intelligence layer that MetaOrchestrator consumes.

    Usage:
        brain = OrchestrationBrain()
        result = brain.prepare(mission_id, goal)
        # result contains: capability, plan, memory, trace
        # MetaOrchestrator uses these to execute deterministically
    """

    def __init__(self):
        self.dispatcher = CapabilityDispatcher()
        self.planner = MissionPlanner()
        self.memory = MemoryInjector()
        self.tracer = OrchestrationTracer()
        self.checkpointer = MissionCheckpointer()

    def prepare(self, mission_id: str, goal: str) -> dict:
        """
        Full orchestration preparation:
        1. Dispatch capability
        2. Inject memory
        3. Create plan
        4. Validate plan
        5. Start trace

        Returns dict with all orchestration context.
        """
        # 1. Capability dispatch
        cap = self.dispatcher.dispatch(goal)

        # 2. Memory injection
        mem = self.memory.inject(goal, cap.capability)

        # 3. Plan creation
        steps = self.planner.create_plan(goal, cap)

        # 4. Plan validation
        validation = self.planner.validate(steps)

        # 5. Start trace
        trace = self.tracer.start(mission_id, goal)
        self.tracer.record_capability(mission_id, cap)
        self.tracer.record_memory(mission_id, mem)
        self.tracer.record_plan(mission_id, steps, validation)

        # Select strategy
        strategy = "v2_budget" if len(steps) > 3 else "v1_standard"
        self.tracer.record_strategy(mission_id, strategy)

        return {
            "mission_id": mission_id,
            "capability": cap.to_dict(),
            "memory": mem.to_dict(),
            "memory_prompt": mem.as_prompt_context(),
            "plan": [s.to_dict() for s in steps],
            "plan_valid": validation.valid,
            "plan_validation": validation.to_dict(),
            "strategy": strategy,
            "steps": steps,
        }

    def complete_mission(self, mission_id: str, outcome: str,
                         reason: str = "") -> dict | None:
        """Record mission completion and return final trace."""
        trace = self.tracer.complete(mission_id, outcome, reason)
        return trace.to_dict() if trace else None

    def get_trace(self, mission_id: str) -> dict | None:
        trace = self.tracer.get(mission_id)
        return trace.to_dict() if trace else None

    def get_recent_traces(self, limit: int = 10) -> list[dict]:
        return self.tracer.get_recent(limit)
