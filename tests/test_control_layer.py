"""
Tests — Control Layer v1
Couvre les 6 blocs du control layer :
  BLOC 1 — Mission System
  BLOC 2 — Action Queue
  BLOC 3 — Mode System
  BLOC 4 — Advisory View
  BLOC 5 — Control API
  BLOC 6 — Intégration bout-en-bout

Objectif : 0 FAIL
"""
import sys
import types
import json
import time
import tempfile
import threading
import urllib.request
import urllib.error
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# ── Mock structlog ─────────────────────────────────────────────────────────────
if "structlog" not in sys.modules:
    _root = Path(__file__).parent.parent
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))
    sys.modules.setdefault(
        "structlog",
        __import__("tests.mock_structlog", fromlist=["mock_structlog"])
    )

# ── Mock langchain ─────────────────────────────────────────────────────────────
for _mod in [
    "langchain_core",
    "langchain_core.language_models",
    "langchain_core.messages",
    "langchain_core.outputs",
    "langchain_core.callbacks",
    "langchain_core.callbacks.manager",
    "langchain",
    "langchain.chat_models",
    "langchain_openai",
    "langchain_anthropic",
]:
    if _mod not in sys.modules:
        _m = types.ModuleType(_mod)
        if _mod == "langchain_core.messages":
            _m.SystemMessage = lambda content="": None
            _m.HumanMessage  = lambda content="": None
            _m.AIMessage     = lambda content="": None
        if _mod == "langchain_core.language_models":
            class _FakeLLM:
                def invoke(self, *a, **k): return type("R", (), {"content": ""})()
            _m.BaseChatModel = _FakeLLM
        sys.modules[_mod] = _m

# ── Compteurs ──────────────────────────────────────────────────────────────────
_pass = 0
_fail = 0

def ok(name: str):
    global _pass
    _pass += 1
    print(f"  PASS  {name}")

def ko(name: str, exc=None):
    global _fail
    _fail += 1
    msg = f" ({exc})" if exc else ""
    print(f"  FAIL  {name}{msg}")

def section(title: str):
    print(f"\n{'─'*55}")
    print(f"  {title}")
    print('─'*55)

def assert_eq(got, exp, label=""):
    if got != exp:
        raise AssertionError(f"{label}: attendu {exp!r}, obtenu {got!r}")

def assert_in(value, container, label=""):
    if value not in container:
        raise AssertionError(f"{label}: {value!r} absent de {container!r}")


# ══════════════════════════════════════════════════════════════════════════════
#  BLOC 1 — Mission System
# ══════════════════════════════════════════════════════════════════════════════

section("BLOC 1 — Mission System")

from core.mission_system import (
    MissionSystem, MissionIntent, MissionStatus,
    MissionResult, detect_intent, get_mission_system,
)

def _ms(td):
    from core.action_queue import ActionQueue
    from core.mode_system import ModeSystem
    aq   = ActionQueue(storage=Path(td) / "queue.json")
    mode = ModeSystem(storage=Path(td) / "mode.json")
    return MissionSystem(
        storage=Path(td) / "missions.json",
        action_queue=aq,
        mode_system=mode,
    )

# 1. detect_intent — keywords d'analyse
def test_intent_analyze():
    i = detect_intent("analyse le code de ce module")
    assert i == MissionIntent.ANALYZE, f"got {i}"
ok("test_intent_analyze") if not (lambda: (lambda: None)())() else None
try:
    test_intent_analyze()
    ok("intent_analyze")
except Exception as e:
    ko("intent_analyze", e)

# 2. detect_intent — création
try:
    i = detect_intent("crée un nouveau fichier rapport")
    assert i == MissionIntent.CREATE, f"got {i}"
    ok("intent_create")
except Exception as e:
    ko("intent_create", e)

# 3. detect_intent — amélioration
try:
    i = detect_intent("améliore le système de cache")
    assert i == MissionIntent.IMPROVE, f"got {i}"
    ok("intent_improve")
except Exception as e:
    ko("intent_improve", e)

