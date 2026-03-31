"""
JARVIS MAX v3 — Background Job Manager
Permet de lancer des tâches asynchrones qui peuvent injecter des Observations 
directement dans l'EventStream sans bloquer la boucle de décision principale.
"""
import asyncio
import uuid
import structlog
from typing import Any, Callable, Coroutine
from datetime import datetime

log = structlog.get_logger()

class BackgroundJob:
    """Représente une tâche de fond (ex: Recherche, Scan de sécurité, Tests)."""
    def __init__(self, name: str, mission_id: str, coro: Coroutine):
        self.job_id = f"job-{uuid.uuid4().hex[:6]}"
        self.name = name
        self.mission_id = mission_id
        self.coro = coro
        self.status = "pending"
        self.started_at = None
        self.finished_at = None
        self._task = None

    async def run(self, on_observation: Callable[[Any], Coroutine]):
        """Exécute la coroutine et gère le cycle de vie."""
        self.status = "running"
        self.started_at = datetime.now()
        log.info("background_job_started", job_id=self.job_id, name=self.name)
        
        try:
            # On passe une fonction de callback pour émettre des observations au stream
            result = await self.coro
            self.status = "completed"
            log.info("background_job_finished", job_id=self.job_id, name=self.name)
            return result
        except asyncio.CancelledError:
            self.status = "cancelled"
            log.warning("background_job_cancelled", job_id=self.job_id)
        except Exception as e:
            self.status = "failed"
            log.error("background_job_failed", job_id=self.job_id, err=str(e))
            raise
        finally:
            self.finished_at = datetime.now()

class HiveMindManager:
    """Orchestrateur des tâches parallèles."""
    def __init__(self, event_stream: Any):
        self.event_stream = event_stream
        self.active_jobs = {}

    def spawn(self, name: str, mission_id: str, coro: Coroutine):
        """Lance une nouvelle tâche de fond."""
        job = BackgroundJob(name, mission_id, coro)
        task = asyncio.create_task(self._run_wrapper(job))
        self.active_jobs[job.job_id] = job
        return job.job_id

    async def _run_wrapper(self, job: BackgroundJob):
        try:
            await job.run(on_observation=self.emit_observation)
        finally:
            if job.job_id in self.active_jobs:
                del self.active_jobs[job.job_id]

    async def emit_observation(self, observation: Any):
        """Injecte une observation asynchrone dans le stream global."""
        await self.event_stream.add_event(observation)
        log.debug("hive_mind_observation_injected", type=type(observation).__name__)

    def stop_all(self):
        """Arrête brutalement tout le swarm (fin de mission)."""
        for job_id, job in self.active_jobs.items():
            if job._task:
                job._task.cancel()
        self.active_jobs.clear()
