"""
JARVIS MAX — Execution Checkpoint System

Intermediate state persistence for multi-step missions.
Enables resume-after-crash and partial step recovery.

Architecture:
  ExecutionCheckpoint
  ├── save()        : Persist current step state to disk
  ├── load()        : Restore last checkpoint for a mission
  ├── advance()     : Mark step complete, save next
  ├── get_history() : Full step execution log
  └── clear()       : Remove checkpoints after completion

Storage: JSON files in workspace/.checkpoints/<mission_id>.json
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

import structlog

log = structlog.get_logger()

_CHECKPOINT_DIR = Path("workspace/.checkpoints")


@dataclass
class StepState:
    """State of a single execution step."""
    step_index: int
    step_name: str
    status: str = "pending"          # pending, running, succeeded, failed, skipped
    started_at: float = 0.0
    finished_at: float = 0.0
    result: str = ""
    error: str = ""
    attempt: int = 0
    max_attempts: int = 3
    inputs: dict = field(default_factory=dict)
    outputs: dict = field(default_factory=dict)
    tool_used: str = ""
    files_modified: list = field(default_factory=list)

    @property
    def duration_s(self) -> float:
        if self.started_at and self.finished_at:
            return round(self.finished_at - self.started_at, 3)
        return 0.0


@dataclass
class ExecutionCheckpoint:
    """
    Full checkpoint state for a multi-step mission execution.

    Supports:
    - Step-by-step state tracking
    - Resume from last successful step
    - Failure history for replanning
    - File modification tracking for rollback
    """
    mission_id: str
    plan_description: str = ""
    total_steps: int = 0
    current_step: int = 0
    status: str = "active"           # active, paused, completed, failed, abandoned
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    steps: list[StepState] = field(default_factory=list)
    error_history: list[dict] = field(default_factory=list)
    files_modified: list[str] = field(default_factory=list)
    context: dict = field(default_factory=dict)   # Arbitrary mission context

    # ── Step Management ──────────────────────────────────────────

    def initialize_steps(self, step_names: list[str]) -> None:
        """Set up step tracking from a plan."""
        self.total_steps = len(step_names)
        self.steps = [
            StepState(step_index=i, step_name=name)
            for i, name in enumerate(step_names)
        ]
        self.save()

    def start_step(self, step_index: int, inputs: dict | None = None) -> StepState:
        """Mark a step as running."""
        if step_index >= len(self.steps):
            raise IndexError(f"Step {step_index} out of range (total: {len(self.steps)})")
        step = self.steps[step_index]
        step.status = "running"
        step.started_at = time.time()
        step.attempt += 1
        if inputs:
            step.inputs = inputs
        self.current_step = step_index
        self.updated_at = time.time()
        self.save()
        log.info("checkpoint_step_started",
                 mission_id=self.mission_id,
                 step=step_index,
                 name=step.step_name,
                 attempt=step.attempt)
        return step

    def complete_step(self, step_index: int, result: str = "",
                      outputs: dict | None = None,
                      files_modified: list[str] | None = None) -> None:
        """Mark a step as successfully completed."""
        step = self.steps[step_index]
        step.status = "succeeded"
        step.finished_at = time.time()
        step.result = result[:2000]
        if outputs:
            step.outputs = outputs
        if files_modified:
            step.files_modified = files_modified
            self.files_modified.extend(f for f in files_modified
                                       if f not in self.files_modified)
        self.updated_at = time.time()
        self.save()
        log.info("checkpoint_step_completed",
                 mission_id=self.mission_id,
                 step=step_index,
                 name=step.step_name,
                 duration_s=step.duration_s)

    def fail_step(self, step_index: int, error: str,
                  retryable: bool = True) -> None:
        """Mark a step as failed."""
        step = self.steps[step_index]
        step.status = "failed"
        step.finished_at = time.time()
        step.error = error[:500]
        self.error_history.append({
            "step_index": step_index,
            "step_name": step.step_name,
            "error": error[:500],
            "attempt": step.attempt,
            "retryable": retryable,
            "ts": time.time(),
        })
        self.updated_at = time.time()
        self.save()
        log.warning("checkpoint_step_failed",
                    mission_id=self.mission_id,
                    step=step_index,
                    name=step.step_name,
                    error=error[:100],
                    retryable=retryable,
                    attempt=step.attempt)

    def skip_step(self, step_index: int, reason: str = "") -> None:
        """Skip a step (e.g., not needed after replanning)."""
        step = self.steps[step_index]
        step.status = "skipped"
        step.finished_at = time.time()
        step.result = f"Skipped: {reason}" if reason else "Skipped"
        self.updated_at = time.time()
        self.save()

    # ── Resume Logic ─────────────────────────────────────────────

    def get_resume_point(self) -> int:
        """Find the first non-completed step to resume from."""
        for i, step in enumerate(self.steps):
            if step.status not in ("succeeded", "skipped"):
                return i
        return len(self.steps)  # All complete

    def get_failed_steps(self) -> list[StepState]:
        """Get all steps that failed (for replanning)."""
        return [s for s in self.steps if s.status == "failed"]

    def can_retry_step(self, step_index: int) -> bool:
        """Check if a failed step can be retried."""
        step = self.steps[step_index]
        return step.status == "failed" and step.attempt < step.max_attempts

    def get_completed_outputs(self) -> dict:
        """Collect outputs from all completed steps."""
        result = {}
        for step in self.steps:
            if step.status == "succeeded" and step.outputs:
                result[step.step_name] = step.outputs
        return result

    # ── Status ──────────────────────────────────────────────────

    def is_complete(self) -> bool:
        """Check if all steps are in terminal state."""
        return all(s.status in ("succeeded", "skipped", "failed") for s in self.steps)

    def success_rate(self) -> float:
        """Fraction of steps that succeeded."""
        if not self.steps:
            return 0.0
        succeeded = sum(1 for s in self.steps if s.status == "succeeded")
        return succeeded / len(self.steps)

    def mark_completed(self) -> None:
        self.status = "completed"
        self.updated_at = time.time()
        self.save()

    def mark_failed(self, reason: str = "") -> None:
        self.status = "failed"
        if reason:
            self.error_history.append({
                "step_index": -1,
                "step_name": "mission",
                "error": reason[:500],
                "attempt": 0,
                "retryable": False,
                "ts": time.time(),
            })
        self.updated_at = time.time()
        self.save()

    def mark_abandoned(self) -> None:
        self.status = "abandoned"
        self.updated_at = time.time()
        self.save()

    # ── Persistence ─────────────────────────────────────────────

    def save(self) -> None:
        """Persist checkpoint to disk."""
        try:
            _CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
            path = _CHECKPOINT_DIR / f"{self.mission_id}.json"
            data = {
                "mission_id": self.mission_id,
                "plan_description": self.plan_description,
                "total_steps": self.total_steps,
                "current_step": self.current_step,
                "status": self.status,
                "created_at": self.created_at,
                "updated_at": self.updated_at,
                "steps": [asdict(s) for s in self.steps],
                "error_history": self.error_history,
                "files_modified": self.files_modified,
                "context": self.context,
            }
            path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            log.warning("checkpoint_save_failed",
                        mission_id=self.mission_id, err=str(e)[:100])

    @classmethod
    def load(cls, mission_id: str) -> "ExecutionCheckpoint | None":
        """Load checkpoint from disk, or None if not found."""
        path = _CHECKPOINT_DIR / f"{mission_id}.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            cp = cls(mission_id=data["mission_id"])
            cp.plan_description = data.get("plan_description", "")
            cp.total_steps = data.get("total_steps", 0)
            cp.current_step = data.get("current_step", 0)
            cp.status = data.get("status", "active")
            cp.created_at = data.get("created_at", 0)
            cp.updated_at = data.get("updated_at", 0)
            cp.steps = [
                StepState(**s) for s in data.get("steps", [])
            ]
            cp.error_history = data.get("error_history", [])
            cp.files_modified = data.get("files_modified", [])
            cp.context = data.get("context", {})
            return cp
        except Exception as e:
            log.warning("checkpoint_load_failed",
                        mission_id=mission_id, err=str(e)[:100])
            return None

    def clear(self) -> None:
        """Remove checkpoint file after successful completion."""
        try:
            path = _CHECKPOINT_DIR / f"{self.mission_id}.json"
            if path.exists():
                path.unlink()
        except Exception:
            pass

    # ── Summary ──────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "mission_id": self.mission_id,
            "status": self.status,
            "total_steps": self.total_steps,
            "current_step": self.current_step,
            "completed": sum(1 for s in self.steps if s.status == "succeeded"),
            "failed": sum(1 for s in self.steps if s.status == "failed"),
            "success_rate": round(self.success_rate(), 3),
            "files_modified": self.files_modified,
            "error_count": len(self.error_history),
            "resume_point": self.get_resume_point(),
        }


# ── Helpers ────────────────────────────────────────────────────────────

def get_or_create_checkpoint(mission_id: str,
                             plan_description: str = "",
                             step_names: list[str] | None = None) -> ExecutionCheckpoint:
    """Load existing checkpoint or create new one."""
    cp = ExecutionCheckpoint.load(mission_id)
    if cp is not None:
        log.info("checkpoint_resumed",
                 mission_id=mission_id,
                 resume_point=cp.get_resume_point(),
                 total_steps=cp.total_steps)
        return cp

    cp = ExecutionCheckpoint(mission_id=mission_id,
                             plan_description=plan_description)
    if step_names:
        cp.initialize_steps(step_names)
    return cp


def list_active_checkpoints() -> list[dict]:
    """List all non-completed checkpoints."""
    results = []
    if not _CHECKPOINT_DIR.exists():
        return results
    for f in _CHECKPOINT_DIR.glob("*.json"):
        try:
            cp = ExecutionCheckpoint.load(f.stem)
            if cp and cp.status == "active":
                results.append(cp.to_dict())
        except Exception:
            pass
    return results