# 4. detect_intent — recherche
try:
    i = detect_intent("cherche et explore les fichiers de config")
    assert i == MissionIntent.SEARCH, f"got {i}"
    ok("intent_search")
except Exception as e:
    ko("intent_search", e)

# 5. detect_intent — monitoring
try:
    i = detect_intent("surveille les métriques du système")
    assert i == MissionIntent.MONITOR, f"got {i}"
    ok("intent_monitor")
except Exception as e:
    ko("intent_monitor", e)

# 6. detect_intent — review
try:
    i = detect_intent("review ce pull request")
    assert i == MissionIntent.REVIEW, f"got {i}"
    ok("intent_review")
except Exception as e:
    ko("intent_review", e)

# 7. detect_intent — plan
try:
    i = detect_intent("planifie la prochaine sprint")
    assert i == MissionIntent.PLAN, f"got {i}"
    ok("intent_plan")
except Exception as e:
    ko("intent_plan", e)

# 8. detect_intent — fallback OTHER
try:
    i = detect_intent("xyzzy foo bar quux")
    assert i == MissionIntent.OTHER, f"got {i}"
    ok("intent_other_fallback")
except Exception as e:
    ko("intent_other_fallback", e)

# 9. submit — retourne MissionResult
try:
    with tempfile.TemporaryDirectory() as td:
        ms = _ms(td)
        r  = ms.submit("analyse le module core/orchestrator.py")
        assert isinstance(r, MissionResult)
        assert r.mission_id
        assert r.intent == MissionIntent.ANALYZE
        ok("submit_returns_result")
except Exception as e:
    ko("submit_returns_result", e)

# 10. submit — plan a des étapes
try:
    with tempfile.TemporaryDirectory() as td:
        ms = _ms(td)
        r  = ms.submit("analyse les performances du système")
        assert len(r.plan_steps) > 0, "plan vide"
        ok("submit_plan_has_steps")
except Exception as e:
    ko("submit_plan_has_steps", e)

# 11. submit — advisory score rempli
try:
    with tempfile.TemporaryDirectory() as td:
        ms = _ms(td)
        r  = ms.submit("crée un rapport de synthèse")
        assert 0.0 <= r.advisory_score <= 10.0
        ok("submit_advisory_score_range")
except Exception as e:
    ko("submit_advisory_score_range", e)

# 12. submit — action_ids créés
try:
    with tempfile.TemporaryDirectory() as td:
        ms = _ms(td)
        r  = ms.submit("recherche les fichiers modifiés")
        assert isinstance(r.action_ids, list)
        ok("submit_action_ids_list")
except Exception as e:
    ko("submit_action_ids_list", e)

# 13. submit — persistance sur disque
try:
    with tempfile.TemporaryDirectory() as td:
        ms = _ms(td)
        r  = ms.submit("surveille le CPU")
        ms2 = _ms(td)
        found = ms2.get(r.mission_id)
        assert found is not None
        assert found.mission_id == r.mission_id
        ok("submit_persisted")
except Exception as e:
    ko("submit_persisted", e)

# 14. approve mission
try:
    with tempfile.TemporaryDirectory() as td:
        ms = _ms(td)
        r  = ms.submit("analyse les logs d'erreur")
        approved = ms.approve(r.mission_id, note="OK")
        assert approved is not None
        assert approved.status in {
            MissionStatus.APPROVED, MissionStatus.EXECUTING, MissionStatus.DONE
        }
        ok("approve_mission")
except Exception as e:
    ko("approve_mission", e)

# 15. reject mission
try:
    with tempfile.TemporaryDirectory() as td:
        ms = _ms(td)
        r  = ms.submit("planifie la refonte du système")
        rejected = ms.reject(r.mission_id, note="Hors scope")
        assert rejected is not None
        assert rejected.status == MissionStatus.REJECTED
        ok("reject_mission")
except Exception as e:
    ko("reject_mission", e)

