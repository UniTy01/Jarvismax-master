"""
kernel/improvement/ — Kernel Improvement Gating
=================================================
The kernel controls when self-improvement is allowed.
No improvement cycle can start without the kernel's approval.

KERNEL RULE: Zero imports from core/.

Usage:
  from kernel.improvement import get_gate, ImprovementDecision
  gate = get_gate()
  decision = gate.check()
  if decision.allowed:
      run_improvement_cycle()
"""
from kernel.improvement.gate import (
    ImprovementGate,
    ImprovementDecision,
    get_gate,
    register_history_provider,
)

__all__ = [
    "ImprovementGate",
    "ImprovementDecision",
    "get_gate",
    "register_history_provider",
]
