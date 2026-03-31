"""
JARVIS MAX — BackgroundDispatcher
Pool de workers pour exécuter les BackgroundTask de CoreTaskQueue.

Architecture :
    BackgroundDispatcher
    ├── CoreTaskQueue          — source des tâches
    ├── N asyncio workers      — consomment la queue en parallèle
    ├── MetaOrchestrator       — exécute les tâches "conversation"
    └── ws_hub                 — notifications WebSocket (optionnel)

Usage :
    dispatcher = get_dispatcher(settings)
    task_id = await dispatcher.dispatch_background_task(
        name="crawl_web",
        payload={"url": "https://..."},
    )
    task_id = await dispatcher.dispatch_background_conversation(
        mission="Analyse le marché CBD France",
        mission_id="abc123",
    )
    await dispatcher.shutdown()
"""
from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any, Callable, Coroutine

import structlog

from core.task_queue import (
    BackgroundTask,
    CoreTaskQueue,
    TaskState,
    get_core_task_queue,
)

log = structlog.get_logger(__name__)


class BackgroundDispatcher:
    """
    Worker pool that consumes CoreTaskQueue and executes tasks.

    Workers start lazily on first dispatch.
    shutdown() drains the queue or times out after timeout_s seconds.
    """

    def __init__(
        self,
        settings,
        queue:       CoreTaskQueue | None = None,
        concurrency: int                  = 3,
    ):
        self.s           = settings
        self._queue      = queue or get_core_task_queue()
        self._concurrency = concurrency
        self._workers:   list[asyncio.Task] = []
        self._shutdown   = asyncio.Event()
        self._started    = False

    # ── Dispatch helpers ──────────────────────────────────────

    async def dispatch_background_task(
        self,
        name:              str,
        payload:           dict          = None,
        coroutine_factory: Callable[..., Coroutine] | None = None,
        max_retries:       int           = 3,
        base_delay_s:      float         = 1.0,
        max_delay_s:       float         = 60.0,
        mission_id:        str           = "",
    ) -> str:
        """
        Enqueue a generic background task.
        If coroutine_factory is provided it is stored in payload under
        the key 'coroutine_factory' for the worker to call.

        Returns the task UUID.
        """
        p = dict(payload or {})
        if coroutine_factory is not None:
            p["coroutine_factory"] = coroutine_factory

        task = await self._queue.enqueue(
            name         = name,
            payload      = p,
            max_retries  = max_retries,
            base_delay_s = base_delay_s,
            max_delay_s  = max_delay_s,
            mission_id   = mission_id,
            kind         = "task",
        )
        self._ensure_started()
        log.info("dispatcher_task_enqueued", task_id=task.id, name=name)
        return task.id

    async def dispatch_background_conversation(
        self,
        mission:    str,
        mission_id: str               = "",
        mode:       str               = "auto",
        budget:     dict | None       = None,
        max_retries: int              = 1,
    ) -> str:
        """
        Enqueue a full conversation/mission for OrchestratorV2.
        budget dict may contain keys: max_tokens, max_time_s, max_cost_usd.

        Returns the task UUID.
        """
        sid = mission_id or str(uuid.uuid4())
        task = await self._queue.enqueue(
            name         = f"conversation:{sid[:8]}",
            payload      = {
                "mission":    mission,
                "mission_id": sid,
                "mode":       mode,
                "budget":     budget or {},
            },
            max_retries  = max_retries,
            base_delay_s = 2.0,
            max_delay_s  = 30.0,
            mission_id   = sid,
            kind         = "conversation",
        )
        self._ensure_started()
        log.info("dispatcher_conversation_enqueued", task_id=task.id, mission_id=sid)
        return task.id

    # ── Lifecycle ─────────────────────────────────────────────

    def start(self) -> None:
        if self._started:
            return
        self._shutdown.clear()
        for i in range(self._concurrency):
            w = asyncio.ensure_future(self._worker(i))
            self._workers.append(w)
        self._started = True
        log.info("dispatcher_started", workers=self._concurrency)

    def _ensure_started(self) -> None:
        if not self._started:
            self.start()

    async def shutdown(self, timeout_s: float = 30.0) -> None:
        """Signal shutdown and wait for workers to drain."""
        log.info("dispatcher_shutdown_requested", timeout_s=timeout_s)
        self._shutdown.set()
        if self._workers:
            done, pending = await asyncio.wait(self._workers, timeout=timeout_s)
            for p in pending:
                p.cancel()
        self._workers.clear()
        self._started = False
        log.info("dispatcher_shutdown_complete")

    # ── Worker loop ───────────────────────────────────────────

    async def _worker(self, worker_id: int) -> None:
        log.debug("dispatcher_worker_started", id=worker_id)
        while not self._shutdown.is_set():
            task = await self._queue.dequeue(timeout=1.0)
            if task is None:
                continue
            await self._execute(task)
        log.debug("dispatcher_worker_stopped", id=worker_id)

    async def _execute(self, task: BackgroundTask) -> None:
        await self._ws_emit(task.mission_id, "running", task.id, task.name)
        await self._progress(task.id, 0, "Starting…")
        try:
            if task.kind == "conversation":
                result = await self._run_conversation(task)
            else:
                result = await self._run_task(task)

            await self._queue.mark_done(task.id, result=result)
            await self._progress(task.id, 100, "Done")
            await self._ws_emit(task.mission_id, "done", task.id, task.name)
            log.info("dispatcher_task_done", task_id=task.id, name=task.name)

        except Exception as e:
            task.attempts += 1
            err = str(e)[:200]
            log.warning("dispatcher_task_failed",
                        task_id=task.id, name=task.name,
                        attempts=task.attempts, err=err)

            if task.can_retry():
                delay = task.retry_delay()
                log.info("dispatcher_retry_scheduled",
                         task_id=task.id, delay_s=delay, attempts=task.attempts)
                asyncio.ensure_future(self._delayed_requeue(task, delay))
                await self._progress(task.id, 0, f"Retry {task.attempts}/{task.max_retries}…")
                await self._ws_emit(task.mission_id, "retrying", task.id, task.name)
            else:
                await self._queue.mark_failed(task.id, error=err)
                await self._progress_error(task.id, err)
                await self._ws_emit(task.mission_id, "failed", task.id, task.name)

    # ── Task runners ──────────────────────────────────────────

    async def _run_task(self, task: BackgroundTask) -> Any:
        factory = task.payload.get("coroutine_factory")
        if factory is not None and callable(factory):
            coro = factory(task)
            if asyncio.iscoroutine(coro):
                return await coro
            return coro
        # No factory: echo the payload back as result
        return {"echoed": task.payload, "task_id": task.id}

    async def _run_conversation(self, task: BackgroundTask) -> Any:
        # Canonical: MetaOrchestrator
        from core.meta_orchestrator import get_meta_orchestrator
        orch = get_meta_orchestrator()
        session = await orch.run(
            user_input = task.payload["mission"],
            mode       = task.payload.get("mode", "auto"),
            session_id = task.payload.get("mission_id"),
        )
        return getattr(session, "final_report", "")[:2000]

    # ── Retry ─────────────────────────────────────────────────

    async def _delayed_requeue(self, task: BackgroundTask, delay: float) -> None:
        await asyncio.sleep(delay)
        task.updated_at = time.time()
        await self._queue.requeue(task)

    # ── Progress helpers ──────────────────────────────────────

    async def _progress(self, task_id: str, percent: int, message: str = "") -> None:
        try:
            from api.ws_hub import get_hub
            await get_hub().emit_task_progress(task_id, percent, message)
        except Exception as e:
            log.debug("ws_progress_skipped", task=task_id, err=str(e)[:80])

    async def _progress_error(self, task_id: str, error: str) -> None:
        try:
            from api.ws_hub import get_hub
            hub = get_hub()
            await hub.emit_task_progress(task_id, 0, f"ERROR: {error[:120]}")
            # Also push a terminal event to SSE listeners
            import time
            import asyncio as _asyncio
            payload = {"type": "task_failed", "task_id": task_id,
                       "error": error[:200], "ts": time.time()}
            await hub._push_sse(hub._sse_tasks.get(task_id, []), payload)
        except Exception as _exc:
            log.debug("dispatcher_exception", err=str(_exc)[:120], location="dispatcher:255")

    # ── WebSocket notifications ───────────────────────────────

    async def _ws_emit(
        self,
        mission_id: str,
        event:      str,
        task_id:    str,
        task_name:  str,
    ) -> None:
        if not mission_id:
            return
        try:
            from api.ws_hub import get_hub
            hub = get_hub()
            await hub.broadcast_mission(
                mission_id,
                {
                    "type":      "background_task",
                    "event":     event,
                    "task_id":   task_id,
                    "task_name": task_name,
                },
            )
        except Exception:
            pass   # WS hub is optional


# ── Singleton ─────────────────────────────────────────────────

_dispatcher: BackgroundDispatcher | None = None


def get_dispatcher(settings=None, concurrency: int = 3) -> BackgroundDispatcher:
    global _dispatcher
    if _dispatcher is None:
        if settings is None:
            from config.settings import get_settings
            settings = get_settings()
        _dispatcher = BackgroundDispatcher(settings, concurrency=concurrency)
    return _dispatcher