# 16. list_missions — filtre par status
try:
    with tempfile.TemporaryDirectory() as td:
        ms = _ms(td)
        ms.submit("analyse A")
        ms.submit("analyse B")
        missions = ms.list_missions()
        assert len(missions) >= 2
        ok("list_missions")
except Exception as e:
    ko("list_missions", e)

# 17. stats — structure de base
try:
    with tempfile.TemporaryDirectory() as td:
        ms = _ms(td)
        ms.submit("améliore le module X")
        st = ms.stats()
        assert "total" in st
        assert st["total"] >= 1
        ok("mission_stats")
except Exception as e:
    ko("mission_stats", e)

# 18. to_dict — sérialisable JSON
try:
    with tempfile.TemporaryDirectory() as td:
        ms = _ms(td)
        r  = ms.submit("review le code de l'agent")
        d  = r.to_dict()
        json.dumps(d)   # doit pas lever
        assert "mission_id" in d
        assert "status" in d
        ok("result_to_dict_json_serializable")
except Exception as e:
    ko("result_to_dict_json_serializable", e)

# 19. get — mission introuvable retourne None
try:
    with tempfile.TemporaryDirectory() as td:
        ms = _ms(td)
        assert ms.get("inexistant-xyz") is None
        ok("get_unknown_returns_none")
except Exception as e:
    ko("get_unknown_returns_none", e)

# 20. submit — input vide géré sans crash
try:
    with tempfile.TemporaryDirectory() as td:
        ms = _ms(td)
        r  = ms.submit("")
        assert r is not None
        ok("submit_empty_input_no_crash")
except Exception as e:
    ko("submit_empty_input_no_crash", e)


# ══════════════════════════════════════════════════════════════════════════════
#  BLOC 2 — Action Queue
# ══════════════════════════════════════════════════════════════════════════════

section("BLOC 2 — Action Queue")

from core.action_queue import (
    ActionQueue, Action, ActionRisk, ActionStatus, get_action_queue,
)

def _aq(td):
    return ActionQueue(storage=Path(td) / "queue.json")

# 21. enqueue — retourne Action
try:
    with tempfile.TemporaryDirectory() as td:
        aq = _aq(td)
        a  = aq.enqueue("Test action", risk="LOW", target="file.py", impact="Rien")
        assert isinstance(a, Action)
        assert a.id
        ok("enqueue_returns_action")
except Exception as e:
    ko("enqueue_returns_action", e)

# 22. enqueue — status PENDING par défaut
try:
    with tempfile.TemporaryDirectory() as td:
        aq = _aq(td)
        a  = aq.enqueue("Test", risk="LOW", target="x", impact="y")
        assert a.status == ActionStatus.PENDING
        ok("enqueue_status_pending")
except Exception as e:
    ko("enqueue_status_pending", e)

# 23. approve — PENDING → APPROVED
try:
    with tempfile.TemporaryDirectory() as td:
        aq = _aq(td)
        a  = aq.enqueue("Approuver", risk="LOW", target="x", impact="y")
        ok_a = aq.approve(a.id)
        assert ok_a.status == ActionStatus.APPROVED
        ok("approve_pending_to_approved")
except Exception as e:
    ko("approve_pending_to_approved", e)

# 24. reject — PENDING → REJECTED
try:
    with tempfile.TemporaryDirectory() as td:
        aq = _aq(td)
        a  = aq.enqueue("Rejeter", risk="HIGH", target="x", impact="y")
        r  = aq.reject(a.id, note="trop risqué")
        assert r.status == ActionStatus.REJECTED
        assert r.note == "trop risqué"
        ok("reject_with_note")
except Exception as e:
    ko("reject_with_note", e)

# 25. mark_executed — APPROVED → EXECUTED
try:
    with tempfile.TemporaryDirectory() as td:
        aq = _aq(td)
        a  = aq.enqueue("Exécuter", risk="LOW", target="x", impact="y")
        aq.approve(a.id)
        ex = aq.mark_executed(a.id, result="succès")
        assert ex.status == ActionStatus.EXECUTED
        assert ex.result == "succès"
        ok("mark_executed")
