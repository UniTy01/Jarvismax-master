"""
core/skills/skill_service.py — Unified skill system facade.

Single entry point for all skill operations.
Wired into MetaOrchestrator for retrieval and post-mission creation.
"""
from __future__ import annotations

import structlog
from typing import Optional

from core.skills.skill_models import Skill
from core.skills.skill_registry import SkillRegistry
from core.skills.skill_retriever import SkillRetriever
from core.skills.skill_builder import SkillBuilder

log = structlog.get_logger("skills.service")

_DEFAULT_STORE = "workspace/skills.jsonl"


class SkillService:
    """
    Facade for the skill system.

    Provides:
    - retrieve_for_mission(): get relevant skills before execution
    - record_outcome(): maybe create a skill after execution
    - list/search/inspect for API access
    """

    def __init__(self, store_path: str = _DEFAULT_STORE):
        self._registry = SkillRegistry(path=store_path)
        self._retriever = SkillRetriever(self._registry)
        self._builder = SkillBuilder(self._registry)

    # ── Pre-execution: retrieve ─────────────────────────────────

    def retrieve_for_mission(
        self,
        goal: str,
        top_k: int = 3,
        min_score: float = 0.15,
    ) -> list[dict]:
        """
        Retrieve relevant skills for a mission goal.
        Returns planning-ready dicts. Safe to call always (returns [] on empty).
        """
        return self._retriever.retrieve_for_planning(
            goal, top_k=top_k, min_score=min_score
        )

    # ── Post-execution: record ──────────────────────────────────

    def record_outcome(
        self,
        mission_id: str,
        goal: str,
        result: str,
        status: str,
        tools_used: list[str] | None = None,
        agents_used: list[str] | None = None,
        steps_taken: list[str] | None = None,
        risk_level: str = "low",
        confidence: float = 0.6,
    ) -> Optional[Skill]:
        """
        Evaluate a completed mission and maybe create a skill.
        Returns the Skill if created/updated, None otherwise.
        """
        return self._builder.maybe_create(
            mission_id=mission_id,
            goal=goal,
            result=result,
            status=status,
            tools_used=tools_used,
            agents_used=agents_used,
            steps_taken=steps_taken,
            risk_level=risk_level,
            confidence=confidence,
        )

    def record_skill_use(self, skill_id: str, success: bool = True) -> None:
        """Record that a skill was used (updates use_count, success_count)."""
        skill = self._registry.get(skill_id)
        if skill:
            skill.record_use(success)
            self._registry.update(skill)

    # ── Query / inspect ─────────────────────────────────────────

    def refine_skill(
        self,
        skill_id: str,
        new_result: str,
        success: bool = True,
        new_steps: list[str] | None = None,
    ) -> bool:
        """
        Refine a skill based on reuse outcome (Hermes-inspired).
        When reused successfully: boost confidence, update steps.
        When reuse failed: reduce confidence slightly.
        """
        skill = self._registry.get(skill_id)
        if not skill:
            return False

        skill.record_use(success)

        if success:
            skill.confidence = round(
                skill.confidence + (1.0 - skill.confidence) * 0.1, 3
            )
            if new_steps:
                from core.skills.skill_models import SkillStep
                skill.steps = [
                    SkillStep(order=i + 1, description=s)
                    for i, s in enumerate(new_steps)
                ]
            log.info("skill_refined",
                     id=skill_id, confidence=skill.confidence,
                     use_count=skill.use_count)
        else:
            skill.confidence = round(max(0.1, skill.confidence - 0.05), 3)
            log.info("skill_degraded",
                     id=skill_id, confidence=skill.confidence)

        self._registry.update(skill)
        return True

    def list_skills(self, limit: int = 50) -> list[dict]:
        """List all skills as dicts."""
        skills = self._registry.all()
        skills.sort(key=lambda s: -s.updated_at)
        return [s.to_dict() for s in skills[:limit]]

    def get_skill(self, skill_id: str) -> Optional[dict]:
        """Get one skill by ID."""
        s = self._registry.get(skill_id)
        return s.to_dict() if s else None

    def search_skills(self, query: str, top_k: int = 5) -> list[dict]:
        """Search skills by text similarity."""
        results = self._retriever.retrieve(query, top_k=top_k)
        return [
            {**skill.to_dict(), "_relevance": score}
            for skill, score in results
        ]

    def stats(self) -> dict:
        """Skill system statistics."""
        skills = self._registry.all()
        return {
            "total": len(skills),
            "by_problem_type": _count_by(skills, "problem_type"),
            "by_risk_level": _count_by(skills, "risk_level"),
            "avg_confidence": (
                round(sum(s.confidence for s in skills) / len(skills), 3)
                if skills else 0
            ),
            "total_uses": sum(s.use_count for s in skills),
        }

    def delete_skill(self, skill_id: str) -> bool:
        return self._registry.delete(skill_id)


def _count_by(skills: list[Skill], attr: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for s in skills:
        val = getattr(s, attr, "unknown")
        counts[val] = counts.get(val, 0) + 1
    return counts


# ── Singleton ────────────────────────────────────────────────────

_service: SkillService | None = None


def get_skill_service() -> SkillService:
    global _service
    if _service is None:
        _service = SkillService()
        log.info("skill_service_initialized", skills=_service.stats()["total"])
    return _service
