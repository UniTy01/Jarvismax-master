"""
memory/memory_compactor.py — Prune and compact memory to avoid noisy growth.

Strategies:
1. TTL-based expiry (working memory, old low-confidence items)
2. Dedup (merge near-identical entries)
3. Summarize repeated patterns
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import structlog

log = structlog.get_logger("memory.compactor")

# Working memory expires after 24 hours
_WORKING_TTL = 86400
# Low-confidence items expire after 7 days
_LOW_CONFIDENCE_TTL = 7 * 86400
_LOW_CONFIDENCE_THRESHOLD = 0.3


def compact_jsonl(
    path: str,
    *,
    max_age_days: int = 30,
    min_confidence: float = 0.2,
    dry_run: bool = False,
) -> dict:
    """
    Compact a JSONL memory file.

    Removes:
    - entries older than max_age_days with low confidence
    - working memory entries older than 24h
    - entries with empty content

    Returns stats dict.
    """
    p = Path(path)
    if not p.exists():
        return {"status": "file_not_found"}

    now = time.time()
    cutoff = now - (max_age_days * 86400)
    working_cutoff = now - _WORKING_TTL

    kept = []
    removed = 0
    total = 0

    with open(p) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            total += 1
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                removed += 1
                continue

            content = item.get("content", "")
            created = item.get("created_at", item.get("ts", now))
            confidence = item.get("confidence", 0.5)
            mem_type = item.get("memory_type", item.get("content_type", ""))

            # Remove empty
            if not content or not content.strip():
                removed += 1
                continue

            # Remove expired working memory
            if mem_type == "working" and created < working_cutoff:
                removed += 1
                continue

            # Remove old low-confidence items
            if confidence < min_confidence and created < cutoff:
                removed += 1
                continue

            kept.append(line + "\n")

    stats = {
        "total": total,
        "kept": len(kept),
        "removed": removed,
        "path": str(p),
    }

    if not dry_run and removed > 0:
        with open(p, "w") as f:
            f.writelines(kept)
        log.info("memory_compacted", **stats)
    else:
        log.info("memory_compact_dry_run", **stats)

    return stats


def compact_all(workspace: str = "workspace", dry_run: bool = False) -> dict:
    """Compact all JSONL memory files in workspace."""
    ws = Path(workspace)
    results = {}
    for jsonl in ws.glob("*.jsonl"):
        results[jsonl.name] = compact_jsonl(str(jsonl), dry_run=dry_run)
    return results