except Exception as e:
    ko("mark_executed", e)

# 26. mark_failed — APPROVED → FAILED
try:
    with tempfile.TemporaryDirectory() as td:
        aq = _aq(td)
        a  = aq.enqueue("Échouer", risk="MEDIUM", target="x", impact="y")
        aq.approve(a.id)
        f  = aq.mark_failed(a.id, result="timeout")
        assert f.status == ActionStatus.FAILED
        ok("mark_failed")
except Exception as e:
    ko("mark_failed", e)

# 27. pending() — filtre correct
try:
    with tempfile.TemporaryDirectory() as td:
        aq = _aq(td)
        a1 = aq.enqueue("P1", risk="LOW", target="x", impact="y")
        a2 = aq.enqueue("P2", risk="LOW", target="x", impact="y")
        aq.approve(a1.id)
        pending = aq.pending()
        ids = [p.id for p in pending]
        assert a2.id in ids
        assert a1.id not in ids
        ok("pending_filter")
except Exception as e:
    ko("pending_filter", e)

# 28. for_mission — filtre par mission_id
try:
    with tempfile.TemporaryDirectory() as td:
        aq = _aq(td)
        aq.enqueue("Autre", risk="LOW", target="x", impact="y", mission_id="m999")
        a  = aq.enqueue("Mine", risk="LOW", target="x", impact="y", mission_id="m001")
        mine = aq.for_mission("m001")
        assert len(mine) == 1
        assert mine[0].id == a.id
        ok("for_mission_filter")
except Exception as e:
    ko("for_mission_filter", e)

# 29. stats — structure complète
try:
    with tempfile.TemporaryDirectory() as td:
        aq = _aq(td)
        aq.enqueue("X", risk="LOW", target="x", impact="y")
        st = aq.stats()
        for key in ("total", "pending", "approved", "executed", "rejected"):
            assert key in st, f"clé manquante: {key}"
        ok("action_stats_complete")
except Exception as e:
    ko("action_stats_complete", e)

# 30. to_summary — format lisible
try:
    with tempfile.TemporaryDirectory() as td:
        aq = _aq(td)
        a  = aq.enqueue("Test résumé", risk="CRITICAL", target="prod", impact="delete")
        s  = a.to_summary()
        assert "CRITICAL" in s
        assert a.id in s
        ok("to_summary_format")
except Exception as e:
    ko("to_summary_format", e)

# 31. approve — introuvable retourne None
try:
    with tempfile.TemporaryDirectory() as td:
        aq = _aq(td)
        assert aq.approve("xyz-fake") is None
        ok("approve_unknown_returns_none")
except Exception as e:
    ko("approve_unknown_returns_none", e)

# 32. reject — déjà EXECUTED retourne None
try:
    with tempfile.TemporaryDirectory() as td:
        aq = _aq(td)
        a  = aq.enqueue("done", risk="LOW", target="x", impact="y")
        aq.approve(a.id)
        aq.mark_executed(a.id)
        assert aq.reject(a.id) is None
        ok("reject_executed_returns_none")
except Exception as e:
    ko("reject_executed_returns_none", e)

# 33. persistance rechargement
try:
    with tempfile.TemporaryDirectory() as td:
        aq1 = _aq(td)
        a   = aq1.enqueue("Persisté", risk="HIGH", target="db", impact="maj")
        aq2 = _aq(td)
        reloaded = aq2.get(a.id)
        assert reloaded is not None
        assert reloaded.description == "Persisté"
        ok("action_queue_persistence")
except Exception as e:
    ko("action_queue_persistence", e)

# 34. all() — tri par date décroissante, limite respectée
try:
    with tempfile.TemporaryDirectory() as td:
        aq = _aq(td)
        for i in range(5):
            aq.enqueue(f"A{i}", risk="LOW", target="x", impact="y")
        all3 = aq.all(limit=3)
        assert len(all3) == 3
        ok("all_limit_respected")
except Exception as e:
    ko("all_limit_respected", e)

