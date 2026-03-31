"""
memory/memory_decay.py — Memory confidence decay over time.

Inspired by Hermes Agent's bounded memory model.
Unused memories gradually lose confidence, making room for fresh knowledge.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import structlog

log = structlog.get_logger("memory.decay")

# Decay rate: lose 0.01 confidence per day of non-access
_DECAY_PER_DAY = 0.01
# Floor: never decay below this
_MIN_CONFIDENCE = 0.05
# Only decay items older than this (days)
_GRACE_PERIOD_DAYS = 7


def apply_decay(
    path: str,
    *,
    decay_rate: float = _DECAY_PER_DAY,
    min_confidence: float = _MIN_CONFIDENCE,
    grace_days: int = _GRACE_PERIOD_DAYS,
    dry_run: bool = False,
) -> dict:
    """
    Apply confidence decay to a JSONL memory file.

    Items not accessed recently lose confidence gradually.
    High-use items decay slower (use_count bonus).

    Returns stats dict.
    """
    p = Path(path)
    if not p.exists():
        return {"status": "file_not_found"}

    now = time.time()
    grace_cutoff = now - (grace_days * 86400)
    decayed_count = 0
    total = 0
    lines_out = []

    with open(p) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            total += 1
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                lines_out.append(line + "\n")
                continue

            created = item.get("created_at", item.get("ts", now))
            last_access = item.get("last_accessed_at", created)
            confidence = item.get("confidence", 0.5)
            use_count = item.get("use_count", item.get("access_count", 0))

            # Skip items within grace period
            if created > grace_cutoff:
                lines_out.append(json.dumps(item, ensure_ascii=False) + "\n")
                continue

            # Calculate days since last access
            days_unused = max(0, (now - last_access) / 86400)

            # Use count bonus: high-use items decay slower
            effective_rate = decay_rate / (1 + use_count * 0.5)

            # Apply decay
            decay_amount = days_unused * effective_rate
            new_confidence = max(min_confidence, confidence - decay_amount)

            if new_confidence < confidence:
                item["confidence"] = round(new_confidence, 4)
                decayed_count += 1

            lines_out.append(json.dumps(item, ensure_ascii=False) + "\n")

    stats = {
        "total": total,
        "decayed": decayed_count,
        "unchanged": total - decayed_count,
        "path": str(p),
    }

    if not dry_run and decayed_count > 0:
        with open(p, "w") as f:
            f.writelines(lines_out)
        log.info("memory_decay_applied", **stats)
    else:
        log.info("memory_decay_dry_run", **stats)

    return stats
