"""
JARVIS MAX — LoopGuard (Phase 4)
=================================
Détection et interruption des boucles d'exécution dans les missions.

Protège contre :
    1. Agent qui s'appelle lui-même (auto-delegation loop)
    2. Cycle de délégation (A→B→A→B→...)
    3. Output identique répété (agent bloqué sur même réponse)
    4. Dépassement du nombre max d'itérations par mission

Usage :
    guard = LoopGuard(mission_id="m-001", max_iterations=20)

    for agent in pipeline:
        check = guard.check(agent_id, output_hash)
        if check.is_loop:
            # stop or reroute
            break
        guard.record(agent_id, output)
"""
from __future__ import annotations

import hashlib
import time
from collections import Counter, deque
from dataclasses import dataclass, field
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────────────────

MAX_ITERATIONS_DEFAULT = 20    # max agent calls per mission
MAX_SAME_AGENT_RUNS    = 5     # max consecutive runs of same agent
MAX_OUTPUT_REPEATS     = 3     # same output hash → loop
CYCLE_WINDOW           = 8     # look-back window for cycle detection


# ─────────────────────────────────────────────────────────────────────────────
# LoopCheckResult
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class LoopCheckResult:
    is_loop:       bool  = False
    loop_type:     str   = ""      # "auto_delegation" | "cycle" | "repeated_output" | "max_iterations"
    detail:        str   = ""
    confidence:    float = 0.0     # 0–1: how certain we are it's a loop
    suggested_action: str = ""     # "stop" | "reroute" | "reduce_confidence"


# ─────────────────────────────────────────────────────────────────────────────
# LoopGuard
# ─────────────────────────────────────────────────────────────────────────────

class LoopGuard:
    """
    Détecteur de boucles pour une mission.

    Instancier une fois par mission, appeler check() + record() à chaque agent.
    Thread-safe pour usage concurrent léger.
    """

    def __init__(
        self,
        mission_id:     str,
        max_iterations: int = MAX_ITERATIONS_DEFAULT,
    ):
        self.mission_id     = mission_id
        self.max_iterations = max_iterations

        # History
        self._agent_sequence: deque[str] = deque(maxlen=CYCLE_WINDOW)
        self._output_hashes:  deque[str] = deque(maxlen=MAX_OUTPUT_REPEATS + 2)
        self._agent_counts:   Counter    = Counter()
        self._total_iterations: int      = 0
        self._loop_events:    list[dict] = []

    # ── Hashing ───────────────────────────────────────────────────────────────

    @staticmethod
    def _hash_output(output: str) -> str:
        """Short hash of output for duplicate detection."""
        normalized = output.strip().lower()[:500]
        return hashlib.md5(normalized.encode(), usedforsecurity=False).hexdigest()[:12]

    # ── Public API ────────────────────────────────────────────────────────────

    def record(self, agent_id: str, output: str = "") -> None:
        """
        Record an agent execution. Call AFTER the agent runs.
        """
        self._total_iterations += 1
        self._agent_sequence.append(agent_id)
        self._agent_counts[agent_id] += 1
        if output:
            self._output_hashes.append(self._hash_output(output))

    def check(self, agent_id: str, output: str = "") -> LoopCheckResult:
        """
        Check if running agent_id would create a loop.
        Call BEFORE running the agent.

        Returns LoopCheckResult — is_loop=False means safe to proceed.
        """
        # 1. Max iterations
        if self._total_iterations >= self.max_iterations:
            return LoopCheckResult(
                is_loop        = True,
                loop_type      = "max_iterations",
                detail         = "Mission reached max iterations (%d)" % self.max_iterations,
                confidence     = 1.0,
                suggested_action = "stop",
            )

        # 2. Same agent called too many times
        if self._agent_counts[agent_id] >= MAX_SAME_AGENT_RUNS:
            return LoopCheckResult(
                is_loop        = True,
                loop_type      = "auto_delegation",
                detail         = "%s called %d times (max=%d)" % (
                    agent_id, self._agent_counts[agent_id], MAX_SAME_AGENT_RUNS
                ),
                confidence     = 0.9,
                suggested_action = "reroute",
            )

        # 3. Delegation cycle (A→B→A pattern in recent sequence)
        if len(self._agent_sequence) >= 4:
            seq = list(self._agent_sequence)
            cycle = self._detect_cycle(seq + [agent_id])
            if cycle:
                return LoopCheckResult(
                    is_loop        = True,
                    loop_type      = "cycle",
                    detail         = "Delegation cycle detected: %s" % " -> ".join(cycle),
                    confidence     = 0.85,
                    suggested_action = "reroute",
                )

        # 4. Repeated output (agent stuck)
        if output and len(self._output_hashes) >= MAX_OUTPUT_REPEATS:
            h = self._hash_output(output)
            recent = list(self._output_hashes)[-MAX_OUTPUT_REPEATS:]
            if all(x == h for x in recent):
                return LoopCheckResult(
                    is_loop        = True,
                    loop_type      = "repeated_output",
                    detail         = "Same output repeated %d times (hash=%s)" % (
                        MAX_OUTPUT_REPEATS, h
                    ),
                    confidence     = 0.8,
                    suggested_action = "reduce_confidence",
                )

        return LoopCheckResult(is_loop=False)

    def _detect_cycle(self, seq: list[str]) -> list[str] | None:
        """
        Floyd-style cycle detection in a short sequence.
        Returns the repeating subsequence if found, else None.
        """
        n = len(seq)
        # Check for period-2 and period-3 cycles
        for period in (2, 3):
            if n >= period * 2:
                tail = seq[-period:]
                prev = seq[-(period * 2):-period]
                if tail == prev:
                    return tail
        return None

    def get_stats(self) -> dict:
        """Summary of guard state for logging/debugging."""
        return {
            "mission_id":       self.mission_id,
            "total_iterations": self._total_iterations,
            "max_iterations":   self.max_iterations,
            "agent_counts":     dict(self._agent_counts),
            "recent_sequence":  list(self._agent_sequence),
            "loop_events":      len(self._loop_events),
        }

    def reset(self) -> None:
        """Reset guard state (for mission resume after loop recovery)."""
        self._agent_sequence.clear()
        self._output_hashes.clear()
        self._agent_counts.clear()
        self._total_iterations = 0
