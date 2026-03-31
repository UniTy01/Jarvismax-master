"""
JARVIS MAX — Scheduler: ScheduledTask + NightScheduler with task management.

Trigger types:
  - "manual"          : never auto-due, requires explicit run_now
  - "interval N"      : due when last_run was more than N seconds ago
  - "cron HH:MM"      : due when current UTC time is within ±90s of HH:MM
"""
from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Any

import structlog

log = structlog.get_logger()


class ScheduledTask:
    """A single scheduled task with trigger logic."""

    def __init__(self, config: dict):
        self.id: str = config.get("id", str(uuid.uuid4())[:12])
        self.name: str = config.get("name", "unnamed")
        self.trigger: str = config.get("trigger", "manual")
        self.action: str = config.get("action", "")
        self.enabled: bool = config.get("enabled", True)
        self.last_run: float = config.get("last_run", 0)
        self.payload: dict = config.get("payload", {})

    def is_due(self) -> bool:
        """Check if this task should run now."""
        if not self.enabled:
            return False

        trigger = self.trigger.strip().lower()

        # Manual: never auto-due
        if trigger == "manual":
            return False

        # Interval N: due if last_run was more than N seconds ago
        if trigger.startswith("interval"):
            parts = trigger.split()
            if len(parts) < 2:
                return False
            try:
                interval_s = float(parts[1])
            except ValueError:
                return False
            return (time.time() - self.last_run) >= interval_s

        # Cron HH:MM: due if current UTC time is within ±90s of HH:MM
        if trigger.startswith("cron"):
            parts = trigger.split()
            if len(parts) < 2:
                return False
            time_str = parts[1]
            try:
                hh, mm = map(int, time_str.split(":"))
            except (ValueError, AttributeError):
                return False
            now_utc = datetime.now(timezone.utc)
            target_s = hh * 3600 + mm * 60
            now_s = now_utc.hour * 3600 + now_utc.minute * 60 + now_utc.second
            diff = abs(now_s - target_s)
            # Handle midnight wrap
            if diff > 43200:
                diff = 86400 - diff
            return diff <= 90

        return False

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "trigger": self.trigger,
            "action": self.action,
            "enabled": self.enabled,
            "last_run": self.last_run,
        }


class NightScheduler:
    """
    Task-based scheduler with add/remove/list + integration with
    night_worker.scheduler.NightScheduler for cycle execution.
    """

    def __init__(self, settings: Any = None):
        self._settings = settings
        self._tasks: dict[str, ScheduledTask] = {}

    def add_task(self, config: dict) -> str:
        """Add a scheduled task. Returns the task ID."""
        task = ScheduledTask(config)
        if not task.id or task.id in self._tasks:
            task.id = str(uuid.uuid4())[:12]
        self._tasks[task.id] = task
        log.info("scheduler_task_added", task_id=task.id, name=task.name,
                 trigger=task.trigger)
        return task.id

    def remove_task(self, task_id: str) -> bool:
        """Remove a task by ID. Returns True if found and removed."""
        if task_id in self._tasks:
            del self._tasks[task_id]
            log.info("scheduler_task_removed", task_id=task_id)
            return True
        return False

    def list_tasks(self) -> list[dict]:
        """List all scheduled tasks."""
        return [t.to_dict() for t in self._tasks.values()]

    def get_due_tasks(self) -> list[ScheduledTask]:
        """Return all tasks that are currently due."""
        return [t for t in self._tasks.values() if t.is_due()]

    def mark_run(self, task_id: str) -> None:
        """Mark a task as just-run (update last_run timestamp)."""
        task = self._tasks.get(task_id)
        if task:
            task.last_run = time.time()
