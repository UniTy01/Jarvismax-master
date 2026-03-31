"""
kernel/learning/lesson.py — Kernel-level lesson data contract.

Pure data type. No imports from core/, agents/, api/, tools/.
KernelLesson is the canonical representation of what the kernel
learned from a mission — fed by KernelScore (Pass 8) not re-derived
from raw metadata.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field


@dataclass
class KernelLesson:
    """
    A lesson the kernel extracted from a completed mission.

    Fields come directly from KernelScore (Pass 8):
      - verdict          : "accept" | "low_confidence" | "retry_suggested" | "empty"
      - confidence       : float 0-1 (from reflection > critique > heuristic)
      - weaknesses       : list[str] from critique
      - improvement_suggestion : str from critique
      - what_to_do_differently : synthesized by kernel (not re-derived in core)

    Goal: single kernel-native lesson record that drives both:
      - MemoryFacade.store_failure() (immediate lesson storage)
      - future kernel.improve() trigger
    """
    mission_id:              str
    goal_summary:            str
    what_happened:           str
    what_to_do_differently:  str
    confidence:              float
    verdict:                 str        = "accept"
    weaknesses:              list[str]  = field(default_factory=list)
    improvement_suggestion:  str        = ""
    created_at:              float      = field(default_factory=time.time)
    lesson_id:               str        = field(default_factory=lambda: uuid.uuid4().hex[:12])

    def to_dict(self) -> dict:
        return {
            "lesson_id":             self.lesson_id,
            "mission_id":            self.mission_id,
            "goal_summary":          self.goal_summary,
            "what_happened":         self.what_happened,
            "what_to_do_differently": self.what_to_do_differently,
            "confidence":            self.confidence,
            "verdict":               self.verdict,
            "weaknesses":            self.weaknesses,
            "improvement_suggestion": self.improvement_suggestion,
            "created_at":            self.created_at,
        }

    def to_core_lesson_dict(self) -> dict:
        """
        Backward-compatible dict for core.orchestration.learning_loop.store_lesson.
        Matches the fields store_lesson uses via memory_facade.store_failure().
        """
        return {
            "mission_id":            self.mission_id,
            "goal_summary":          self.goal_summary,
            "what_happened":         self.what_happened,
            "what_to_do_differently": self.what_to_do_differently,
            "confidence":            self.confidence,
        }
