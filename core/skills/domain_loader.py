"""
core/skills/domain_loader.py — Load domain skills from filesystem.

Scans business/skills/ for skill directories and loads them.
Thread-safe singleton registry.
"""
from __future__ import annotations

import os
import threading
import structlog
from pathlib import Path

from core.skills.domain_schema import DomainSkill

log = structlog.get_logger("skills.domain_loader")

_SKILL_DIRS = [
    Path(os.path.dirname(__file__)).parent.parent / "business" / "skills",
]


class DomainSkillRegistry:
    """Registry of loaded domain skills."""

    def __init__(self):
        self._lock = threading.Lock()
        self._skills: dict[str, DomainSkill] = {}
        self._loaded = False

    def load_all(self) -> int:
        """Scan skill directories and load all valid skills."""
        count = 0
        for base_dir in _SKILL_DIRS:
            if not base_dir.is_dir():
                continue
            for entry in sorted(base_dir.iterdir()):
                if not entry.is_dir():
                    continue
                skill_json = entry / "skill.json"
                if not skill_json.is_file():
                    continue
                try:
                    skill = DomainSkill.from_directory(entry)
                    with self._lock:
                        self._skills[skill.id] = skill
                    count += 1
                except Exception as e:
                    log.warning("skill_load_failed", path=str(entry), err=str(e)[:100])
        self._loaded = True
        log.info("domain_skills_loaded", count=count)
        return count

    def get(self, skill_id: str) -> DomainSkill | None:
        if not self._loaded:
            self.load_all()
        with self._lock:
            return self._skills.get(skill_id)

    def list_all(self) -> list[DomainSkill]:
        if not self._loaded:
            self.load_all()
        with self._lock:
            return list(self._skills.values())

    def list_by_domain(self, domain: str) -> list[DomainSkill]:
        return [s for s in self.list_all() if s.domain == domain]

    def get_chain(self, skill_ids: list[str]) -> list[DomainSkill]:
        """Get an ordered list of skills for chaining."""
        result = []
        for sid in skill_ids:
            skill = self.get(sid)
            if skill:
                result.append(skill)
        return result

    def stats(self) -> dict:
        skills = self.list_all()
        domains = {}
        for s in skills:
            domains[s.domain] = domains.get(s.domain, 0) + 1
        return {
            "total": len(skills),
            "by_domain": domains,
            "loaded": self._loaded,
        }


# Singleton
_registry: DomainSkillRegistry | None = None
_lock = threading.Lock()


def get_domain_registry() -> DomainSkillRegistry:
    global _registry
    if _registry is None:
        with _lock:
            if _registry is None:
                _registry = DomainSkillRegistry()
    return _registry
