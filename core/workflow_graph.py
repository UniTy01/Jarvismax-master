"""
JARVIS MAX — Workflow Graph (LangGraph Phase 4b)
StateGraph pour l'orchestration des missions avec human-in-loop.

États du workflow :
    PLANNING          → Analyse de la mission, routing
    SHADOW_CHECK      → ShadowAdvisor évalue le risque
    AWAITING_APPROVAL → Pause (interrupt) si risque élevé
    EXECUTING         → Exécution de la mission
    DONE / FAILED     → États terminaux

Human-in-loop :
    Déclenché quand ShadowGate retourne :
      - decision = IMPROVE (risque moyen → avertissement)
      - score < SCORE_WARN_THRESHOLD (5.5)
    NB : NO-GO → FAILED immédiat (pas d'approbation possible)

Reprise :
    workflow.approve(mission_id, "approved")   → EXECUTING
    workflow.approve(mission_id, "rejected")   → FAILED

API :
    POST /api/v2/missions/{id}/approve
    POST /api/v2/missions/{id}/reject
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, TypedDict

import structlog

log = structlog.get_logger()

# ── Imports LangGraph ──────────────────────────────────────────────────────────
try:
    from langgraph.graph import StateGraph, START, END
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.types import interrupt, Command
    _LANGGRAPH_OK = True
except ImportError:
    _LANGGRAPH_OK = False
    log.warning("workflow_graph_no_langgraph", hint="pip install langgraph")


# ══════════════════════════════════════════════════════════════════════════════
# ÉTAT DU WORKFLOW
# ══════════════════════════════════════════════════════════════════════════════

class WorkflowStage(str, Enum):
    PLANNING          = "PLANNING"
    SHADOW_CHECK      = "SHADOW_CHECK"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    EXECUTING         = "EXECUTING"
    DONE              = "DONE"
    FAILED            = "FAILED"


class MissionWorkflowState(TypedDict):
    """État partagé entre tous les nœuds du workflow."""
    mission_id:       str
    mission_text:     str
    intent:           str            # MissionIntent détectée
    mode:             str            # TaskMode routée
    stage:            str            # WorkflowStage courant
    requires_approval: bool          # True si interrupt() doit être déclenché
    approval_status:  Optional[str]  # "approved" | "rejected" | None
    gate_decision:    str            # GO | IMPROVE | NO-GO | UNKNOWN
    gate_score:       float          # score ShadowAdvisor
    gate_reason:      str            # raison lisible
    execution_result: Optional[str]  # résumé d'exécution
    error:            Optional[str]  # message d'erreur si FAILED
    created_at:       float          # timestamp unix


# ══════════════════════════════════════════════════════════════════════════════
# NŒUDS DU GRAPHE
# ══════════════════════════════════════════════════════════════════════════════

def _plan_node(state: MissionWorkflowState) -> dict:
    """
    Nœud PLANNING : détecte l'intention et le mode de traitement.
    Aucun LLM requis — analyse regex rapide.
    """
    log.info("workflow_plan_node", mission_id=state["mission_id"])

    from core.mission_system import detect_intent
    from core.task_router import TaskRouter

    intent   = detect_intent(state["mission_text"]).value
    decision = TaskRouter().route(state["mission_text"])
    # RoutingDecision has a .mode attribute (TaskMode enum)
    mode = decision.mode.value if hasattr(decision, "mode") else str(decision)

    return {
        "intent": intent,
        "mode":   mode,
        "stage":  WorkflowStage.SHADOW_CHECK.value,
    }


def _shadow_check_node(state: MissionWorkflowState) -> dict:
    """
    Nœud SHADOW_CHECK : ShadowGate évalue le risque de la mission.
    Construit une session minimale pour passer par la gate.
    """
    log.info("workflow_shadow_check", mission_id=state["mission_id"])

    try:
        from core.shadow_gate import ShadowGate, SCORE_WARN_THRESHOLD

        # Session minimale — pas d'appel LLM ici, on évalue le texte brut
        # La gate reçoit un report_dict synthétique basé sur les heuristiques
        gate = ShadowGate()

        # Construction d'un report heuristique sans LLM
        # (le vrai ShadowAdvisor LLM intervient dans l'orchestrateur)
        report = _build_heuristic_report(state["mission_text"], state["intent"])
        gate_result = gate.check_advisory(report)

        decision = gate_result.decision.upper()
        score    = gate_result.score
        reason   = gate_result.reason

        # Logique d'approbation :
        # NO-GO   → FAILED immédiat
        # IMPROVE → interrupt() si score < seuil
        # GO      → exécution directe
        if not gate_result.allowed:
            # Bloqué définitivement
            return {
                "gate_decision":    decision,
                "gate_score":       score,
                "gate_reason":      reason,
                "requires_approval": False,
                "stage":            WorkflowStage.FAILED.value,
                "error":            f"Mission bloquée par ShadowGate : {reason}",
            }

        requires_approval = (
            decision == "IMPROVE"
            or score < SCORE_WARN_THRESHOLD
        )

        next_stage = (
            WorkflowStage.AWAITING_APPROVAL.value
            if requires_approval
            else WorkflowStage.EXECUTING.value
        )

        return {
            "gate_decision":    decision,
            "gate_score":       score,
            "gate_reason":      reason,
            "requires_approval": requires_approval,
            "stage":            next_stage,
        }

    except Exception as exc:
        log.warning("workflow_shadow_check_error", err=str(exc)[:80])
        # Fail-open : on continue sans bloquer
        return {
            "gate_decision":    "UNKNOWN",
            "gate_score":       7.0,
            "gate_reason":      f"Erreur shadow check (fail-open) : {exc}",
            "requires_approval": False,
            "stage":            WorkflowStage.EXECUTING.value,
        }


def _approval_gate_node(state: MissionWorkflowState) -> dict:
    """
    Nœud AWAITING_APPROVAL : interrupt() si approbation humaine requise.
    Bloque l'exécution jusqu'à approve() / reject().
    """
    if not state.get("requires_approval"):
        return {"approval_status": "approved", "stage": WorkflowStage.EXECUTING.value}

    log.info(
        "workflow_approval_interrupt",
        mission_id=state["mission_id"],
        gate_decision=state["gate_decision"],
        gate_score=state["gate_score"],
    )

    # interrupt() suspend le graphe ici et attend Command(resume=...)
    decision = interrupt({
        "mission_id":   state["mission_id"],
        "mission_text": state["mission_text"][:200],
        "gate_decision": state["gate_decision"],
        "gate_score":   state["gate_score"],
        "gate_reason":  state["gate_reason"],
        "message":      (
            f"Mission risquée (score {state['gate_score']:.1f}/10, "
            f"décision: {state['gate_decision']}). "
            "Approuver pour continuer, rejeter pour annuler."
        ),
    })

    approval = str(decision).lower()
    if approval in ("approved", "approve", "yes", "oui", "go"):
        log.info("workflow_approved", mission_id=state["mission_id"])
        return {"approval_status": "approved", "stage": WorkflowStage.EXECUTING.value}
    else:
        log.info("workflow_rejected", mission_id=state["mission_id"], decision=approval)
        return {
            "approval_status": "rejected",
            "stage":           WorkflowStage.FAILED.value,
            "error":           f"Mission rejetée par l'opérateur : {decision}",
        }


def _execute_node(state: MissionWorkflowState) -> dict:
    """
    Nœud EXECUTING : délègue à l'ActionQueue / MissionSystem.
    Enregistre la mission pour exécution asynchrone par l'orchestrateur.
    """
    log.info("workflow_execute", mission_id=state["mission_id"])

    try:
        from core.mission_system import get_mission_system
        ms = get_mission_system()

        # Soumettre la mission au MissionSystem standard
        result = ms.submit(
            text=state["mission_text"],
            mission_id=state["mission_id"],
        )

        summary = getattr(result, "summary", str(result))
        return {
            "execution_result": summary,
            "stage":            WorkflowStage.DONE.value,
        }

    except Exception as exc:
        log.error("workflow_execute_error", err=str(exc), mission_id=state["mission_id"])
        return {
            "stage": WorkflowStage.FAILED.value,
            "error": f"Erreur d'exécution : {exc}",
        }


def _finalize_node(state: MissionWorkflowState) -> dict:
    """Nœud terminal : log le résultat final."""
    stage = state.get("stage", WorkflowStage.DONE.value)
    log.info(
        "workflow_finalized",
        mission_id=state["mission_id"],
        stage=stage,
        result=str(state.get("execution_result", ""))[:100],
        error=state.get("error"),
    )
    return {"stage": stage}


# ── Heuristique de risque sans LLM ───────────────────────────────────────────

_HIGH_RISK_KEYWORDS = [
    "supprime", "delete", "drop", "rm -rf", "format", "wipe",
    "production", "prod", "live", "override", "overwrite", "force push",
    "password", "secret", "token", "api key", "credential",
    "firewall", "port", "expose", "public",
]

_MEDIUM_RISK_KEYWORDS = [
    "modifie", "update", "change", "edit", "patch", "refactor",
    "deploy", "déploie", "migrate", "migration",
]


def _build_heuristic_report(text: str, intent: str) -> dict:
    """
    Rapport risque heuristique sans appel LLM.
    Score entre 4.0 (risqué) et 8.5 (sûr).
    """
    lower = text.lower()
    high_hits   = sum(1 for kw in _HIGH_RISK_KEYWORDS   if kw in lower)
    medium_hits = sum(1 for kw in _MEDIUM_RISK_KEYWORDS if kw in lower)

    if high_hits >= 2:
        score    = 3.0
        decision = "NO-GO"
        reason   = f"Mots-clés à haut risque détectés ({high_hits}) : action bloquée"
    elif high_hits == 1:
        score    = 4.5
        decision = "IMPROVE"
        reason   = f"Mot-clé à haut risque détecté : validation requise"
    elif medium_hits >= 2:
        score    = 5.0
        decision = "IMPROVE"
        reason   = f"Opération modificatrice détectée ({medium_hits} indicateurs)"
    else:
        score    = 8.0
        decision = "GO"
        reason   = "Aucun indicateur de risque détecté"

    return {
        "decision":    decision,
        "final_score": score,
        "reason":      reason,
    }


# ══════════════════════════════════════════════════════════════════════════════
# ROUTAGE CONDITIONNEL
# ══════════════════════════════════════════════════════════════════════════════

def _route_after_shadow(state: MissionWorkflowState) -> str:
    """Décide du nœud suivant après shadow_check."""
    stage = state.get("stage", "")
    if stage == WorkflowStage.FAILED.value:
        return "finalize"
    if state.get("requires_approval"):
        return "approval_gate"
    return "execute"


def _route_after_approval(state: MissionWorkflowState) -> str:
    """Décide du nœud suivant après approval_gate."""
    if state.get("approval_status") == "rejected":
        return "finalize"
    return "execute"


# ══════════════════════════════════════════════════════════════════════════════
# WORKFLOW GRAPH — Singleton
# ══════════════════════════════════════════════════════════════════════════════

_WORKFLOW_INSTANCE: Optional["WorkflowGraph"] = None
_WORKFLOW_LOCK = threading.Lock()


def get_workflow_graph() -> "WorkflowGraph":
    """Retourne le singleton WorkflowGraph."""
    global _WORKFLOW_INSTANCE
    with _WORKFLOW_LOCK:
        if _WORKFLOW_INSTANCE is None:
            _WORKFLOW_INSTANCE = WorkflowGraph()
        return _WORKFLOW_INSTANCE


@dataclass
class MissionWorkflowResult:
    """Résultat d'une exécution de workflow."""
    mission_id:      str
    stage:           str
    gate_decision:   str    = "UNKNOWN"
    gate_score:      float  = 0.0
    approval_status: str    = "n/a"
    execution_result: str   = ""
    error:           str    = ""
    interrupted:     bool   = False   # True si en attente d'approbation

    def is_done(self)     -> bool: return self.stage == WorkflowStage.DONE.value
    def is_failed(self)   -> bool: return self.stage == WorkflowStage.FAILED.value
    def needs_approval(self) -> bool: return self.interrupted


