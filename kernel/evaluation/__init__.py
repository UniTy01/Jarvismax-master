"""
kernel/evaluation/ — Kernel Outcome Evaluation
===============================================
The kernel evaluates every mission result before it is returned.

Evaluation feeds back into:
  - kernel/capabilities/performance.py  (provider reliability)
  - kernel/improvement/gate.py          (failure history)
  - kernel/memory/                      (store lessons)

KERNEL RULE: Zero imports from core/.

Usage:
  from kernel.evaluation import get_evaluator, KernelScore
  score = get_evaluator().evaluate(goal, result, task_type="implementation")
"""
from kernel.evaluation.scorer import (
    KernelEvaluator,
    KernelScore,
    get_evaluator,
    register_core_evaluator,
    register_core_reflection,
    register_core_critique,
    register_skill_evaluator,
    register_agent_evaluator,
    register_improvement_scorer,
)

__all__ = [
    "KernelEvaluator",
    "KernelScore",
    "get_evaluator",
    "register_core_evaluator",
    "register_core_reflection",
    "register_core_critique",
    "register_skill_evaluator",
    "register_agent_evaluator",
    "register_improvement_scorer",
]