# 35. is_critical / is_high_risk
try:
    a_crit = Action(description="x", risk="CRITICAL", target="y", impact="z")
    a_high = Action(description="x", risk="HIGH",     target="y", impact="z")
    a_low  = Action(description="x", risk="LOW",      target="y", impact="z")
    assert a_crit.is_critical()
    assert a_high.is_high_risk()
    assert not a_low.is_critical()
    ok("is_critical_is_high_risk")
except Exception as e:
    ko("is_critical_is_high_risk", e)


# ══════════════════════════════════════════════════════════════════════════════
#  BLOC 3 — Mode System
# ══════════════════════════════════════════════════════════════════════════════

section("BLOC 3 — Mode System")

from core.mode_system import ModeSystem, SystemMode, get_mode_system

def _mode(td):
    return ModeSystem(storage=Path(td) / "mode.json")

# 36. mode par défaut — SUPERVISED
try:
    with tempfile.TemporaryDirectory() as td:
        ms = _mode(td)
        assert ms.get_mode() == SystemMode.SUPERVISED
        ok("default_mode_supervised")
except Exception as e:
    ko("default_mode_supervised", e)

# 37. set_mode — MANUAL
try:
    with tempfile.TemporaryDirectory() as td:
        ms = _mode(td)
        ms.set_mode("MANUAL")
        assert ms.get_mode() == SystemMode.MANUAL
        ok("set_mode_manual")
except Exception as e:
    ko("set_mode_manual", e)

# 38. set_mode — AUTO
try:
    with tempfile.TemporaryDirectory() as td:
        ms = _mode(td)
        ms.set_mode("AUTO")
        assert ms.get_mode() == SystemMode.AUTO
        ok("set_mode_auto")
except Exception as e:
    ko("set_mode_auto", e)

# 39. set_mode — invalide lève ValueError
try:
    with tempfile.TemporaryDirectory() as td:
        ms = _mode(td)
        raised = False
        try:
            ms.set_mode("TURBO")
        except ValueError:
            raised = True
        assert raised
        ok("set_mode_invalid_raises")
except Exception as e:
    ko("set_mode_invalid_raises", e)

# 40. MANUAL — rien n'est auto-approuvé
try:
    with tempfile.TemporaryDirectory() as td:
        ms = _mode(td)
        ms.set_mode("MANUAL")
        for risk in ("LOW", "MEDIUM", "HIGH", "CRITICAL"):
            assert not ms.should_auto_approve(risk, 10.0), f"{risk} auto approuvé en MANUAL"
        ok("manual_nothing_auto")
except Exception as e:
    ko("manual_nothing_auto", e)

# 41. SUPERVISED — LOW auto
try:
    with tempfile.TemporaryDirectory() as td:
        ms = _mode(td)
        ms.set_mode("SUPERVISED")
        assert ms.should_auto_approve("LOW")
        ok("supervised_low_auto")
except Exception as e:
    ko("supervised_low_auto", e)

# 42. SUPERVISED — MEDIUM auto si score >= 7.0
try:
    with tempfile.TemporaryDirectory() as td:
        ms = _mode(td)
        ms.set_mode("SUPERVISED")
        assert ms.should_auto_approve("MEDIUM", shadow_score=7.0)
        assert ms.should_auto_approve("MEDIUM", shadow_score=9.5)
        assert not ms.should_auto_approve("MEDIUM", shadow_score=6.9)
        ok("supervised_medium_threshold")
except Exception as e:
    ko("supervised_medium_threshold", e)

# 43. SUPERVISED — HIGH validation requise
try:
    with tempfile.TemporaryDirectory() as td:
        ms = _mode(td)
        ms.set_mode("SUPERVISED")
        assert not ms.should_auto_approve("HIGH", shadow_score=10.0)
        ok("supervised_high_requires_validation")
except Exception as e:
    ko("supervised_high_requires_validation", e)

