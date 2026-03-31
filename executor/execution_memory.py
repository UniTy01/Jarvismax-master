"""
JARVIS MAX — Execution Memory

Working memory for ongoing missions that prevents repeating failed attempts.

Tracks:
  - What was tried (tool + params)
  - What failed (error + context)
  - What succeeded (result + approach)
  - What changed (files + diffs)

Memory is per-mission and persists across retries/replans.
Helps the orchestrator avoid identical failed attempts.
"""
from __future__ import annotations

import hashlib
import json
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import structlog

log = structlog.get_logger()

_MEMORY_DIR = Path("workspace/.exec_memory")


@dataclass
class AttemptRecord:
    """Record of a single execution attempt."""
    attempt_id: str
    step_name: str
    tool_used: str
    params_hash: str         # Hash of parameters to detect duplicates
    params_summary: str      # Human-readable params summary
    success: bool
    result: str = ""
    error: str = ""
    duration_ms: float = 0
    ts: float = field(default_factory=time.time)
    files_modified: list[str] = field(default_factory=list)


@dataclass
class ExecutionMemory:
    """
    Working memory for a mission's execution history.

    Key features:
    - Deduplication: won't suggest the same failed approach twice
    - Pattern detection: identifies recurring failure patterns
    - Success tracking: knows what worked for similar subtasks
    """
    mission_id: str
    attempts: list[AttemptRecord] = field(default_factory=list)
    failed_hashes: set[str] = field(default_factory=set)
    success_patterns: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))
    context_notes: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    # ── Core Operations ──────────────────────────────────────

    def record_attempt(self, step_name: str, tool: str, params: dict,
                       success: bool, result: str = "", error: str = "",
                       duration_ms: float = 0,
                       files_modified: list[str] | None = None) -> AttemptRecord:
        """Record an execution attempt."""
        params_hash = self._hash_params(tool, params)
        params_summary = f"{tool}({', '.join(f'{k}={str(v)[:30]}' for k, v in list(params.items())[:5])})"

        record = AttemptRecord(
            attempt_id=f"{self.mission_id}_{len(self.attempts)}",
            step_name=step_name,
            tool_used=tool,
            params_hash=params_hash,
            params_summary=params_summary,
            success=success,
            result=result[:1000],
            error=error[:500],
            duration_ms=duration_ms,
            files_modified=files_modified or [],
        )

        self.attempts.append(record)

        if not success:
            self.failed_hashes.add(params_hash)
        else:
            self.success_patterns[step_name].append(params_summary)

        self.save()
        return record

    def was_tried_and_failed(self, tool: str, params: dict) -> bool:
        """Check if this exact tool+params combination was already tried and failed."""
        params_hash = self._hash_params(tool, params)
        return params_hash in self.failed_hashes

    def get_failed_approaches(self, step_name: str = "") -> list[str]:
        """Get human-readable list of failed approaches for a step."""
        failed = [a for a in self.attempts if not a.success]
        if step_name:
            failed = [a for a in failed if a.step_name == step_name]
        return [f"❌ {a.params_summary}: {a.error[:100]}" for a in failed]

    def get_successful_approaches(self, step_name: str = "") -> list[str]:
        """Get approaches that worked for similar steps."""
        succeeded = [a for a in self.attempts if a.success]
        if step_name:
            succeeded = [a for a in succeeded if a.step_name == step_name]
        return [f"✅ {a.params_summary}" for a in succeeded]

    def get_all_files_modified(self) -> list[str]:
        """Get all files modified across all attempts."""
        files = set()
        for a in self.attempts:
            files.update(a.files_modified)
        return sorted(files)

    def add_context_note(self, note: str) -> None:
        """Add a context note (e.g., 'this repo uses pytest', 'main module is core/executor.py')."""
        self.context_notes.append(note)
        self.save()

    # ── Pattern Detection ─────────────────────────────────────

    def detect_failure_pattern(self) -> str | None:
        """
        Detect if there's a recurring failure pattern.

        Returns a description of the pattern, or None.
        """
        if len(self.attempts) < 3:
            return None

        recent = self.attempts[-5:]
        recent_failed = [a for a in recent if not a.success]

        if len(recent_failed) >= 3:
            # Check if same error type
            errors = [a.error[:50] for a in recent_failed]
            if len(set(errors)) == 1:
                return f"Repeated identical error ({len(recent_failed)}x): {errors[0]}"

            # Check if same tool
            tools = [a.tool_used for a in recent_failed]
            if len(set(tools)) == 1:
                return f"Tool '{tools[0]}' failing repeatedly ({len(recent_failed)}x)"

            # Check if same step
            steps = [a.step_name for a in recent_failed]
            if len(set(steps)) == 1:
                return f"Step '{steps[0]}' failing repeatedly ({len(recent_failed)}x)"

        return None

    def should_change_strategy(self) -> bool:
        """
        Heuristic: should we try a fundamentally different approach?

        True if:
        - 3+ consecutive failures
        - Same error repeated
        - No progress in last 5 attempts
        """
        if len(self.attempts) < 3:
            return False

        recent = self.attempts[-3:]
        if all(not a.success for a in recent):
            return True

        return self.detect_failure_pattern() is not None

    def get_summary_for_prompt(self) -> str:
        """
        Generate a concise summary suitable for LLM prompt inclusion.

        Helps the LLM avoid repeating mistakes.
        """
        lines = [f"## Execution Memory ({len(self.attempts)} attempts)"]

        # Context notes
        if self.context_notes:
            lines.append("### Context")
            for note in self.context_notes[-5:]:
                lines.append(f"- {note}")

        # Failed approaches
        failed = self.get_failed_approaches()
        if failed:
            lines.append(f"### Failed Approaches ({len(failed)})")
            for f in failed[-5:]:
                lines.append(f)

        # Successful approaches
        succeeded = self.get_successful_approaches()
        if succeeded:
            lines.append(f"### Successful Approaches ({len(succeeded)})")
            for s in succeeded[-3:]:
                lines.append(s)

        # Pattern warning
        pattern = self.detect_failure_pattern()
        if pattern:
            lines.append(f"\n⚠️ Pattern detected: {pattern}")
            lines.append("→ Consider a different approach.")

        # Files modified
        files = self.get_all_files_modified()
        if files:
            lines.append(f"\n### Files Modified ({len(files)})")
            for f in files[:10]:
                lines.append(f"- {f}")

        return "\n".join(lines)

    # ── Persistence ──────────────────────────────────────────

    def save(self) -> None:
        """Persist to disk."""
        try:
            _MEMORY_DIR.mkdir(parents=True, exist_ok=True)
            path = _MEMORY_DIR / f"{self.mission_id}.json"
            data = {
                "mission_id": self.mission_id,
                "created_at": self.created_at,
                "context_notes": self.context_notes,
                "attempts": [
                    {
                        "attempt_id": a.attempt_id,
                        "step_name": a.step_name,
                        "tool_used": a.tool_used,
                        "params_hash": a.params_hash,
                        "params_summary": a.params_summary,
                        "success": a.success,
                        "result": a.result,
                        "error": a.error,
                        "duration_ms": a.duration_ms,
                        "ts": a.ts,
                        "files_modified": a.files_modified,
                    }
                    for a in self.attempts
                ],
                "failed_hashes": list(self.failed_hashes),
            }
            path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            log.warning("exec_memory_save_failed", mission_id=self.mission_id, err=str(e)[:100])

    @classmethod
    def load(cls, mission_id: str) -> "ExecutionMemory | None":
        """Load from disk."""
        path = _MEMORY_DIR / f"{mission_id}.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            mem = cls(mission_id=data["mission_id"])
            mem.created_at = data.get("created_at", 0)
            mem.context_notes = data.get("context_notes", [])
            mem.failed_hashes = set(data.get("failed_hashes", []))
            for a_data in data.get("attempts", []):
                mem.attempts.append(AttemptRecord(
                    attempt_id=a_data["attempt_id"],
                    step_name=a_data["step_name"],
                    tool_used=a_data["tool_used"],
                    params_hash=a_data["params_hash"],
                    params_summary=a_data["params_summary"],
                    success=a_data["success"],
                    result=a_data.get("result", ""),
                    error=a_data.get("error", ""),
                    duration_ms=a_data.get("duration_ms", 0),
                    ts=a_data.get("ts", 0),
                    files_modified=a_data.get("files_modified", []),
                ))
            return mem
        except Exception as e:
            log.warning("exec_memory_load_failed", mission_id=mission_id, err=str(e)[:100])
            return None

    def clear(self) -> None:
        """Remove memory file."""
        try:
            path = _MEMORY_DIR / f"{self.mission_id}.json"
            if path.exists():
                path.unlink()
        except Exception:
            pass

    # ── Internal ──────────────────────────────────────────────

    @staticmethod
    def _hash_params(tool: str, params: dict) -> str:
        """Create a stable hash for tool+params to detect duplicates."""
        key = json.dumps({"tool": tool, "params": params}, sort_keys=True, default=str)
        return hashlib.sha256(key.encode()).hexdigest()[:16]


# ── Helpers ──────────────────────────────────────────────────

def get_or_create_memory(mission_id: str) -> ExecutionMemory:
    """Load existing memory or create fresh."""
    mem = ExecutionMemory.load(mission_id)
    if mem:
        return mem
    return ExecutionMemory(mission_id=mission_id)
