"""
kernel/planning/ — Kernel Planning Layer
=========================================
The kernel is responsible for planning. Goal decomposition and plan generation
live here, not scattered across core/.

KERNEL RULE: This package does NOT import from core/, agents/, api/, tools/.
It defines kernel-level planning interfaces and delegates to core implementations
via the registration pattern (same as policy_adapter.py).

Architecture:
  KernelGoal          — structured goal understood by the kernel
  KernelPlan          — kernel-level plan (steps + metadata)
  KernelPlanStep      — a single step in a kernel plan
  KernelPlanner       — converts goals into plans
  KernelGoalDecomposer — breaks vague goals into structured tasks

Exports:
  from kernel.planning import KernelPlanner, KernelGoal, KernelPlan
"""
from kernel.planning.goal import KernelGoal, KernelPlanStep, KernelPlan
from kernel.planning.planner import KernelPlanner, get_planner

__all__ = [
    "KernelGoal",
    "KernelPlan",
    "KernelPlanStep",
    "KernelPlanner",
    "get_planner",
]
