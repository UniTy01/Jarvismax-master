"""
Tests — WorkflowGraph (LangGraph Phase 4b)
Vérifie le workflow de mission avec human-in-loop.
"""
from __future__ import annotations
import pytest

from core.workflow_graph import (
    WorkflowGraph,
    WorkflowStage,
    MissionWorkflowResult,
    _build_heuristic_report,
    _LANGGRAPH_OK,
    get_workflow_graph,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_workflow() -> WorkflowGraph:
    """Workflow propre (singleton réinitialisé) pour chaque test."""
    import core.workflow_graph as wg
    wg._WORKFLOW_INSTANCE = None
    return WorkflowGraph()


# ── Heuristique de risque ─────────────────────────────────────────────────────

def test_heuristic_go_safe_text():
    """Texte sans risque → GO avec score élevé."""
    report = _build_heuristic_report("Analyse le code et propose des améliorations", "ANALYZE")
    assert report["decision"] == "GO"
    assert report["final_score"] >= 7.0


def test_heuristic_improve_single_high_risk():
    """Un seul mot-clé haut risque → IMPROVE."""
    report = _build_heuristic_report("Supprime le fichier temporaire", "CREATE")
    assert report["decision"] == "IMPROVE"
    assert report["final_score"] < 6.0


def test_heuristic_nogo_multiple_high_risk():
    """Deux mots-clés haut risque ou plus → NO-GO."""
    report = _build_heuristic_report("supprime les credentials de production", "OTHER")
    assert report["decision"] == "NO-GO"
    assert report["final_score"] < 4.0


def test_heuristic_improve_medium_risk():
    """Plusieurs mots modificateurs → IMPROVE."""
    report = _build_heuristic_report("Modifie et met à jour le deploy de migration", "IMPROVE")
    assert report["decision"] == "IMPROVE"


def test_heuristic_score_is_numeric():
    """Le score doit toujours être un float."""
    report = _build_heuristic_report("Bonjour Jarvis", "CHAT")
    assert isinstance(report["final_score"], float)
    assert report["decision"] in ("GO", "IMPROVE", "NO-GO")


# ── MissionWorkflowResult ─────────────────────────────────────────────────────

def test_result_done():
    r = MissionWorkflowResult(mission_id="x", stage=WorkflowStage.DONE.value)
    assert r.is_done()
    assert not r.is_failed()
    assert not r.needs_approval()


def test_result_failed():
    r = MissionWorkflowResult(mission_id="x", stage=WorkflowStage.FAILED.value, error="err")
    assert r.is_failed()
    assert not r.is_done()


def test_result_awaiting():
    r = MissionWorkflowResult(
        mission_id="x",
        stage=WorkflowStage.AWAITING_APPROVAL.value,
        interrupted=True,
    )
    assert r.needs_approval()
    assert not r.is_done()
    assert not r.is_failed()


# ── Workflow sans LangGraph (fallback) ────────────────────────────────────────

def test_fallback_when_langgraph_unavailable():
    """Si LangGraph absent, fallback retourne FAILED avec message."""
    import core.workflow_graph as wg
    original = wg._LANGGRAPH_OK
    try:
        wg._LANGGRAPH_OK = False
        wf = WorkflowGraph()
        result = wf.run_mission("Analyse le code")
        assert result.stage == WorkflowStage.FAILED.value
        assert "LangGraph" in result.error
    finally:
        wg._LANGGRAPH_OK = original


# ── Singleton ─────────────────────────────────────────────────────────────────

def test_get_workflow_graph_singleton():
    import core.workflow_graph as wg
    wg._WORKFLOW_INSTANCE = None
    g1 = get_workflow_graph()
    g2 = get_workflow_graph()
    assert g1 is g2
    wg._WORKFLOW_INSTANCE = None


# ── WorkflowStage enum ────────────────────────────────────────────────────────

def test_workflow_stage_values():
    stages = {s.value for s in WorkflowStage}
    assert "PLANNING" in stages
    assert "SHADOW_CHECK" in stages
    assert "AWAITING_APPROVAL" in stages
    assert "EXECUTING" in stages
    assert "DONE" in stages
    assert "FAILED" in stages


# ── Intégration LangGraph (si disponible) ─────────────────────────────────────

@pytest.mark.skipif(not _LANGGRAPH_OK, reason="langgraph non installé")
def test_workflow_runs_safe_mission():
    """Mission sans risque → DONE ou FAILED (execute_node peut échouer sans MissionSystem)."""
    wf = _make_workflow()
    result = wf.run_mission("Analyse la structure du projet Python")
    # DONE si MissionSystem disponible, FAILED sinon (execute_node échoue)
    # Dans les deux cas, pas d'interrupt (texte sûr)
    assert result.stage in (WorkflowStage.DONE.value, WorkflowStage.FAILED.value)
    assert not result.interrupted
    assert result.gate_decision == "GO"


@pytest.mark.skipif(not _LANGGRAPH_OK, reason="langgraph non installé")
def test_workflow_blocks_nogo_mission():
    """Mission NO-GO → FAILED immédiat sans interrupt."""
    wf = _make_workflow()
    result = wf.run_mission("supprime les secrets de production maintenant")
    assert result.stage == WorkflowStage.FAILED.value
    assert not result.interrupted
    assert result.gate_decision == "NO-GO"


@pytest.mark.skipif(not _LANGGRAPH_OK, reason="langgraph non installé")
def test_workflow_interrupts_risky_mission():
    """Mission risquée (IMPROVE) → AWAITING_APPROVAL avec interrupted=True."""
    wf = _make_workflow()
    # Un seul mot-clé haut risque → IMPROVE → interrupt
    result = wf.run_mission("Supprime le fichier temporaire obsolète")
    # Le workflow s'arrête en AWAITING_APPROVAL avant d'exécuter
    assert result.interrupted is True
    assert result.stage == WorkflowStage.AWAITING_APPROVAL.value
    assert result.mission_id in [p["mission_id"] for p in wf.get_pending_approvals()]


@pytest.mark.skipif(not _LANGGRAPH_OK, reason="langgraph non installé")
def test_workflow_approve_resumes_execution():
    """Après approve → workflow reprend et se termine (DONE ou FAILED)."""
    wf = _make_workflow()
    # Déclencher l'interrupt
    result = wf.run_mission("Supprime le fichier temp")
    assert result.interrupted

    # Approuver
    approved = wf.approve(result.mission_id, "approved")
    assert approved.stage in (WorkflowStage.DONE.value, WorkflowStage.FAILED.value)
    assert approved.approval_status == "approved"
    # Plus dans pending
    pending_ids = [p["mission_id"] for p in wf.get_pending_approvals()]
    assert result.mission_id not in pending_ids


@pytest.mark.skipif(not _LANGGRAPH_OK, reason="langgraph non installé")
def test_workflow_reject_leads_to_failed():
    """Après reject → FAILED avec message approprié."""
    wf = _make_workflow()
    result = wf.run_mission("Supprime le fichier temp")
    assert result.interrupted

    rejected = wf.approve(result.mission_id, "rejected")
    assert rejected.stage == WorkflowStage.FAILED.value
    assert rejected.approval_status == "rejected"


@pytest.mark.skipif(not _LANGGRAPH_OK, reason="langgraph non installé")
def test_get_mission_state_returns_dict():
    """get_mission_state retourne un dict ou None."""
    wf = _make_workflow()
    result = wf.run_mission("Analyse le code")
    state = wf.get_mission_state(result.mission_id)
    # Peut être None si pas de checkpointer ou si mission déjà terminée
    assert state is None or isinstance(state, dict)


@pytest.mark.skipif(not _LANGGRAPH_OK, reason="langgraph non installé")
def test_pending_approvals_empty_initially():
    """Aucune mission en attente au départ."""
    wf = _make_workflow()
    pending = wf.get_pending_approvals()
    assert isinstance(pending, list)
    assert len(pending) == 0
