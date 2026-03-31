"""
memory/memory_ranker.py — Rank retrieved memories by usefulness.

Combines:
- text similarity (word overlap cosine)
- recency boost
- confidence weight
- access frequency signal
"""
from __future__ import annotations

import math
import re
import time
from collections import Counter
from typing import Any


def _tokenize(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) >= 2]


def _cosine(a: Counter, b: Counter) -> float:
    if not a or not b:
        return 0.0
    common = set(a) & set(b)
    dot = sum(a[w] * b[w] for w in common)
    ma = math.sqrt(sum(v * v for v in a.values()))
    mb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (ma * mb) if ma and mb else 0.0


def rank_memories(
    query: str,
    items: list[Any],
    *,
    top_k: int = 5,
    min_score: float = 0.1,
    recency_weight: float = 0.1,
    confidence_weight: float = 0.1,
) -> list[tuple[Any, float]]:
    """
    Rank memory items by relevance to a query.

    Items must have .content (str) and optionally .confidence (float),
    .created_at (float), .access_count (int).

    Returns list of (item, score) sorted descending.
    """
    query_tokens = Counter(_tokenize(query))
    if not query_tokens:
        return []

    now = time.time()
    scored = []

    for item in items:
        content = getattr(item, "content", str(item))
        item_tokens = Counter(_tokenize(content))

        # Text similarity (0-1)
        sim = _cosine(query_tokens, item_tokens)

        # Confidence boost (0 to confidence_weight)
        confidence = getattr(item, "confidence", 0.5)
        conf_boost = confidence * confidence_weight

        # Recency boost (0 to recency_weight, decays over 30 days)
        created = getattr(item, "created_at", now)
        age_days = max(0, (now - created) / 86400)
        recency = max(0, 1 - age_days / 30) * recency_weight

        score = sim + conf_boost + recency

        if score >= min_score:
            scored.append((item, round(score, 4)))

    scored.sort(key=lambda x: -x[1])
    return scored[:top_k]
