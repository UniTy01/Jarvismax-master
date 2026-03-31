"""
JARVIS MAX v3 — Autonomous Loop
Boucle ininfinie ReAct (Reasoning and Acting) liant le DevinAgent, 
l'EventStream, et le Sandbox (Terminal/Éditeur) de manière asynchrone.
"""
import asyncio
import structlog
from pathlib import Path

from core.event_stream import EventStream
from core.events import (
    Action, Observation, FinishAction, DelegateAction,
    TerminalAction, TerminalObservation,
    FileReadAction, FileObservation,
    FileWriteAction, FileEditAction,
    BrowserNavigateAction, BrowserObservation,
    SaveMemoryAction, PythonExecuteAction, PythonObservation,
    BackgroundAction, BackgroundObservation
)
from core.repo_map import get_repo_map
# Lazy imports — these modules may not be present in all deployments
try:
    from executor.desktop_env.sandbox import DockerSandbox, LocalFallbackSandbox
    from executor.desktop_env.terminal import PersistentTerminal
    from executor.desktop_env.editor import SurgicalEditor
    from executor.desktop_env.browser import WebSurfer
except ImportError:
    DockerSandbox = LocalFallbackSandbox = None  # type: ignore
    PersistentTerminal = SurgicalEditor = WebSurfer = None  # type: ignore

try:
    from agents.autonomous.devin_agent import DevinAgent
except ImportError:
    DevinAgent = None  # type: ignore

try:
    from core.background_job import HiveMindManager
except ImportError:
    HiveMindManager = None  # type: ignore

try:
    from core.validator import MissionValidator
except ImportError:
    MissionValidator = None  # type: ignore

log = structlog.get_logger()

# ── EventEmitter (fail-open) ──────────────────────────────────
try:
    from api.event_emitter import (
        emit_mission_created, emit_mission_completed, emit_mission_aborted,
        emit_agent_started, emit_agent_result, emit_agent_failed,
    )
    _EMIT_AVAILABLE = True
except ImportError:
    _EMIT_AVAILABLE = False
    def emit_mission_created(*a, **kw): pass
    def emit_mission_completed(*a, **kw): pass
    def emit_mission_aborted(*a, **kw): pass
    def emit_agent_started(*a, **kw): pass
    def emit_agent_result(*a, **kw): pass
    def emit_agent_failed(*a, **kw): pass

# ── OrchestrationGuard (fail-open) ────────────────────────────
try:
    from core.orchestration_guard import get_guard as _get_guard
    _USE_GUARD = True
except ImportError:
    _USE_GUARD = False