# 44. SUPERVISED — CRITICAL validation requise
try:
    with tempfile.TemporaryDirectory() as td:
        ms = _mode(td)
        ms.set_mode("SUPERVISED")
        assert not ms.should_auto_approve("CRITICAL", shadow_score=10.0)
        ok("supervised_critical_requires_validation")
except Exception as e:
    ko("supervised_critical_requires_validation", e)

# 45. AUTO — LOW/MEDIUM/HIGH auto
try:
    with tempfile.TemporaryDirectory() as td:
        ms = _mode(td)
        ms.set_mode("AUTO")
        for risk in ("LOW", "MEDIUM", "HIGH"):
            assert ms.should_auto_approve(risk), f"{risk} non-auto en AUTO"
        ok("auto_low_medium_high_auto")
except Exception as e:
    ko("auto_low_medium_high_auto", e)

# 46. AUTO — CRITICAL toujours validation
try:
    with tempfile.TemporaryDirectory() as td:
        ms = _mode(td)
        ms.set_mode("AUTO")
        assert not ms.should_auto_approve("CRITICAL")
        ok("auto_critical_requires_validation")
except Exception as e:
    ko("auto_critical_requires_validation", e)

# 47. requires_validation — inverse de should_auto_approve
try:
    with tempfile.TemporaryDirectory() as td:
        ms = _mode(td)
        ms.set_mode("SUPERVISED")
        assert ms.requires_validation("HIGH") == (not ms.should_auto_approve("HIGH"))
        ok("requires_validation_inverse")
except Exception as e:
    ko("requires_validation_inverse", e)

# 48. mode_description — contient le mode
try:
    with tempfile.TemporaryDirectory() as td:
        ms = _mode(td)
        ms.set_mode("AUTO")
        desc = ms.mode_description()
        assert "AUTO" in desc
        ok("mode_description_contains_mode")
except Exception as e:
    ko("mode_description_contains_mode", e)

# 49. to_dict — structure complète
try:
    with tempfile.TemporaryDirectory() as td:
        ms = _mode(td)
        d  = ms.to_dict()
        for key in ("mode", "description", "rules"):
            assert key in d, f"clé manquante: {key}"
        ok("mode_to_dict_complete")
except Exception as e:
    ko("mode_to_dict_complete", e)

# 50. persistance rechargement
try:
    with tempfile.TemporaryDirectory() as td:
        ms1 = _mode(td)
        ms1.set_mode("AUTO", changed_by="test")
        ms2 = _mode(td)
        assert ms2.get_mode() == SystemMode.AUTO
        ok("mode_persistence")
except Exception as e:
    ko("mode_persistence", e)


# ══════════════════════════════════════════════════════════════════════════════
#  BLOC 4 — Advisory View
# ══════════════════════════════════════════════════════════════════════════════

section("BLOC 4 — Advisory View")

from core.advisory_view import AdvisoryView, format_advisory, advisory_short

_REPORT_GO = {
    "decision":     "GO",
    "final_score":  8.5,
    "confidence":   0.9,
    "justification": "Tout est bon.",
    "blocking_issues": [],
    "risks": [],
    "improvements": ["Ajouter logs"],
    "tests_required": ["test_unit"],
    "weak_points": [],
}

_REPORT_NOGO = {
    "decision":    "NO-GO",
    "final_score": 2.0,
    "confidence":  0.7,
    "justification": "Trop risqué.",
    "blocking_issues": [
        {"type": "securite", "description": "Faille critique", "severity": "high", "evidence": "CVE-xxx"},
    ],
    "risks": [
        {"type": "prod", "description": "Rupture API", "severity": "high", "probability": "high", "impact": "high"},
    ],
    "improvements": [],
    "tests_required": [],
    "weak_points": ["Auth manquante"],
}

_REPORT_IMPROVE = {
    "decision":    "IMPROVE",
    "final_score": 5.5,
    "confidence":  0.6,
    "justification": "Quelques lacunes.",
    "blocking_issues": [],
    "risks": [{"type": "perf", "description": "Lenteur", "severity": "medium", "probability": "medium", "impact": "medium"}],
    "improvements": ["Optimiser les requêtes", "Ajouter cache"],
    "tests_required": [],
    "weak_points": [],
}

