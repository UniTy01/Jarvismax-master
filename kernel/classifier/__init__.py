"""
kernel/classifier/ — Kernel Mission Classification
====================================================
The kernel classifies every mission before execution.
Classification is deterministic, pure logic, zero LLM calls.

The kernel owns classification because:
- It determines risk level → policy check
- It determines complexity → planning depth
- It determines task type → capability routing
- It determines needs_approval → human gating

KERNEL RULE: No imports from core/, agents/, api/, tools/.
core/orchestration/mission_classifier.py registers itself here.

Usage:
  from kernel.classifier import get_classifier, KernelClassification
  clf = get_classifier()
  result = clf.classify("build a REST API with JWT authentication")
"""
from kernel.classifier.mission_classifier import (
    KernelClassifier,
    KernelClassification,
    KernelTaskType,
    KernelComplexity,
    KernelRisk,
    get_classifier,
    register_core_classifier,
)

__all__ = [
    "KernelClassifier",
    "KernelClassification",
    "KernelTaskType",
    "KernelComplexity",
    "KernelRisk",
    "get_classifier",
    "register_core_classifier",
]
