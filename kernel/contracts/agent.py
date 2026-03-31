"""
kernel/contracts/agent.py — Kernel-level agent contract (Pass 16).

Defines the Protocol every agent must satisfy to be dispatched by the kernel
(R7: agents are replaceable, kernel is the authority).

K1 compliant: zero imports from core/, api/, agents/, tools/.

Usage:
    from kernel.contracts.agent import KernelAgentContract, KernelAgentResult, AgentHealthStatus
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, Protocol, runtime_checkable


# ══════════════════════════════════════════════════════════════════════════════
# Enumerations
# ══════════════════════════════════════════════════════════════════════════════

class AgentHealthStatus(str, Enum):
    """Agent health as seen by the kernel dispatcher."""
    HEALTHY   = "healthy"    # agent is ready and operational
    DEGRADED  = "degraded"   # agent works but with reduced capability
    OVERLOADED = "overloaded" # agent is temporarily saturated
    UNHEALTHY = "unhealthy"  # agent cannot accept new tasks
    UNKNOWN   = "unknown"    # health check not yet performed


class KernelAgentStatus(str, Enum):
    """Outcome status of a KernelAgentResult."""
    SUCCESS  = "success"
    PARTIAL  = "partial"   # partial result, may need retry or downstream fix
    FAILED   = "failed"
    SKIPPED  = "skipped"   # agent opted out (not capable / not applicable)
    TIMEOUT  = "timeout"


# ══════════════════════════════════════════════════════════════════════════════
# KernelAgentTask — input contract
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class KernelAgentTask:
    """
    Input passed by the kernel to any agent.

    The kernel owns task creation; agents must not fabricate tasks for
    themselves (R7: kernel is the authority).
    """
    task_id:    str   = field(default_factory=lambda: f"ktask-{uuid.uuid4().hex[:8]}")
    mission_id: str   = ""
    goal:       str   = ""
    mode:       str   = "auto"          # execution mode hint
    context:    dict  = field(default_factory=dict)
    priority:   int   = 5               # 1 (highest) → 10 (lowest)
    deadline:   float = 0.0             # unix timestamp, 0 = no deadline
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "task_id":    self.task_id,
            "mission_id": self.mission_id,
            "goal":       self.goal,
            "mode":       self.mode,
            "context":    self.context,
            "priority":   self.priority,
            "deadline":   self.deadline,
            "created_at": self.created_at,
        }


# ══════════════════════════════════════════════════════════════════════════════
# KernelAgentResult — output contract
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class KernelAgentResult:
    """
    Kernel-native output produced by any agent after executing a KernelAgentTask.

    Designed to be a minimal, serializable result the kernel can:
      - Log to the cognitive journal
      - Feed into KernelScore / evaluation
      - Persist as a KernelLesson
      - Use for plan step status update
    """
    agent_id:   str   = ""
    task_id:    str   = ""
    mission_id: str   = ""
    status:     KernelAgentStatus = KernelAgentStatus.SUCCESS

    # Core output
    output:     str   = ""             # human-readable result
    confidence: float = 1.0           # 0.0 – 1.0

    # Optional enrichment
    reasoning:  str   = ""            # brief reasoning trace
    metadata:   dict  = field(default_factory=dict)
    error:      Optional[str] = None  # populated if status == FAILED

    # Timing
    started_at:  float = field(default_factory=time.time)
    finished_at: float = 0.0

    def __post_init__(self) -> None:
        if not self.task_id:
            self.task_id = f"ktask-{uuid.uuid4().hex[:8]}"
        if not 0.0 <= self.confidence <= 1.0:
            self.confidence = max(0.0, min(1.0, self.confidence))
        if isinstance(self.status, str):
            try:
                self.status = KernelAgentStatus(self.status)
            except ValueError:
                self.status = KernelAgentStatus.FAILED

    @property
    def duration_ms(self) -> float:
        if self.finished_at and self.started_at:
            return round((self.finished_at - self.started_at) * 1000, 2)
        return 0.0

    @property
    def ok(self) -> bool:
        return self.status in (KernelAgentStatus.SUCCESS, KernelAgentStatus.PARTIAL)

    def to_dict(self) -> dict:
        return {
            "agent_id":    self.agent_id,
            "task_id":     self.task_id,
            "mission_id":  self.mission_id,
            "status":      self.status.value,
            "output":      self.output[:2000] if self.output else "",
            "confidence":  round(self.confidence, 3),
            "reasoning":   self.reasoning[:500] if self.reasoning else "",
            "metadata":    self.metadata,
            "error":       self.error,
            "duration_ms": self.duration_ms,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "KernelAgentResult":
        return cls(
            agent_id=d.get("agent_id", ""),
            task_id=d.get("task_id", ""),
            mission_id=d.get("mission_id", ""),
            status=KernelAgentStatus(d.get("status", "success")),
            output=d.get("output", ""),
            confidence=float(d.get("confidence", 1.0)),
            reasoning=d.get("reasoning", ""),
            metadata=d.get("metadata", {}),
            error=d.get("error"),
        )


# ══════════════════════════════════════════════════════════════════════════════
# KernelAgentContract — Protocol (structural typing)
# ══════════════════════════════════════════════════════════════════════════════

@runtime_checkable
class KernelAgentContract(Protocol):
    """
    Protocol every kernel-dispatchable agent must satisfy (R7).

    Structural typing: agents do NOT have to subclass this Protocol.
    The kernel uses isinstance(agent, KernelAgentContract) to validate
    at registration time.

    Minimum required interface:
        agent_id        — unique identifier for this agent
        capability_type — what the agent specialises in (e.g. "research", "coding")
        execute()       — receive a KernelAgentTask, return KernelAgentResult
        health_check()  — return current AgentHealthStatus (fail-open: UNKNOWN)
    """

    @property
    def agent_id(self) -> str:
        """Unique, stable identifier for this agent instance."""
        ...

    @property
    def capability_type(self) -> str:
        """Capability domain: research | coding | analysis | planning | generic …"""
        ...

    async def execute(
        self,
        task: KernelAgentTask,
        context: Optional[dict] = None,
    ) -> KernelAgentResult:
        """
        Execute the given task and return a kernel-native result.

        Must not raise — catch internal exceptions and return a FAILED result.
        """
        ...

    async def health_check(self) -> AgentHealthStatus:
        """
        Return the current health status of this agent.

        Must be fast (< 200 ms) and never raise.
        Fail-open: return AgentHealthStatus.UNKNOWN if unsure.
        """
        ...


# ══════════════════════════════════════════════════════════════════════════════
# KernelAgentRegistry — lightweight in-memory registry (singleton)
# ══════════════════════════════════════════════════════════════════════════════

class KernelAgentRegistry:
    """
    Tracks agents registered with the kernel at boot.

    Agents register themselves (or are registered by main.py) via:
        registry.register(agent)

    The kernel router queries:
        registry.get(agent_id)
        registry.list_by_capability(capability_type)
        registry.healthy_agents()
    """

    def __init__(self) -> None:
        self._agents: dict[str, Any] = {}  # agent_id → agent instance

    def register(self, agent: Any) -> bool:
        """
        Register an agent if it satisfies KernelAgentContract.

        Returns True on success, False if the agent does not comply.
        """
        if not isinstance(agent, KernelAgentContract):
            return False
        self._agents[agent.agent_id] = agent
        return True

    def get(self, agent_id: str) -> Optional[Any]:
        return self._agents.get(agent_id)

    def list_by_capability(self, capability_type: str) -> list[Any]:
        return [
            a for a in self._agents.values()
            if a.capability_type == capability_type
        ]

    def all_agents(self) -> list[Any]:
        return list(self._agents.values())

    async def healthy_agents(self) -> list[Any]:
        """
        Return agents whose health_check() reports HEALTHY or DEGRADED.

        Calls health_check() on each registered agent concurrently (fail-open).
        BLOC 3: kernel is the authority on agent availability.
        """
        import asyncio

        async def _check(agent: Any) -> tuple[Any, "AgentHealthStatus"]:
            try:
                status = await agent.health_check()
                return agent, status
            except Exception:
                return agent, AgentHealthStatus.UNKNOWN

        if not self._agents:
            return []

        results = await asyncio.gather(*[_check(a) for a in self._agents.values()])
        _ok = {AgentHealthStatus.HEALTHY, AgentHealthStatus.DEGRADED}
        return [agent for agent, status in results if status in _ok]

    async def dispatch(
        self,
        task: "KernelAgentTask",
        capability_type: str = "",
    ) -> "KernelAgentResult":
        """
        Dispatch a KernelAgentTask to the best available agent (BLOC 3 — R7).

        Selection order:
          1. Agents matching capability_type (if provided)
          2. Any healthy agent as fallback
          3. SKIPPED result if no agent available

        Fail-open: always returns a KernelAgentResult, never raises.
        K1-compliant: no imports from core/, agents/, api/.
        """
        _best: Any = None

        # 1. Find by capability_type
        if capability_type:
            candidates = self.list_by_capability(capability_type)
            if candidates:
                _best = candidates[0]

        # 2. Fallback: any registered agent
        if _best is None and self._agents:
            _best = next(iter(self._agents.values()))

        # 3. No agents at all
        if _best is None:
            return KernelAgentResult(
                task_id=task.task_id,
                mission_id=task.mission_id,
                agent_id="none",
                status=KernelAgentStatus.SKIPPED,
                output="",
                reasoning="No agents registered in KernelAgentRegistry",
            )

        # Dispatch
        try:
            return await _best.execute(task)
        except Exception as _e:
            return KernelAgentResult(
                task_id=task.task_id,
                mission_id=task.mission_id,
                agent_id=getattr(_best, "agent_id", "unknown"),
                status=KernelAgentStatus.FAILED,
                output="",
                error=str(_e)[:200],
                reasoning="dispatch() caught exception from agent.execute()",
            )

    def __len__(self) -> int:
        return len(self._agents)

    def __repr__(self) -> str:
        return f"KernelAgentRegistry(agents={list(self._agents.keys())})"


# Module-level singleton
_registry: Optional[KernelAgentRegistry] = None


def get_agent_registry() -> KernelAgentRegistry:
    """Return the module-level KernelAgentRegistry singleton."""
    global _registry
    if _registry is None:
        _registry = KernelAgentRegistry()
    return _registry
