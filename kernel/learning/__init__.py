"""
kernel/learning/ — Kernel Learning Layer
=========================================
The kernel closes the cognitive loop after each mission:

  kernel.evaluate() → KernelScore → kernel.learn(score) → KernelLesson stored

KERNEL RULE: This package does NOT import from core/, agents/, api/, tools/.
Core lesson storage registers itself via register_lesson_store().

Architecture:
  KernelLesson  — canonical lesson data type (verdict, confidence, weaknesses,
                  improvement_suggestion from KernelScore)
  KernelLearner — decides when to learn, extracts lesson, stores via registration
  register_lesson_store — registration slot for core.orchestration.learning_loop.store_lesson

Exports:
  from kernel.learning import KernelLearner, KernelLesson, get_learner, register_lesson_store
"""
from kernel.learning.lesson import KernelLesson
from kernel.learning.learner import KernelLearner, get_learner, register_lesson_store

__all__ = [
    "KernelLesson",
    "KernelLearner",
    "get_learner",
    "register_lesson_store",
]