class AutonomousLoop:
    """Orchestre la boucle de l'agent autonome."""
    
    def __init__(self, mission_id: str, workspace_path: str, max_steps: int = 50):
        self.mission_id = mission_id
        self.workspace_path = workspace_path
        self.max_steps = max_steps
        self.stream = EventStream(mission_id)
        
        # Détection Sandbox
        self.sandbox = DockerSandbox(workspace_path)
        if not self.sandbox.is_available():
            log.warning("docker_unavailable_using_local_fallback")
            self.sandbox = LocalFallbackSandbox(workspace_path)
            
        self.terminal = PersistentTerminal(self.sandbox)
        self.editor = SurgicalEditor(workspace_path)
        self.browser = WebSurfer()
        self.agent = DevinAgent()
        self.hive_mind = HiveMindManager(self.stream) # Phase 13
        self.validator = MissionValidator(self.terminal) # Phase 14

    async def run(self, initial_instruction: str) -> bool:
        """Démarre la mission et boucle jusqu'au succès, l'échec ou le max_steps."""
        # Resolve agent role from AI OS
        _agent_role = "operator"
        try:
            from core.agents.role_definitions import role_for_agent
            _agent_role = role_for_agent(getattr(self, "agent_name", "unknown"))
        except Exception:
            pass
        log.info("autonomous_loop_starting", mission=self.mission_id, role=_agent_role)
        try:
            emit_mission_created(self.mission_id, initial_instruction)
        except Exception as e:
            log.debug("emit_mission_created_skipped", err=str(e)[:80])

        # Init Sandbox
        await self.terminal.start()
        
        # Injecte l'instruction utilisateur initiale
        await self.stream.append(
            Action(
                action_type="start_mission", 
                reasoning=f"Objectif : {initial_instruction}"
            )
        )
        
        step = 0
        success = False
        
        try:
            while step < self.max_steps:
                step += 1
                log.info("agent_loop_step", step=step, max=self.max_steps)
                
                # Contextualisation : la carte du code (Aider-style)
                repo_map = get_repo_map(self.workspace_path)
                
                # 1. THINK & ACT
                action = await self.agent.decide_next_action(self.stream, repo_map)
                await self.stream.append(action)
                
                # Condition de sortie
                if isinstance(action, FinishAction):
                    if action.success:
                        # Phase 14 : Auto-Healing / Validation avant de quitter
                        valid, report = await self.validator.validate()
                        if not valid:
                            log.warning("auto_healing_triggered", reason=report[:100])
                            await self.stream.append(
                                Observation(
                                    content=f"⚠️ AUTO-HEALING : Ta mission semblait finie mais les tests ont échoué.\n{report}\nCorrige ces erreurs avant de retenter de finir.",
                                    is_error=True
                                )
                            )
                            continue # On ne sort pas de la boucle !
                        
                        success = True
                        log.info("agent_loop_finished_with_validation", summary=action.summary)
                        try:
                            emit_mission_completed(self.mission_id, action.summary)
                        except Exception as e:
                            log.debug("emit_mission_completed_skipped", err=str(e)[:80])
                    else:
                        success = False
                        log.info("agent_loop_aborted", summary=action.summary)
                        try:
                            emit_mission_aborted(self.mission_id, action.summary)
                        except Exception as e:
                            log.debug("emit_mission_aborted_skipped", err=str(e)[:80])
                    break
                    
                # 2. OBSERVE
                observation = await self._execute_action(action)
                await self.stream.append(observation)
                
            else:
                log.warning("agent_loop_max_steps_reached", steps=step)
                await self.stream.append(
                    Observation(content="Timeout : Nombre maximal d'étapes atteint.", is_error=True)
                )
                try:
                    emit_mission_aborted(self.mission_id, f"max_steps_reached ({step})")
                except Exception as e:
                    log.debug("emit_mission_aborted_skipped", err=str(e)[:80])
                
        finally:
            # Teardown
            self.hive_mind.stop_all() # Arrête les jobs de fond
            self.terminal.close()
            self.sandbox.stop()
            
        return success

    async def _execute_action(self, action: Action) -> Observation:
        """Exécute l'action demandée par le LLM."""
        try:
            if isinstance(action, TerminalAction):
                exit_code, out = await self.terminal.execute(action.command)
                return TerminalObservation(
                    content=out, 
                    exit_code=exit_code, 
                    is_error=(exit_code != 0)
                )
                
            elif isinstance(action, FileReadAction):
                content = self.editor.read_file(action.file_path, action.start_line, action.end_line)
                is_error = content.startswith("❌")
                return FileObservation(content=content, file_path=action.file_path, is_error=is_error)
                
            elif isinstance(action, FileWriteAction):
                res = self.editor.write_file(action.file_path, action.content)
                return FileObservation(content=res, file_path=action.file_path, is_error=res.startswith("❌"))
                
            elif isinstance(action, FileEditAction):
                res = self.editor.edit_file(action.file_path, action.old_content, action.new_content)
                return FileObservation(content=res, file_path=action.file_path, is_error=res.startswith("❌"))
                
            elif isinstance(action, DelegateAction):
                # Pont entre Agent Loop v3 et le registre des agents v2 (DebugAgent, RecoveryAgent, etc.)
                try:
                    from agents.crew import AgentCrew
                    from config.settings import get_settings
                    from core.state import JarvisSession
                    
                    crew = AgentCrew(get_settings())
                    if action.agent_name not in crew.registry:
                        return Observation(content=f"❌ Erreur: Agent {action.agent_name} inconnu.", is_error=True)
                        
                    log.info("agent_loop_delegate", target=action.agent_name, task=action.task[:50])
                    try:
                        emit_agent_started(self.mission_id, action.agent_name)
                    except Exception as e:
                        log.debug("emit_agent_started_skipped", err=str(e)[:80])

                    # Sub-session proxy
                    sub_session = JarvisSession(
                        session_id=f"sub-{self.mission_id}-{action.agent_name}",
                        user_input=action.task,
                        mode="auto"
                    )
                    sub_session.mission_summary = action.task

                    # Canonical: MetaOrchestrator
                    from core.meta_orchestrator import get_meta_orchestrator
                    orch = get_meta_orchestrator()
                    _last_err = None
                    _max_retries = 2
                    for _attempt in range(_max_retries + 1):
                        try:
                            await orch.agents.run(action.agent_name, sub_session)
                            _last_err = None
                            break
                        except Exception as _e:
                            _last_err = _e
                            if _attempt < _max_retries:
                                await asyncio.sleep(0.5 * (2 ** _attempt))
                    if _last_err is not None:
                        raise _last_err

                    res = sub_session.get_output(action.agent_name)
                    try:
                        emit_agent_result(self.mission_id, action.agent_name, res[:3000] if res else "done")
                    except Exception as e:
                        log.debug("emit_agent_result_skipped", err=str(e)[:80])
                    return Observation(content=f"✅ Délégation à {action.agent_name} achevée.\nOutput:\n{res}")
                except Exception as e:
                    try:
                        emit_agent_failed(self.mission_id, action.agent_name, str(e))
                    except Exception as e2:
                        log.debug("emit_agent_failed_skipped", err=str(e2)[:80])
                    return Observation(content=f"❌ Échec de la délégation: {str(e)}", is_error=True)
                
            elif isinstance(action, BrowserNavigateAction):
                res = self.browser.navigate(action.url)
                return BrowserObservation(content=res, url=action.url, is_error=res.startswith("❌"))
                
            elif isinstance(action, SaveMemoryAction):
                self.agent.memory_bank.add_lesson(action.problem_context, action.successful_solution)
                return Observation(content="✅ Leçon mémorisée dans la mémoire épisodique.")
                
            elif isinstance(action, PythonExecuteAction):
                import uuid
                tmp = f".jarvis_tmp_{uuid.uuid4().hex[:6]}.py"
                self.editor.write_file(tmp, action.code)
                exit_code, out = await self.terminal.execute(f"python {tmp}")
                # We could delete it, but keeping it is harmless and allows debugging
                return PythonObservation(content=out, exit_code=exit_code, is_error=(exit_code != 0))
            
            elif isinstance(action, BackgroundAction):
                # Phase 13 : Lancement d'un job asynchrone (Hive Mind)
                async def scout_routine():
                    # Cet agent va tourner en arrière-plan sans bloquer la boucle principale
                    from agents.autonomous.scout_agent import ScoutResearcher
                    scout = ScoutResearcher()
                    
                    await self.hive_mind.emit_observation(
                        BackgroundObservation(
                            job_id="start", job_name=action.job_name, 
                            status="running", content=f"Agent Scout lancé sur : {action.task_description}"
                        )
                    )
                    
                    # Logique de recherche réelle via WebSurfer
                    result = await scout.research(action.task_description, self.browser)
                    
                    await self.hive_mind.emit_observation(
                        BackgroundObservation(
                            job_id="end", job_name=action.job_name, 
                            status="completed", content=f"Résultat Scout pour '{action.job_name}':\n{result}"
                        )
                    )
                
                self.hive_mind.spawn(action.job_name, self.mission_id, scout_routine())
                return Observation(content=f"🚀 Système Hive Mind : Agent Scout '{action.job_name}' déployé en arrière-plan.")
                
            return Observation(
                content=f"❌ Type d'action non géré ou invalide: {type(action).__name__}", 
                is_error=True
            )
        except Exception as e:
            log.error("action_execution_failed", err=str(e)[:100])
            return Observation(content=f"❌ Crash interne lors de l'exécution: {str(e)}", is_error=True)
