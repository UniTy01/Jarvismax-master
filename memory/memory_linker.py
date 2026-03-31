"""
memory/memory_linker.py — Link related missions, skills, failures, decisions.

Creates a lightweight graph of relationships between memory items.
Enables: "show me all skills created from missions that failed, then recovered."

Storage: JSONL file (workspace/memory_links.jsonl)
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

import structlog

log = structlog.get_logger("memory.linker")

_LINK_FILE = Path("workspace/memory_links.jsonl")


class LinkType(str, Enum):
    MISSION_CREATED_SKILL = "mission_created_skill"
    MISSION_HAD_FAILURE = "mission_had_failure"
    FAILURE_LED_TO_LESSON = "failure_led_to_lesson"
    SKILL_USED_IN_MISSION = "skill_used_in_mission"
    SKILL_REFINED_BY_MISSION = "skill_refined_by_mission"
    DECISION_IN_MISSION = "decision_in_mission"
    MISSION_SIMILAR_TO = "mission_similar_to"


@dataclass
class MemoryLink:
    source_type: str       # "mission", "skill", "failure", "decision"
    source_id: str
    target_type: str
    target_id: str
    link_type: LinkType
    metadata: dict = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "source_type": self.source_type,
            "source_id": self.source_id,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "link_type": self.link_type.value,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }


class MemoryLinker:
    """Manages links between memory entities."""

    def __init__(self, path: str | Path | None = None):
        self._path = Path(path) if path else _LINK_FILE
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def link(
        self,
        source_type: str,
        source_id: str,
        target_type: str,
        target_id: str,
        link_type: LinkType,
        **metadata,
    ) -> MemoryLink:
        """Create a link between two memory entities."""
        ml = MemoryLink(
            source_type=source_type,
            source_id=source_id,
            target_type=target_type,
            target_id=target_id,
            link_type=link_type,
            metadata=metadata,
        )
        try:
            with open(self._path, "a") as f:
                f.write(json.dumps(ml.to_dict(), ensure_ascii=False) + "\n")
        except Exception as e:
            log.debug("link_write_failed", err=str(e)[:60])
        return ml

    def find_links(
        self,
        entity_id: str,
        link_type: LinkType | None = None,
        direction: str = "both",  # "source", "target", "both"
    ) -> list[dict]:
        """Find all links involving an entity."""
        if not self._path.exists():
            return []
        results = []
        with open(self._path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    item = json.loads(line)
                except json.JSONDecodeError:
                    continue

                match_source = item.get("source_id") == entity_id
                match_target = item.get("target_id") == entity_id

                if direction == "source" and not match_source:
                    continue
                if direction == "target" and not match_target:
                    continue
                if direction == "both" and not (match_source or match_target):
                    continue

                if link_type and item.get("link_type") != link_type.value:
                    continue

                results.append(item)
        return results

    def get_mission_graph(self, mission_id: str) -> dict:
        """Get all linked entities for a mission."""
        links = self.find_links(mission_id)
        return {
            "mission_id": mission_id,
            "skills_created": [l for l in links if l["link_type"] == "mission_created_skill"],
            "failures": [l for l in links if l["link_type"] == "mission_had_failure"],
            "skills_used": [l for l in links if l["link_type"] == "skill_used_in_mission"],
            "decisions": [l for l in links if l["link_type"] == "decision_in_mission"],
            "total_links": len(links),
        }

    def stats(self) -> dict:
        """Get link statistics."""
        if not self._path.exists():
            return {"total": 0}
        counts: dict[str, int] = {}
        total = 0
        with open(self._path) as f:
            for line in f:
                if not line.strip():
                    continue
                total += 1
                try:
                    item = json.loads(line)
                    lt = item.get("link_type", "unknown")
                    counts[lt] = counts.get(lt, 0) + 1
                except json.JSONDecodeError:
                    pass
        return {"total": total, "by_type": counts}
