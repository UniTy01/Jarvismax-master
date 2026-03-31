"""
JARVIS MAX — Multi-Mission Intelligence Layer
================================================
Allows Jarvis to reason across multiple concurrent missions safely.

Parts:
1. Mission Priority Model — structured urgency/complexity/risk/dependency scoring
2. Parallel Plan Compatibility — detect safe concurrent execution
3. Resource Conflict Detection — file, tool, and environment contention
4. Mission Queue Intelligence — execute/delay/split/merge heuristics
5. Long Horizon Memory — structured mission outcome storage

All functions fail-open. No execution logic changes. No scheduler rewrite.
Purely additive architecture for future planner integration.

Usage:
    from core.multi_mission_intelligence import (
        score_mission_priority,
        check_parallel_compatibility,
        detect_resource_conflicts,
        suggest_queue_action,
        record_mission_outcome, get_mission_history,
        export_multi_mission_artifacts,
    )
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

try:
    import structlog
    log = structlog.get_logger(__name__)
except ImportError:
    import logging
    log = logging.getLogger(__name__)

REPO_ROOT = Path(os.environ.get("JARVISMAX_REPO", ".")).resolve()


# ═══════════════════════════════════════════════════════════════
# PART 1 — MISSION PRIORITY MODEL
# ═══════════════════════════════════════════════════════════════

class Urgency(str, Enum):
    CRITICAL  = "critical"   # Blocking other work, production issue
    HIGH      = "high"       # Time-sensitive, user waiting
    MEDIUM    = "medium"     # Normal priority
    LOW       = "low"        # Background, can wait
    DEFERRED  = "deferred"   # Explicitly postponed

    @property
    def weight(self) -> float:
        return {"critical": 1.0, "high": 0.8, "medium": 0.5, "low": 0.3, "deferred": 0.1}[self.value]


class Complexity(str, Enum):
    TRIVIAL = "trivial"   # Single tool, single step
    SIMPLE  = "simple"    # 2-3 steps, one agent
    MODERATE = "moderate" # Multi-agent, multi-step
    COMPLEX = "complex"   # Deep planning, many agents
    EPIC    = "epic"      # Multi-cycle, long-running

    @property
    def depth(self) -> int:
        return {"trivial": 1, "simple": 2, "moderate": 3, "complex": 4, "epic": 5}[self.value]


@dataclass
class MissionPriority:
    """Canonical priority scoring for a mission.

    Attributes:
        mission_id: Unique mission identifier.
        urgency: How time-sensitive (critical → deferred).
        complexity: How many steps/agents needed.
        risk_level: How much can go wrong (1-10).
        dependencies: IDs of missions that must complete first.
        resource_requirements: Tools and files this mission needs.
        estimated_duration_s: Expected execution time.
        composite_score: Final priority score (0.0-1.0, higher = more urgent).
    """
    mission_id:           str
    urgency:              Urgency = Urgency.MEDIUM
    complexity:           Complexity = Complexity.MODERATE
    risk_level:           int = 5
    dependencies:         list[str] = field(default_factory=list)
    resource_requirements: list[str] = field(default_factory=list)
    estimated_duration_s: int = 120
    composite_score:      float = 0.0

    def to_dict(self) -> dict:
        return {
            "mission_id": self.mission_id,
            "urgency": self.urgency.value,
            "complexity": self.complexity.value,
            "risk_level": self.risk_level,
            "dependencies": self.dependencies,
            "resource_requirements": self.resource_requirements,
            "estimated_duration_s": self.estimated_duration_s,
            "composite_score": round(self.composite_score, 3),
        }


# Keywords that signal urgency
_URGENCY_SIGNALS: dict[str, Urgency] = {
    "urgent":     Urgency.CRITICAL,
    "critical":   Urgency.CRITICAL,
    "production": Urgency.CRITICAL,
    "broken":     Urgency.HIGH,
    "asap":       Urgency.HIGH,
    "quickly":    Urgency.HIGH,
    "fix now":    Urgency.HIGH,
    "blocker":    Urgency.HIGH,
    "when you can": Urgency.LOW,
    "background": Urgency.LOW,
    "low priority": Urgency.LOW,
    "later":      Urgency.DEFERRED,
    "someday":    Urgency.DEFERRED,
}

# Keywords that signal complexity
_COMPLEXITY_SIGNALS: dict[str, Complexity] = {
    "simple":       Complexity.SIMPLE,
    "quick":        Complexity.TRIVIAL,
    "just":         Complexity.TRIVIAL,
    "refactor":     Complexity.COMPLEX,
    "architecture": Complexity.COMPLEX,
    "migration":    Complexity.EPIC,
    "multi-cycle":  Complexity.EPIC,
    "redesign":     Complexity.EPIC,
    "overnight":    Complexity.EPIC,
}


def score_mission_priority(
    mission_id: str,
    description: str,
    plan_steps: int = 0,
    risk_score: int = 5,
    tools_needed: list[str] | None = None,
    files_targeted: list[str] | None = None,
    depends_on: list[str] | None = None,
    explicit_urgency: str | None = None,
) -> MissionPriority:
    """
    Score the priority of a mission for queue ordering.

    Composite score formula:
        0.35 * urgency_weight
      + 0.20 * (1 - risk/10)       # lower risk = higher priority for auto-execution
      + 0.15 * dependency_factor    # blocked missions get lower score
      + 0.15 * (1 / complexity)     # simpler = faster to execute
      + 0.15 * recency_bonus        # newer missions get a small boost

    Returns MissionPriority with composite_score. Never raises.
    """
    try:
        desc_lower = description.lower()

        # Detect urgency
        urgency = Urgency.MEDIUM
        if explicit_urgency:
            try:
                urgency = Urgency(explicit_urgency)
            except ValueError:
                pass
        else:
            for keyword, urg in _URGENCY_SIGNALS.items():
                if keyword in desc_lower:
                    urgency = urg
                    break

        # Detect complexity
        complexity = Complexity.MODERATE
        if plan_steps <= 1:
            complexity = Complexity.TRIVIAL
        elif plan_steps <= 3:
            complexity = Complexity.SIMPLE
        elif plan_steps <= 6:
            complexity = Complexity.MODERATE
        elif plan_steps <= 10:
            complexity = Complexity.COMPLEX
        else:
            complexity = Complexity.EPIC
        # Override with keyword signals — use the higher (more complex) of
        # plan_steps-based and keyword-based complexity to avoid downgrading.
        for keyword, comp in _COMPLEXITY_SIGNALS.items():
            if keyword in desc_lower:
                if comp.depth > complexity.depth:
                    complexity = comp
                break

        dependencies = depends_on or []
        resources = (tools_needed or []) + (files_targeted or [])

        # Estimated duration
        base_duration = {
            Complexity.TRIVIAL: 30,
            Complexity.SIMPLE: 60,
            Complexity.MODERATE: 180,
            Complexity.COMPLEX: 600,
            Complexity.EPIC: 1800,
        }[complexity]

        # Composite score
        urgency_factor = urgency.weight * 0.35
        risk_factor = (1 - risk_score / 10) * 0.20
        dependency_factor = (0.15 if not dependencies else 0.05)
        complexity_factor = (1 / complexity.depth) * 0.15
        recency_bonus = 0.15  # all new missions get full recency

        composite = urgency_factor + risk_factor + dependency_factor + complexity_factor + recency_bonus
        composite = round(min(max(composite, 0.0), 1.0), 3)

        return MissionPriority(
            mission_id=mission_id,
            urgency=urgency,
            complexity=complexity,
            risk_level=risk_score,
            dependencies=dependencies,
            resource_requirements=resources,
            estimated_duration_s=base_duration,
            composite_score=composite,
        )
    except Exception as e:
        log.debug("priority_scoring_failed", err=str(e)[:100])
        return MissionPriority(mission_id=mission_id, composite_score=0.5)


# ═══════════════════════════════════════════════════════════════
# PART 2 — PARALLEL PLAN COMPATIBILITY
# ═══════════════════════════════════════════════════════════════

class ParallelSafety(str, Enum):
    SAFE        = "safe"         # No conflicts, can run simultaneously
    CAUTION     = "caution"      # Minor overlap, probably safe
    UNSAFE      = "unsafe"       # Conflicts detected, do NOT parallelize

    @property
    def can_parallelize(self) -> bool:
        return self in (ParallelSafety.SAFE, ParallelSafety.CAUTION)


@dataclass
class ParallelCompatibility:
    """Assessment of whether two missions can run concurrently.

    Attributes:
        mission_a: First mission ID.
        mission_b: Second mission ID.
        safety: safe | caution | unsafe.
        conflicts: List of detected conflict descriptions.
        shared_tools: Tools needed by both missions.
        shared_files: Files targeted by both missions.
        risk_sum: Combined risk level.
        recommendation: Human-readable action.
    """
    mission_a:    str
    mission_b:    str
    safety:       ParallelSafety = ParallelSafety.SAFE
    conflicts:    list[str] = field(default_factory=list)
    shared_tools: list[str] = field(default_factory=list)
    shared_files: list[str] = field(default_factory=list)
    risk_sum:     int = 0
    recommendation: str = ""

    def to_dict(self) -> dict:
        return {
            "mission_a": self.mission_a,
            "mission_b": self.mission_b,
            "safety": self.safety.value,
            "can_parallelize": self.safety.can_parallelize,
            "conflicts": self.conflicts,
            "shared_tools": self.shared_tools,
            "shared_files": self.shared_files,
            "risk_sum": self.risk_sum,
            "recommendation": self.recommendation,
        }


# Tools that are write-exclusive (only one mission can use at a time)
_WRITE_EXCLUSIVE_TOOLS = frozenset({
    "write_file", "write_file_safe", "replace_in_file", "file_create",
    "file_delete_safe", "git_commit", "git_push",
    "docker_restart", "docker_compose_up", "docker_compose_down",
    "docker_compose_build", "memory_store_solution", "memory_store_error",
})

# Tools that are safe for concurrent read access
_READ_SAFE_TOOLS = frozenset({
    "read_file", "search_in_files", "list_directory", "list_project_structure",
    "count_lines", "git_status", "git_diff", "git_log", "git_branch",
    "docker_ps", "docker_logs", "docker_inspect", "memory_search_similar",
    "fetch_url", "search_pypi", "api_healthcheck", "env_checker",
})

# Maximum combined risk for parallel execution
_MAX_PARALLEL_RISK = 12


def check_parallel_compatibility(
    priority_a: MissionPriority,
    priority_b: MissionPriority,
) -> ParallelCompatibility:
    """
    Check if two missions can run concurrently.

    Safety heuristics:
    1. Non-overlapping write tools → SAFE
    2. Overlapping read-only tools → SAFE
    3. Overlapping write tools → UNSAFE
    4. Same target files → UNSAFE
    5. Combined risk > threshold → CAUTION
    6. Dependency chain → UNSAFE

    Returns ParallelCompatibility. Never raises.
    """
    try:
        result = ParallelCompatibility(
            mission_a=priority_a.mission_id,
            mission_b=priority_b.mission_id,
        )

        resources_a = set(priority_a.resource_requirements)
        resources_b = set(priority_b.resource_requirements)

        # Separate tools and files
        tools_a = resources_a & (set(_WRITE_EXCLUSIVE_TOOLS) | set(_READ_SAFE_TOOLS))
        tools_b = resources_b & (set(_WRITE_EXCLUSIVE_TOOLS) | set(_READ_SAFE_TOOLS))
        files_a = resources_a - tools_a
        files_b = resources_b - tools_b

        # 1. Check dependency chains
        if priority_a.mission_id in priority_b.dependencies or \
           priority_b.mission_id in priority_a.dependencies:
            result.safety = ParallelSafety.UNSAFE
            result.conflicts.append("dependency_chain")
            result.recommendation = "Execute sequentially — dependency chain detected."
            return result

        # 2. Check write tool conflicts
        write_a = tools_a & _WRITE_EXCLUSIVE_TOOLS
        write_b = tools_b & _WRITE_EXCLUSIVE_TOOLS
        shared_writes = write_a & write_b
        if shared_writes:
            result.shared_tools = sorted(shared_writes)
            result.conflicts.append(f"write_tool_conflict: {','.join(shared_writes)}")
            result.safety = ParallelSafety.UNSAFE

        # 3. Check file conflicts
        shared_files = files_a & files_b
        if shared_files:
            result.shared_files = sorted(shared_files)
            result.conflicts.append(f"file_conflict: {','.join(list(shared_files)[:5])}")
            if result.safety != ParallelSafety.UNSAFE:
                result.safety = ParallelSafety.UNSAFE

        # 4. Check combined risk
        result.risk_sum = priority_a.risk_level + priority_b.risk_level
        if result.risk_sum > _MAX_PARALLEL_RISK and result.safety == ParallelSafety.SAFE:
            result.safety = ParallelSafety.CAUTION
            result.conflicts.append(f"combined_risk_high: {result.risk_sum}")

        # 5. Read-only overlap is fine
        read_shared = (tools_a & _READ_SAFE_TOOLS) & (tools_b & _READ_SAFE_TOOLS)
        if read_shared and not result.conflicts:
            result.shared_tools = sorted(read_shared)
            # No conflict — read sharing is safe

        # Generate recommendation
        if result.safety == ParallelSafety.SAFE:
            result.recommendation = "Safe to parallelize — no resource conflicts."
        elif result.safety == ParallelSafety.CAUTION:
            result.recommendation = f"Proceed with caution — {'; '.join(result.conflicts)}."
        else:
            result.recommendation = f"Do NOT parallelize — {'; '.join(result.conflicts)}."

        return result

    except Exception as e:
        log.debug("parallel_check_failed", err=str(e)[:100])
        return ParallelCompatibility(
            mission_a=priority_a.mission_id,
            mission_b=priority_b.mission_id,
            safety=ParallelSafety.CAUTION,
            recommendation="Check failed — defaulting to caution.",
        )


# ═══════════════════════════════════════════════════════════════
# PART 3 — RESOURCE CONFLICT DETECTION
# ═══════════════════════════════════════════════════════════════

@dataclass
class ResourceConflict:
    """A detected resource conflict between missions.

    Attributes:
        conflict_type: "file" | "tool" | "environment" | "dependency".
        resource: The contested resource name.
        missions: IDs of missions competing for this resource.
        severity: "low" | "medium" | "high".
        resolution: Suggested resolution strategy.
    """
    conflict_type: str
    resource:      str
    missions:      list[str] = field(default_factory=list)
    severity:      str = "medium"
    resolution:    str = ""

    def to_dict(self) -> dict:
        return {
            "conflict_type": self.conflict_type,
            "resource": self.resource,
            "missions": self.missions,
            "severity": self.severity,
            "resolution": self.resolution,
        }


# Protected files that are high-severity conflicts
_HIGH_CONFLICT_FILES = frozenset({
    "core/meta_orchestrator.py", "core/mission_system.py",
    "core/state.py", "core/contracts.py",
    "config/settings.py", "agents/crew.py",
    "docker-compose.yml", "docker-compose.prod.yml",
    "requirements.txt", ".env",
})

# Environment-level resources (only one mission should modify at a time)
_ENVIRONMENT_RESOURCES = frozenset({
    "docker_daemon", "git_index", "pip_packages",
    "qdrant_collection", "redis_cache",
})


def detect_resource_conflicts(
    missions: list[MissionPriority],
) -> list[ResourceConflict]:
    """
    Detect resource conflicts across multiple concurrent missions.

    Checks:
    1. File modification overlaps
    2. Write-exclusive tool contention
    3. Environment-level resource conflicts
    4. Dependency chain violations

    Returns list of ResourceConflict. Never raises.
    """
    conflicts = []
    try:
        # Build resource usage maps
        file_users: dict[str, list[str]] = defaultdict(list)
        tool_users: dict[str, list[str]] = defaultdict(list)

        for m in missions:
            for res in m.resource_requirements:
                if res in _WRITE_EXCLUSIVE_TOOLS:
                    tool_users[res].append(m.mission_id)
                elif "/" in res or res.endswith(".py") or res.endswith(".json") or res.endswith(".yml"):
                    file_users[res].append(m.mission_id)

        # 1. File conflicts
        for file_path, mission_ids in file_users.items():
            if len(mission_ids) > 1:
                severity = "high" if file_path in _HIGH_CONFLICT_FILES else "medium"
                conflicts.append(ResourceConflict(
                    conflict_type="file",
                    resource=file_path,
                    missions=mission_ids,
                    severity=severity,
                    resolution=f"Serialize missions modifying {file_path}. Execute higher-priority first.",
                ))

        # 2. Tool contention
        for tool, mission_ids in tool_users.items():
            if len(mission_ids) > 1:
                severity = "high" if tool in ("git_push", "docker_restart", "file_delete_safe") else "medium"
                conflicts.append(ResourceConflict(
                    conflict_type="tool",
                    resource=tool,
                    missions=mission_ids,
                    severity=severity,
                    resolution=f"Queue access to {tool}. Only one mission at a time.",
                ))

        # 3. Environment conflicts
        env_users: dict[str, list[str]] = defaultdict(list)
        for m in missions:
            for res in m.resource_requirements:
                if "docker" in res:
                    env_users["docker_daemon"].append(m.mission_id)
                if "git_commit" in res or "git_push" in res:
                    env_users["git_index"].append(m.mission_id)
        for env_res, mission_ids in env_users.items():
            if len(set(mission_ids)) > 1:
                conflicts.append(ResourceConflict(
                    conflict_type="environment",
                    resource=env_res,
                    missions=list(set(mission_ids)),
                    severity="high",
                    resolution=f"Environment resource {env_res} requires exclusive access.",
                ))

        # 4. Dependency violations
        id_set = {m.mission_id for m in missions}
        for m in missions:
            for dep in m.dependencies:
                if dep in id_set:
                    conflicts.append(ResourceConflict(
                        conflict_type="dependency",
                        resource=f"{dep} → {m.mission_id}",
                        missions=[dep, m.mission_id],
                        severity="high",
                        resolution=f"Mission {m.mission_id} depends on {dep}. Execute {dep} first.",
                    ))

    except Exception as e:
        log.debug("conflict_detection_failed", err=str(e)[:100])

    return conflicts


# ═══════════════════════════════════════════════════════════════
# PART 4 — MISSION QUEUE INTELLIGENCE
# ═══════════════════════════════════════════════════════════════

class QueueAction(str, Enum):
    EXECUTE_NOW = "execute_now"  # Start immediately
    DELAY       = "delay"        # Wait for dependency/resource
    SPLIT       = "split"        # Break into smaller missions
    MERGE       = "merge"        # Combine with similar mission
    DEFER       = "defer"        # Explicitly postpone

    @property
    def description(self) -> str:
        return {
            "execute_now": "Start execution immediately",
            "delay": "Wait for dependencies or resources to free",
            "split": "Break mission into smaller independent tasks",
            "merge": "Combine with another mission targeting same resources",
            "defer": "Postpone to a later time (low priority or high risk)",
        }[self.value]


@dataclass
class QueueDecision:
    """Queue scheduling decision for a mission.

    Attributes:
        mission_id: Target mission.
        action: Recommended queue action.
        reason: Why this action was chosen.
        blocked_by: Mission IDs blocking this one (if delayed).
        merge_candidate: ID of mission to merge with (if merge).
        split_suggestions: How to split (if split).
        confidence: 0.0-1.0 confidence in this recommendation.
    """
    mission_id:       str
    action:           QueueAction = QueueAction.EXECUTE_NOW
    reason:           str = ""
    blocked_by:       list[str] = field(default_factory=list)
    merge_candidate:  str = ""
    split_suggestions: list[str] = field(default_factory=list)
    confidence:       float = 0.5

    def to_dict(self) -> dict:
        return {
            "mission_id": self.mission_id,
            "action": self.action.value,
            "action_description": self.action.description,
            "reason": self.reason,
            "blocked_by": self.blocked_by,
            "merge_candidate": self.merge_candidate,
            "split_suggestions": self.split_suggestions,
            "confidence": round(self.confidence, 2),
        }


def suggest_queue_action(
    mission: MissionPriority,
    active_missions: list[MissionPriority] | None = None,
    conflict_map: list[ResourceConflict] | None = None,
) -> QueueDecision:
    """
    Suggest queue scheduling action for a mission.

    Decision heuristics:
    1. No conflicts, no dependencies → EXECUTE_NOW
    2. Blocked by dependency → DELAY
    3. Resource conflict with active mission → DELAY
    4. High risk + high complexity → DEFER (for human review)
    5. EPIC complexity → SPLIT
    6. Same-file target as queued mission → MERGE candidate

    Returns QueueDecision. Never raises.
    """
    try:
        active = active_missions or []
        conflicts = conflict_map or []

        # Filter conflicts for this mission
        my_conflicts = [c for c in conflicts if mission.mission_id in c.missions]
        high_conflicts = [c for c in my_conflicts if c.severity == "high"]

        # 1. Check dependencies
        active_ids = {m.mission_id for m in active}
        unresolved_deps = [d for d in mission.dependencies if d in active_ids]
        if unresolved_deps:
            return QueueDecision(
                mission_id=mission.mission_id,
                action=QueueAction.DELAY,
                reason=f"Blocked by dependencies: {', '.join(unresolved_deps)}",
                blocked_by=unresolved_deps,
                confidence=0.95,
            )

        # 2. Check resource conflicts with active missions
        if high_conflicts:
            blockers = set()
            for c in high_conflicts:
                for mid in c.missions:
                    if mid != mission.mission_id and mid in active_ids:
                        blockers.add(mid)
            if blockers:
                return QueueDecision(
                    mission_id=mission.mission_id,
                    action=QueueAction.DELAY,
                    reason=f"Resource conflict with active missions: {', '.join(c.resource for c in high_conflicts[:3])}",
                    blocked_by=sorted(blockers),
                    confidence=0.85,
                )

        # 3. Deferred urgency
        if mission.urgency == Urgency.DEFERRED:
            return QueueDecision(
                mission_id=mission.mission_id,
                action=QueueAction.DEFER,
                reason="Mission explicitly marked as deferred.",
                confidence=0.90,
            )

        # 4. High risk + high complexity → defer for review
        if mission.risk_level >= 8 and mission.complexity.depth >= 4:
            return QueueDecision(
                mission_id=mission.mission_id,
                action=QueueAction.DEFER,
                reason=f"High risk ({mission.risk_level}/10) + high complexity ({mission.complexity.value}). Recommend human review.",
                confidence=0.75,
            )

        # 5. Epic complexity → suggest split
        if mission.complexity == Complexity.EPIC:
            return QueueDecision(
                mission_id=mission.mission_id,
                action=QueueAction.SPLIT,
                reason="Epic complexity — break into smaller independent tasks.",
                split_suggestions=[
                    "Phase 1: Analysis and planning",
                    "Phase 2: Implementation (per-module)",
                    "Phase 3: Testing and validation",
                    "Phase 4: Integration and review",
                ],
                confidence=0.70,
            )

        # 6. Check for merge candidates
        for active_m in active:
            if active_m.mission_id == mission.mission_id:
                continue
            shared_files = set(mission.resource_requirements) & set(active_m.resource_requirements)
            file_overlap = [f for f in shared_files if "/" in f or f.endswith((".py", ".json"))]
            if len(file_overlap) >= 2:
                return QueueDecision(
                    mission_id=mission.mission_id,
                    action=QueueAction.MERGE,
                    reason=f"Significant file overlap with {active_m.mission_id}: {', '.join(file_overlap[:3])}",
                    merge_candidate=active_m.mission_id,
                    confidence=0.60,
                )

        # 7. Default: execute now
        return QueueDecision(
            mission_id=mission.mission_id,
            action=QueueAction.EXECUTE_NOW,
            reason="No conflicts, dependencies met. Ready to execute.",
            confidence=0.85,
        )

    except Exception as e:
        log.debug("queue_suggestion_failed", err=str(e)[:100])
        return QueueDecision(
            mission_id=mission.mission_id,
            action=QueueAction.DELAY,
            reason=f"Decision failed: {str(e)[:100]}. Defaulting to delay.",
            confidence=0.30,
        )


# ═══════════════════════════════════════════════════════════════
# PART 5 — LONG HORIZON MEMORY
# ═══════════════════════════════════════════════════════════════

@dataclass
class MissionOutcome:
    """Structured record of a mission's outcome for long-term memory.

    Attributes:
        mission_id: Unique mission identifier.
        description: Original mission description.
        intent: Detected intent category.
        status: Final status (done/failed/rejected/blocked).
        duration_s: Total execution time.
        agents_used: List of agents that participated.
        tools_used: List of tools that were called.
        retries: Number of retry attempts.
        fallbacks: Number of fallback activations.
        risk_score: Mission risk score.
        error_category: If failed, the error classification.
        files_modified: Files that were changed.
        timestamp: When the outcome was recorded.
    """
    mission_id:     str
    description:    str = ""
    intent:         str = ""
    status:         str = "unknown"
    duration_s:     float = 0.0
    agents_used:    list[str] = field(default_factory=list)
    tools_used:     list[str] = field(default_factory=list)
    retries:        int = 0
    fallbacks:      int = 0
    risk_score:     int = 0
    error_category: str = ""
    files_modified: list[str] = field(default_factory=list)
    timestamp:      float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "mission_id": self.mission_id,
            "description": self.description[:300],
            "intent": self.intent,
            "status": self.status,
            "duration_s": round(self.duration_s, 1),
            "agents_used": self.agents_used,
            "tools_used": self.tools_used,
            "retries": self.retries,
            "fallbacks": self.fallbacks,
            "risk_score": self.risk_score,
            "error_category": self.error_category,
            "files_modified": self.files_modified,
            "timestamp": self.timestamp,
        }


# Bounded in-memory outcome history
_OUTCOME_HISTORY: list[MissionOutcome] = []
_MAX_HISTORY = 500


def record_mission_outcome(outcome: MissionOutcome) -> None:
    """Record a mission outcome. Bounded buffer, fail-open."""
    try:
        _OUTCOME_HISTORY.append(outcome)
        if len(_OUTCOME_HISTORY) > _MAX_HISTORY:
            del _OUTCOME_HISTORY[:_MAX_HISTORY // 5]
    except Exception:
        pass


def get_mission_history(
    status: str | None = None,
    intent: str | None = None,
    last_n: int = 50,
) -> list[dict]:
    """Retrieve mission outcomes with optional filtering."""
    try:
        results = _OUTCOME_HISTORY[:]
        if status:
            results = [r for r in results if r.status == status]
        if intent:
            results = [r for r in results if r.intent == intent]
        return [r.to_dict() for r in results[-last_n:]][::-1]
    except Exception:
        return []


def get_history_summary() -> dict:
    """Aggregate summary of mission outcome history."""
    try:
        if not _OUTCOME_HISTORY:
            return {"total": 0}
        total = len(_OUTCOME_HISTORY)
        by_status = Counter(o.status for o in _OUTCOME_HISTORY)
        by_intent = Counter(o.intent for o in _OUTCOME_HISTORY)
        avg_duration = sum(o.duration_s for o in _OUTCOME_HISTORY) / total
        total_retries = sum(o.retries for o in _OUTCOME_HISTORY)
        total_fallbacks = sum(o.fallbacks for o in _OUTCOME_HISTORY)

        # Failure patterns
        failure_categories = Counter(
            o.error_category for o in _OUTCOME_HISTORY
            if o.status == "failed" and o.error_category
        )

        # Most modified files
        file_counts = Counter()
        for o in _OUTCOME_HISTORY:
            for f in o.files_modified:
                file_counts[f] += 1

        return {
            "total": total,
            "by_status": dict(by_status),
            "by_intent": dict(by_intent.most_common(10)),
            "avg_duration_s": round(avg_duration, 1),
            "total_retries": total_retries,
            "total_fallbacks": total_fallbacks,
            "success_rate": round(by_status.get("done", 0) / max(total, 1), 3),
            "failure_categories": dict(failure_categories.most_common(5)),
            "most_modified_files": dict(file_counts.most_common(10)),
        }
    except Exception:
        return {"total": len(_OUTCOME_HISTORY)}


def clear_history() -> None:
    """Clear outcome history (for testing)."""
    _OUTCOME_HISTORY.clear()


# ═══════════════════════════════════════════════════════════════
# PART 6 — OUTPUT ARTIFACTS
# ═══════════════════════════════════════════════════════════════

def export_multi_mission_artifacts(output_dir: str = "workspace") -> dict:
    """
    Export multi-mission intelligence artifacts as JSON files.

    Produces:
    - mission_priority_schema.json — priority model definition + examples
    - parallel_execution_rules.json — safety rules + tool classifications
    - resource_conflict_patterns.json — conflict types + resolutions
    - mission_queue_heuristics.json — queue action rules + signals

    Returns {filename: path}. Never raises.
    """
    out = Path(output_dir)
    if not out.is_absolute():
        out = REPO_ROOT / out
    out.mkdir(parents=True, exist_ok=True)
    produced = {}

    # 1. Priority schema
    try:
        schema = {
            "urgency_levels": [
                {"level": u.value, "weight": u.weight, "description": {
                    "critical": "Blocking other work, production issue",
                    "high": "Time-sensitive, user waiting",
                    "medium": "Normal priority",
                    "low": "Background, can wait",
                    "deferred": "Explicitly postponed",
                }.get(u.value, "")}
                for u in Urgency
            ],
            "complexity_levels": [
                {"level": c.value, "depth": c.depth, "description": {
                    "trivial": "Single tool, single step",
                    "simple": "2-3 steps, one agent",
                    "moderate": "Multi-agent, multi-step",
                    "complex": "Deep planning, many agents",
                    "epic": "Multi-cycle, long-running",
                }.get(c.value, "")}
                for c in Complexity
            ],
            "scoring_formula": {
                "urgency_weight": 0.35,
                "risk_factor": 0.20,
                "dependency_factor": 0.15,
                "complexity_factor": 0.15,
                "recency_bonus": 0.15,
            },
            "urgency_signals": {k: v.value for k, v in _URGENCY_SIGNALS.items()},
            "complexity_signals": {k: v.value for k, v in _COMPLEXITY_SIGNALS.items()},
        }
        path = out / "mission_priority_schema.json"
        path.write_text(json.dumps(schema, indent=2, ensure_ascii=False), encoding="utf-8")
        produced["mission_priority_schema.json"] = str(path)
    except Exception as e:
        log.debug("export_priority_failed", err=str(e)[:80])

    # 2. Parallel execution rules
    try:
        rules = {
            "write_exclusive_tools": sorted(_WRITE_EXCLUSIVE_TOOLS),
            "read_safe_tools": sorted(_READ_SAFE_TOOLS),
            "max_parallel_risk": _MAX_PARALLEL_RISK,
            "safety_levels": [
                {"level": "safe", "can_parallelize": True, "description": "No conflicts detected"},
                {"level": "caution", "can_parallelize": True, "description": "Minor overlap, probably safe"},
                {"level": "unsafe", "can_parallelize": False, "description": "Conflicts detected — serialize"},
            ],
            "conflict_checks": [
                "1. Dependency chain detection",
                "2. Write-exclusive tool overlap",
                "3. Target file overlap",
                "4. Combined risk threshold",
                "5. Read-only sharing (always safe)",
            ],
        }
        path = out / "parallel_execution_rules.json"
        path.write_text(json.dumps(rules, indent=2, ensure_ascii=False), encoding="utf-8")
        produced["parallel_execution_rules.json"] = str(path)
    except Exception as e:
        log.debug("export_parallel_failed", err=str(e)[:80])

    # 3. Resource conflict patterns
    try:
        patterns = {
            "conflict_types": [
                {"type": "file", "description": "Multiple missions modifying same file", "severity": "medium-high"},
                {"type": "tool", "description": "Write-exclusive tool contention", "severity": "medium-high"},
                {"type": "environment", "description": "System-level resource (docker, git index)", "severity": "high"},
                {"type": "dependency", "description": "Mission depends on another active mission", "severity": "high"},
            ],
            "high_conflict_files": sorted(_HIGH_CONFLICT_FILES),
            "environment_resources": sorted(_ENVIRONMENT_RESOURCES),
            "resolution_strategies": [
                "Serialize: Execute missions sequentially by priority",
                "Queue: Wait for resource to free, then proceed",
                "Split: Break conflicting mission into non-conflicting parts",
                "Merge: Combine missions targeting same resources",
            ],
        }
        path = out / "resource_conflict_patterns.json"
        path.write_text(json.dumps(patterns, indent=2, ensure_ascii=False), encoding="utf-8")
        produced["resource_conflict_patterns.json"] = str(path)
    except Exception as e:
        log.debug("export_conflicts_failed", err=str(e)[:80])

    # 4. Queue heuristics
    try:
        heuristics = {
            "queue_actions": [
                {"action": a.value, "description": a.description}
                for a in QueueAction
            ],
            "decision_rules": [
                {"priority": 1, "condition": "Unresolved dependencies", "action": "delay"},
                {"priority": 2, "condition": "High resource conflict with active mission", "action": "delay"},
                {"priority": 3, "condition": "Urgency = deferred", "action": "defer"},
                {"priority": 4, "condition": "Risk >= 8 AND complexity >= complex", "action": "defer"},
                {"priority": 5, "condition": "Complexity = epic", "action": "split"},
                {"priority": 6, "condition": "Significant file overlap with queued mission", "action": "merge"},
                {"priority": 7, "condition": "Default (no conflicts)", "action": "execute_now"},
            ],
            "mission_outcome_schema": {
                "fields": [
                    "mission_id", "description", "intent", "status",
                    "duration_s", "agents_used", "tools_used",
                    "retries", "fallbacks", "risk_score",
                    "error_category", "files_modified", "timestamp",
                ],
                "statuses": ["done", "failed", "rejected", "blocked"],
                "buffer_size": _MAX_HISTORY,
            },
        }
        path = out / "mission_queue_heuristics.json"
        path.write_text(json.dumps(heuristics, indent=2, ensure_ascii=False), encoding="utf-8")
        produced["mission_queue_heuristics.json"] = str(path)
    except Exception as e:
        log.debug("export_heuristics_failed", err=str(e)[:80])

    try:
        log.info("multi_mission_artifacts_exported", files=list(produced.keys()))
    except Exception:
        pass

    return produced