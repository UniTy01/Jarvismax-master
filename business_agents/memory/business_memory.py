"""
JARVIS MAX — Business Agent Memory
=====================================
Bounded, typed memory for business agents.

4 scopes:
  - agent_local_memory: agent-specific working state
  - client_context_memory: customer context and history
  - business_profile_memory: business info, pricing, services
  - reusable_response_memory: validated answers and templates

All memory is JSON-backed, bounded, and per-agent isolated.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class MemoryEntry:
    """Single memory entry."""
    key: str
    value: Any
    scope: str
    agent_id: str
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    access_count: int = 0
    ttl_seconds: float = 0    # 0 = no expiry

    @property
    def expired(self) -> bool:
        if self.ttl_seconds <= 0:
            return False
        return (time.time() - self.updated_at) > self.ttl_seconds


# Scope limits
_SCOPE_LIMITS: dict[str, int] = {
    "agent_local_memory": 100,
    "client_context_memory": 500,
    "business_profile_memory": 50,
    "reusable_response_memory": 200,
}


class BusinessMemory:
    """
    Bounded, typed memory store for a business agent.

    Isolated per agent_id. JSON file backed.
    """

    def __init__(self, agent_id: str, storage_dir: Path | None = None):
        self.agent_id = agent_id
        self._dir = (storage_dir or Path("workspace/business_data/memory")) / agent_id
        self._entries: dict[str, dict[str, MemoryEntry]] = {
            "agent_local_memory": {},
            "client_context_memory": {},
            "business_profile_memory": {},
            "reusable_response_memory": {},
        }
        self._load()

    def store(self, scope: str, key: str, value: Any,
              ttl_seconds: float = 0) -> bool:
        """Store a value in the specified scope."""
        if scope not in self._entries:
            return False

        limit = _SCOPE_LIMITS.get(scope, 100)
        scope_data = self._entries[scope]

        # Check bounds
        if key not in scope_data and len(scope_data) >= limit:
            # Evict oldest entry
            oldest_key = min(scope_data, key=lambda k: scope_data[k].updated_at)
            del scope_data[oldest_key]

        if key in scope_data:
            entry = scope_data[key]
            entry.value = value
            entry.updated_at = time.time()
        else:
            scope_data[key] = MemoryEntry(
                key=key, value=value, scope=scope,
                agent_id=self.agent_id, ttl_seconds=ttl_seconds,
            )

        self._save()
        return True

    def retrieve(self, scope: str, key: str) -> Any | None:
        """Retrieve a value from the specified scope."""
        if scope not in self._entries:
            return None
        entry = self._entries[scope].get(key)
        if entry is None:
            return None
        if entry.expired:
            del self._entries[scope][key]
            return None
        entry.access_count += 1
        return entry.value

    def search(self, scope: str, query: str, limit: int = 10) -> list[dict]:
        """Search entries in a scope by keyword matching."""
        if scope not in self._entries:
            return []
        results = []
        query_lower = query.lower()
        for entry in self._entries[scope].values():
            if entry.expired:
                continue
            # Match against key and stringified value
            text = f"{entry.key} {json.dumps(entry.value, default=str)}".lower()
            if query_lower in text:
                results.append({
                    "key": entry.key,
                    "value": entry.value,
                    "scope": entry.scope,
                    "updated_at": entry.updated_at,
                })
        return results[:limit]

    def list_scope(self, scope: str) -> list[dict]:
        """List all entries in a scope."""
        if scope not in self._entries:
            return []
        self._cleanup_expired(scope)
        return [
            {"key": e.key, "value": e.value, "updated_at": e.updated_at,
             "access_count": e.access_count}
            for e in self._entries[scope].values()
        ]

    def delete(self, scope: str, key: str) -> bool:
        if scope in self._entries and key in self._entries[scope]:
            del self._entries[scope][key]
            self._save()
            return True
        return False

    def get_stats(self) -> dict:
        """Memory usage stats."""
        stats = {}
        for scope, entries in self._entries.items():
            self._cleanup_expired(scope)
            limit = _SCOPE_LIMITS.get(scope, 100)
            stats[scope] = {
                "count": len(entries),
                "limit": limit,
                "usage_pct": round(len(entries) / limit * 100, 1) if limit > 0 else 0,
            }
        return {"agent_id": self.agent_id, "scopes": stats}

    def _cleanup_expired(self, scope: str) -> None:
        expired_keys = [k for k, e in self._entries[scope].items() if e.expired]
        for k in expired_keys:
            del self._entries[scope][k]

    def _save(self) -> None:
        try:
            self._dir.mkdir(parents=True, exist_ok=True)
            for scope, entries in self._entries.items():
                path = self._dir / f"{scope}.json"
                data = []
                for e in entries.values():
                    data.append({
                        "key": e.key, "value": e.value, "scope": e.scope,
                        "agent_id": e.agent_id, "created_at": e.created_at,
                        "updated_at": e.updated_at, "access_count": e.access_count,
                        "ttl_seconds": e.ttl_seconds,
                    })
                path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        except Exception:
            pass

    def _load(self) -> None:
        if not self._dir.exists():
            return
        for scope in self._entries:
            path = self._dir / f"{scope}.json"
            if path.exists():
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    for entry_data in data:
                        e = MemoryEntry(**{k: v for k, v in entry_data.items()
                                           if k in MemoryEntry.__dataclass_fields__})
                        if not e.expired:
                            self._entries[scope][e.key] = e
                except Exception:
                    pass