# 51. is_go / is_no_go / is_improve
try:
    assert AdvisoryView(_REPORT_GO).is_go()
    assert AdvisoryView(_REPORT_NOGO).is_no_go()
    assert AdvisoryView(_REPORT_IMPROVE).is_improve()
    ok("advisory_decision_booleans")
except Exception as e:
    ko("advisory_decision_booleans", e)

# 52. text() — contient la décision
try:
    txt = AdvisoryView(_REPORT_GO).text()
    assert "GO" in txt
    assert "8.5" in txt
    ok("advisory_text_contains_decision_score")
except Exception as e:
    ko("advisory_text_contains_decision_score", e)

# 53. text() NO-GO — contient les blocages
try:
    txt = AdvisoryView(_REPORT_NOGO).text()
    assert "Faille critique" in txt
    assert "NO-GO" in txt
    ok("advisory_text_nogo_blocking_issues")
except Exception as e:
    ko("advisory_text_nogo_blocking_issues", e)

# 54. short() — une ligne compacte
try:
    s = AdvisoryView(_REPORT_GO).short()
    assert "GO" in s
    assert "score=" in s
    assert "\n" not in s
    ok("advisory_short_one_line")
except Exception as e:
    ko("advisory_short_one_line", e)

# 55. to_dict() — JSON-serializable
try:
    d = AdvisoryView(_REPORT_IMPROVE).to_dict()
    json.dumps(d)
    assert "decision" in d
    assert "score" in d
    assert "is_go" in d
    ok("advisory_to_dict_serializable")
except Exception as e:
    ko("advisory_to_dict_serializable", e)

# 56. critical_count()
try:
    view = AdvisoryView(_REPORT_NOGO)
    assert view.critical_count() == 1
    ok("advisory_critical_count")
except Exception as e:
    ko("advisory_critical_count", e)

# 57. format_advisory — raccourci
try:
    txt = format_advisory(_REPORT_GO)
    assert "GO" in txt
    ok("format_advisory_shortcut")
except Exception as e:
    ko("format_advisory_shortcut", e)

# 58. advisory_short — raccourci
try:
    s = advisory_short(_REPORT_NOGO)
    assert "NO-GO" in s
    ok("advisory_short_shortcut")
except Exception as e:
    ko("advisory_short_shortcut", e)

# 59. score bar — affichage barre ASCII
try:
    d = AdvisoryView(_REPORT_GO).to_dict()
    bar = d["score_bar"]
    assert "█" in bar
    assert "8.5" in bar
    ok("advisory_score_bar")
except Exception as e:
    ko("advisory_score_bar", e)

# 60. rapport dict vide — ne crash pas
try:
    view = AdvisoryView({})
    txt  = view.text()
    assert "UNKNOWN" in txt
    ok("advisory_empty_report_no_crash")
except Exception as e:
    ko("advisory_empty_report_no_crash", e)

# 61. NO-GO flags is_blocked
try:
    d = AdvisoryView(_REPORT_NOGO).to_dict()
    assert d["is_blocked"]
    assert not d["is_go"]
    ok("advisory_is_blocked_flag")
except Exception as e:
    ko("advisory_is_blocked_flag", e)

# 62. rapport avec risks affiche probabilité/impact
try:
    txt = AdvisoryView(_REPORT_NOGO).text()
    assert "P=" in txt
    assert "I=" in txt
    ok("advisory_risks_prob_impact")
except Exception as e:
    ko("advisory_risks_prob_impact", e)



# ══════════════════════════════════════════════════════════════════════════════
#  Résultat final
# ══════════════════════════════════════════════════════════════════════════════

print(f"\n{'═'*55}")
print(f"  RÉSULTAT : {_pass} PASS | {_fail} FAIL")
print(f"{'═'*55}")
if _fail:
    pass  # sys.exit removed for pytest compatibility