class WorkflowGraph:
    """
    Graphe de workflow LangGraph pour les missions JarvisMax.

    Usage :
        wf = get_workflow_graph()

        # Soumettre une mission
        result = wf.run_mission("Analyse le code Python et propose des améliorations")
        if result.needs_approval():
            # L'opérateur doit approuver via API
            wf.approve(result.mission_id, "approved")

        # Ou rejeter
        wf.approve(result.mission_id, "rejected")
    """

    def __init__(self):
        self._checkpointer = None
        self._graph        = None
        self._interrupts: dict[str, dict] = {}  # mission_id → interrupt payload
        self._lock = threading.Lock()

        if _LANGGRAPH_OK:
            self._checkpointer = MemorySaver()
            self._graph = self._build_graph()
            log.info("workflow_graph_ready")
        else:
            log.warning("workflow_graph_disabled", reason="langgraph not installed")

    # ── Graphe ────────────────────────────────────────────────────────────────

    def _build_graph(self):
        """Construit et compile le StateGraph LangGraph."""
        builder = StateGraph(MissionWorkflowState)

        # Nœuds
        builder.add_node("plan",          _plan_node)
        builder.add_node("shadow_check",  _shadow_check_node)
        builder.add_node("approval_gate", _approval_gate_node)
        builder.add_node("execute",       _execute_node)
        builder.add_node("finalize",      _finalize_node)

        # Edges
        builder.add_edge(START,           "plan")
        builder.add_edge("plan",          "shadow_check")

        builder.add_conditional_edges(
            "shadow_check",
            _route_after_shadow,
            {
                "approval_gate": "approval_gate",
                "execute":       "execute",
                "finalize":      "finalize",
            },
        )

        builder.add_conditional_edges(
            "approval_gate",
            _route_after_approval,
            {
                "execute":  "execute",
                "finalize": "finalize",
            },
        )

        builder.add_edge("execute",  "finalize")
        builder.add_edge("finalize", END)

        return builder.compile(
            checkpointer=self._checkpointer,
            interrupt_before=["approval_gate"],
        )

    # ── API publique ──────────────────────────────────────────────────────────

    def run_mission(
        self,
        text:       str,
        mission_id: str | None = None,
    ) -> MissionWorkflowResult:
        """
        Lance un nouveau workflow de mission.

        Retourne immédiatement si le workflow se termine normalement.
        Retourne avec interrupted=True si une approbation est requise.
        """
        if not _LANGGRAPH_OK or self._graph is None:
            return self._fallback_result(text, mission_id)

        mid = mission_id or str(uuid.uuid4())
        config = {"configurable": {"thread_id": mid}}

        initial_state: MissionWorkflowState = {
            "mission_id":       mid,
            "mission_text":     text,
            "intent":           "",
            "mode":             "",
            "stage":            WorkflowStage.PLANNING.value,
            "requires_approval": False,
            "approval_status":  None,
            "gate_decision":    "UNKNOWN",
            "gate_score":       0.0,
            "gate_reason":      "",
            "execution_result": None,
            "error":            None,
            "created_at":       time.time(),
        }

        try:
            output = self._graph.invoke(initial_state, config=config)

            # Avec interrupt_before, LangGraph ne lève pas d'exception :
            # il retourne l'état courant et met le graphe en pause.
            # On détecte la pause via snapshot.next (non-vide si paused).
            snapshot = self._graph.get_state(config)
            if snapshot and snapshot.next:
                # Graphe pausé — approbation requise
                return self._handle_interrupt(mid, config)

            return self._state_to_result(output, mid)

        except Exception as exc:
            exc_type = type(exc).__name__
            if "Interrupt" in exc_type or "interrupt" in str(exc).lower():
                return self._handle_interrupt(mid, config)

            log.error("workflow_run_error", err=str(exc), mission_id=mid)
            return MissionWorkflowResult(
                mission_id=mid,
                stage=WorkflowStage.FAILED.value,
                error=str(exc),
            )

    def approve(self, mission_id: str, decision: str = "approved") -> MissionWorkflowResult:
        """
        Reprend un workflow en attente d'approbation.

        Args:
            mission_id : ID de la mission à reprendre
            decision   : "approved" | "rejected"

        Returns:
            MissionWorkflowResult mis à jour
        """
        if not _LANGGRAPH_OK or self._graph is None:
            return MissionWorkflowResult(
                mission_id=mission_id,
                stage=WorkflowStage.FAILED.value,
                error="LangGraph non disponible",
            )

        config = {"configurable": {"thread_id": mission_id}}

        try:
            output = self._graph.invoke(
                Command(resume=decision),
                config=config,
            )
            result = self._state_to_result(output, mission_id)
            # Nettoyer l'entrée interrupt
            with self._lock:
                self._interrupts.pop(mission_id, None)
            return result

        except Exception as exc:
            exc_type = type(exc).__name__
            if "Interrupt" in exc_type:
                # Interrupt encore (ne devrait pas arriver normalement)
                return self._handle_interrupt(mission_id, config)
            log.error("workflow_approve_error", err=str(exc), mission_id=mission_id)
            return MissionWorkflowResult(
                mission_id=mission_id,
                stage=WorkflowStage.FAILED.value,
                error=str(exc),
            )

    def get_pending_approvals(self) -> list[dict]:
        """Retourne la liste des missions en attente d'approbation."""
        with self._lock:
            return list(self._interrupts.values())

    def get_mission_state(self, mission_id: str) -> dict | None:
        """Retourne l'état courant d'un workflow depuis le checkpointer."""
        if not self._checkpointer:
            return None
        try:
            config = {"configurable": {"thread_id": mission_id}}
            snapshot = self._graph.get_state(config)
            if snapshot and snapshot.values:
                return dict(snapshot.values)
        except Exception:
            pass
        return None

    # ── Internals ─────────────────────────────────────────────────────────────

    def _handle_interrupt(self, mission_id: str, config: dict) -> MissionWorkflowResult:
        """Gère un interrupt LangGraph en sauvegardant le payload."""
        # Récupérer l'état depuis le checkpointer
        payload: dict = {"mission_id": mission_id, "timestamp": time.time()}
        try:
            snapshot = self._graph.get_state(config)
            if snapshot and snapshot.values:
                state = snapshot.values
                payload.update({
                    "mission_text":  state.get("mission_text", "")[:200],
                    "gate_decision": state.get("gate_decision", "UNKNOWN"),
                    "gate_score":    state.get("gate_score", 0.0),
                    "gate_reason":   state.get("gate_reason", ""),
                })
                gate_score    = float(state.get("gate_score", 0.0))
                gate_decision = state.get("gate_decision", "UNKNOWN")
            else:
                gate_score    = 0.0
                gate_decision = "UNKNOWN"
        except Exception:
            gate_score    = 0.0
            gate_decision = "UNKNOWN"

        with self._lock:
            self._interrupts[mission_id] = payload

        log.info(
            "workflow_waiting_approval",
            mission_id=mission_id,
            gate_decision=gate_decision,
            gate_score=gate_score,
        )

        return MissionWorkflowResult(
            mission_id=mission_id,
            stage=WorkflowStage.AWAITING_APPROVAL.value,
            gate_decision=gate_decision,
            gate_score=gate_score,
            interrupted=True,
        )

    @staticmethod
    def _state_to_result(state: dict, mission_id: str) -> MissionWorkflowResult:
        return MissionWorkflowResult(
            mission_id=mission_id,
            stage=state.get("stage", WorkflowStage.DONE.value),
            gate_decision=state.get("gate_decision", "UNKNOWN"),
            gate_score=float(state.get("gate_score", 0.0)),
            approval_status=state.get("approval_status") or "n/a",
            execution_result=state.get("execution_result") or "",
            error=state.get("error") or "",
            interrupted=False,
        )

    @staticmethod
    def _fallback_result(text: str, mission_id: str | None) -> MissionWorkflowResult:
        """Fallback si LangGraph non disponible."""
        return MissionWorkflowResult(
            mission_id=mission_id or str(uuid.uuid4()),
            stage=WorkflowStage.FAILED.value,
            error="LangGraph non installé — workflow indisponible (pip install langgraph)",
        )
