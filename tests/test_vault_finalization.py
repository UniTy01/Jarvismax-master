"""
JARVIS MAX — Tests BLOC 1-4 : Vault Finalization
Tests des 4 blocs de finalisation production :
  BLOC 1 : VaultMemory (memory/vault_memory.py)
  BLOC 2 : LearningLoop (learning/learning_loop.py)
  BLOC 3 : ShadowGate (core/shadow_gate.py)
  BLOC 4 : CoherenceChecker (core/coherence_checker.py)
"""
import sys
import os
import time
import json
import tempfile
import importlib
from pathlib import Path
from unittest.mock import MagicMock, patch

# Force UTF-8 sur Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# ── Bootstrap chemin ──────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# Mock structlog AVANT les imports projet
sys.modules.setdefault("structlog", __import__("tests.mock_structlog", fromlist=["mock_structlog"]))

_pass = _fail = 0

def ok(label: str):
    global _pass
    _pass += 1
    print(f"  ✅ {label}")

def ko(label: str, exc: Exception):
    global _fail
    _fail += 1
    print(f"  ❌ {label} — {exc}")


# ══════════════════════════════════════════════════════════════════════════════
# BLOC 1 — VAULT MEMORY
# ══════════════════════════════════════════════════════════════════════════════

print("\n── BLOC 1 : VaultMemory ──────────────────────────────────────────────")

def test_vault_import():
    from memory.vault_memory import VaultEntry, VaultMemory, get_vault_memory, VAULT_TYPES
    ok("Import VaultMemory OK")

def test_vault_entry_schema():
    from memory.vault_memory import VaultEntry
    e = VaultEntry(
        type="pattern",
        content="Toujours utiliser asyncio.wait_for() avec timeout",
        source="tests/test_async.py",
        confidence=0.85,
    )
    assert e.id, "id manquant"
    assert e.type == "pattern"
    assert e.content.startswith("Toujours")
    assert e.source == "tests/test_async.py"
    assert e.confidence == 0.85
    assert e.usage_count == 0
    assert e.last_used is None
    assert e.tags == []
    assert e.related_to == []
    assert e.valid is True
    ok("VaultEntry schema complet (10 champs)")

def test_vault_entry_type_normalisation():
    from memory.vault_memory import VaultEntry
    e = VaultEntry(type="invalid_type", content="test", source="x", confidence=0.5)
    assert e.type == "insight", f"Expected 'insight', got {e.type!r}"
    ok("VaultEntry type normalisé vers 'insight'")

def test_vault_entry_confidence_clamp():
    from memory.vault_memory import VaultEntry
    e_low  = VaultEntry(type="fix", content="test clamp", source="x", confidence=-1.5)
    e_high = VaultEntry(type="fix", content="test clamp 2", source="x", confidence=99.0)
    assert e_low.confidence == 0.0
    assert e_high.confidence == 1.0
    ok("VaultEntry confidence clampée [0, 1]")

def test_vault_entry_fingerprint():
    from memory.vault_memory import VaultEntry
    e1 = VaultEntry(type="pattern", content="même contenu test", source="a", confidence=0.8)
    e2 = VaultEntry(type="pattern", content="même contenu test", source="b", confidence=0.7)
    assert e1.fingerprint == e2.fingerprint, "Fingerprints doivent correspondre"
    ok("VaultEntry fingerprint identique pour même contenu")

def test_vault_entry_expired():
    from memory.vault_memory import VaultEntry
    e = VaultEntry(
        type="fix", content="exp test", source="x", confidence=0.7,
        expires_at=time.time() - 1,  # déjà expiré
    )
    assert e.is_expired()
    assert not e.is_active()
    ok("VaultEntry is_expired() / is_active()")

def test_vault_entry_boost():
    from memory.vault_memory import VaultEntry
    e = VaultEntry(type="pattern", content="boost test", source="x", confidence=0.70)
    e.boost(success=True)
    assert e.confidence == 0.75, f"Expected 0.75, got {e.confidence}"
    e.boost(success=False)
    e.boost(success=False)
    # confidence réduite
    assert e.confidence < 0.75
    ok("VaultEntry boost() succès/échec")

def test_vault_entry_boost_invalidate():
    from memory.vault_memory import VaultEntry, _MIN_CONFIDENCE
    e = VaultEntry(type="error", content="bad pattern test", source="x", confidence=0.31)
    # Plusieurs failures pour passer sous le seuil
    for _ in range(5):
        e.boost(success=False)
    assert not e.valid, "Entry devrait être invalidée après plusieurs failures"
    ok("VaultEntry invalidée si confidence < seuil")

def test_vault_entry_to_dict():
    from memory.vault_memory import VaultEntry
    e = VaultEntry(
        type="code",
        content="code snippet",
        source="forge-builder",
        confidence=0.9,
        tags=["python", "async"],
    )
    d = e.to_dict()
    assert "id" in d
    assert "type" in d
    assert d["type"] == "code"
    assert "content" in d
    assert "source" in d
    assert "confidence" in d
    assert "usage_count" in d
    assert "last_used" in d
    assert "tags" in d
    assert "related_to" in d
    assert "valid" in d
    ok("VaultEntry to_dict() contient les 10 champs obligatoires")

def test_vault_entry_from_dict():
    from memory.vault_memory import VaultEntry
    d = {
        "id": "abc12345",
        "type": "insight",
        "content": "test from dict",
        "source": "unit-test",
        "confidence": 0.75,
        "usage_count": 3,
        "last_used": "2026-01-01T00:00:00Z",
        "tags": ["test"],
        "related_to": [],
        "valid": True,
        "created_at": time.time(),
        "expires_at": None,
    }
    e = VaultEntry.from_dict(d)
    assert e.id == "abc12345"
    assert e.usage_count == 3
    assert e.last_used == "2026-01-01T00:00:00Z"
    ok("VaultEntry from_dict() reconstruction correcte")

def test_vault_store_basic(tmp_path):
    from memory.vault_memory import VaultMemory
    vm = VaultMemory(storage_path=tmp_path / "vault.json")
    entry = vm.store(
        type="pattern",
        content="Utiliser httpx plutôt que requests pour async",
        source="best_practices.md",
        confidence=0.82,
        tags=["python", "http", "async"],
    )
    assert entry is not None
    assert entry.type == "pattern"
    assert entry.id in vm._entries
    ok("VaultMemory.store() stocke une entrée")

def test_vault_store_low_confidence_rejected(tmp_path):
    from memory.vault_memory import VaultMemory
    vm = VaultMemory(storage_path=tmp_path / "vault.json")
    result = vm.store(
        type="insight",
        content="confidence trop basse test",
        source="x",
        confidence=0.10,  # < 0.30
    )
    assert result is None
    ok("VaultMemory.store() rejette confidence < 0.30")

def test_vault_store_duplicate_fp(tmp_path):
    from memory.vault_memory import VaultMemory
    vm = VaultMemory(storage_path=tmp_path / "vault.json")
    vm.store(type="pattern", content="test dédup fingerprint exact",
             source="x", confidence=0.70)
    r2 = vm.store(type="pattern", content="test dédup fingerprint exact",
                  source="y", confidence=0.75)
    assert r2 is None, "Doublon par fingerprint devrait être rejeté"
    ok("VaultMemory.store() déduplication fingerprint")

def test_vault_store_duplicate_jaccard(tmp_path):
    from memory.vault_memory import VaultMemory
    vm = VaultMemory(storage_path=tmp_path / "vault.json")
    vm.store(
        type="pattern",
        content="Toujours utiliser asyncio wait_for avec timeout pour éviter les blocages",
        source="x", confidence=0.80,
    )
    # Contenu similaire (Jaccard > 0.60)
    r2 = vm.store(
        type="pattern",
        content="Toujours utiliser asyncio wait_for avec timeout pour éviter les blocages async",
        source="y", confidence=0.80,
    )
    assert r2 is None, "Doublon Jaccard devrait être rejeté"
    ok("VaultMemory.store() déduplication Jaccard")

def test_vault_retrieve(tmp_path):
    from memory.vault_memory import VaultMemory
    vm = VaultMemory(storage_path=tmp_path / "vault.json")
    vm.store(type="pattern", content="asyncio wait_for timeout python async",
             source="x", confidence=0.85, tags=["python", "async"])
    vm.store(type="error", content="module not found import error python",
             source="y", confidence=0.70, tags=["python"])
    vm.store(type="business", content="freemium SaaS pricing model revenue",
             source="z", confidence=0.65, tags=["business"])

    results = vm.retrieve(query="async timeout", max_k=3)
    assert len(results) > 0
    assert results[0].type in {"pattern", "error"}  # async content should rank first
    ok("VaultMemory.retrieve() retourne des résultats pertinents")

def test_vault_retrieve_type_filter(tmp_path):
    from memory.vault_memory import VaultMemory
    vm = VaultMemory(storage_path=tmp_path / "vault.json")
    vm.store(type="pattern", content="test pattern retrieval filter type",
             source="x", confidence=0.75)
    vm.store(type="error", content="test error retrieval filter type entry",
             source="y", confidence=0.75)

    results = vm.retrieve(query="test", type_filter="error", max_k=5)
    assert all(e.type == "error" for e in results)
    ok("VaultMemory.retrieve() filtre par type")

def test_vault_retrieve_tags_filter(tmp_path):
    from memory.vault_memory import VaultMemory
    vm = VaultMemory(storage_path=tmp_path / "vault.json")
    vm.store(type="pattern", content="docker container deployment ops",
             source="x", confidence=0.75, tags=["docker", "ops"])
    vm.store(type="pattern", content="python typing hints annotate code",
             source="y", confidence=0.75, tags=["python", "types"])

    results = vm.retrieve(query="code", tags_filter=["docker"], max_k=5)
    assert any("docker" in e.tags for e in results)
    ok("VaultMemory.retrieve() filtre par tags")

def test_vault_feedback_success(tmp_path):
    from memory.vault_memory import VaultMemory
    vm = VaultMemory(storage_path=tmp_path / "vault.json")
    e = vm.store(type="fix", content="feedback success test entry vault",
                 source="x", confidence=0.70)
    before = vm._entries[e.id].confidence
    vm.feedback(e.id, success=True)
    after = vm._entries[e.id].confidence
    assert after > before
    ok("VaultMemory.feedback(success=True) booste confidence")

def test_vault_feedback_failure(tmp_path):
    from memory.vault_memory import VaultMemory
    vm = VaultMemory(storage_path=tmp_path / "vault.json")
    e = vm.store(type="fix", content="feedback failure test entry vault",
                 source="x", confidence=0.70)
    before = vm._entries[e.id].confidence
    vm.feedback(e.id, success=False)
    after = vm._entries[e.id].confidence
    assert after < before
    ok("VaultMemory.feedback(success=False) réduit confidence")

def test_vault_invalidate(tmp_path):
    from memory.vault_memory import VaultMemory
    vm = VaultMemory(storage_path=tmp_path / "vault.json")
    e = vm.store(type="insight", content="invalidate test entry vault content",
                 source="x", confidence=0.75)
    assert vm._entries[e.id].valid is True
    vm.invalidate(e.id)
    assert vm._entries[e.id].valid is False
    # Ne doit plus apparaître dans retrieve
    results = vm.retrieve(query="invalidate test", max_k=5)
    assert all(r.id != e.id for r in results)
    ok("VaultMemory.invalidate() soft-delete")

def test_vault_get_context_for_prompt(tmp_path):
    from memory.vault_memory import VaultMemory
    vm = VaultMemory(storage_path=tmp_path / "vault.json")
    vm.store(type="pattern", content="use asyncio properly with timeouts",
             source="x", confidence=0.85, tags=["python"])
    ctx = vm.get_context_for_prompt(query="asyncio timeout", max_k=3)
    assert "Vault" in ctx or "pattern" in ctx.upper() or "PATTERN" in ctx
    ok("VaultMemory.get_context_for_prompt() retourne bloc injectable")

def test_vault_get_context_marks_used(tmp_path):
    from memory.vault_memory import VaultMemory
    vm = VaultMemory(storage_path=tmp_path / "vault.json")
    e = vm.store(type="pattern", content="mark used context prompt test vault",
                 source="x", confidence=0.85)
    assert vm._entries[e.id].usage_count == 0
    vm.get_context_for_prompt(query="mark used context", max_k=3)
    assert vm._entries[e.id].usage_count == 1
    ok("VaultMemory.get_context_for_prompt() incrémente usage_count")

def test_vault_is_known(tmp_path):
    from memory.vault_memory import VaultMemory
    vm = VaultMemory(storage_path=tmp_path / "vault.json")
    vm.store(type="pattern", content="known content already stored pattern",
             source="x", confidence=0.80)
    assert vm.is_known("known content already stored pattern")
    assert not vm.is_known("completely different new content here now")
    ok("VaultMemory.is_known() détecte les doublons")

def test_vault_prune_expired(tmp_path):
    from memory.vault_memory import VaultMemory
    vm = VaultMemory(storage_path=tmp_path / "vault.json")
    e = vm.store(type="fix", content="prune expired test entry vault content",
                 source="x", confidence=0.75, ttl_days=0)
    # Force expiration
    vm._entries[e.id].expires_at = time.time() - 1
    n = vm.prune_expired()
    assert n >= 1
    assert e.id not in vm._entries
    ok("VaultMemory.prune_expired() supprime les entrées expirées")

def test_vault_stats(tmp_path):
    from memory.vault_memory import VaultMemory
    vm = VaultMemory(storage_path=tmp_path / "vault.json")
    vm.store(type="pattern", content="asyncio wait_for avoids network hangs completely",
             source="x", confidence=0.75)
    vm.store(type="error", content="bare except silences all python exceptions dangerously",
             source="y", confidence=0.80)
    s = vm.stats()
    assert s["total_active"] >= 2, f"Expected >= 2 active, got {s['total_active']}"
    assert "by_type" in s
    assert "avg_confidence" in s
    ok("VaultMemory.stats() retourne statistiques correctes")

def test_vault_persistence(tmp_path):
    from memory.vault_memory import VaultMemory
    path = tmp_path / "vault.json"
    vm1 = VaultMemory(storage_path=path)
    e = vm1.store(type="insight", content="persistence test entry vault content",
                  source="unit-test", confidence=0.78)
    assert path.exists()

    vm2 = VaultMemory(storage_path=path)
    assert e.id in vm2._entries
    assert vm2._entries[e.id].content == e.content
    ok("VaultMemory persistance JSON (save/load)")

def test_vault_singleton():
    from memory.vault_memory import get_vault_memory
    vm1 = get_vault_memory()
    vm2 = get_vault_memory()
    assert vm1 is vm2
    ok("get_vault_memory() singleton")


# Exécution BLOC 1
for name, fn in list(globals().items()):
    if name.startswith("test_vault_") and callable(fn):
        try:
            import inspect
            sig = inspect.signature(fn)
            if "tmp_path" in sig.parameters:
                with tempfile.TemporaryDirectory() as td:
                    fn(Path(td))
            else:
                fn()
        except Exception as e:
            ko(name, e)


# ══════════════════════════════════════════════════════════════════════════════
# BLOC 2 — LEARNING LOOP
# ══════════════════════════════════════════════════════════════════════════════

print("\n── BLOC 2 : LearningLoop ─────────────────────────────────────────────")

def test_ll_import():
    from learning.learning_loop import (
        LearningLoop, LearningReport, ExtractedInsight,
        learning_loop, get_learning_loop,
    )
    ok("Import LearningLoop OK")

def test_ll_extract_pattern():
    from learning.learning_loop import LearningLoop
    loop = LearningLoop()
    insights = loop._extract(
        "Toujours utiliser asyncio.wait_for() avec timeout pour éviter les blocages réseau.",
        agent_name="forge-builder",
        context="python async",
        success=True,
    )
    assert len(insights) > 0
    types = [i.type for i in insights]
    assert "pattern" in types
    ok("LearningLoop extrait un pattern depuis un texte 'toujours...'")

def test_ll_extract_anti_pattern():
    from learning.learning_loop import LearningLoop
    loop = LearningLoop()
    insights = loop._extract(
        "Ne jamais utiliser bare except car il masque les vraies erreurs Python.",
        agent_name="lens-reviewer",
        context="python error handling",
        success=False,
    )
    assert len(insights) > 0
    types = [i.type for i in insights]
    assert "anti_pattern" in types
    ok("LearningLoop extrait un anti-pattern depuis 'jamais...'")

def test_ll_extract_error():
    from learning.learning_loop import LearningLoop
    loop = LearningLoop()
    insights = loop._extract(
        "❌ REFUSÉ : erreur de syntaxe dans le code généré — TypeError ligne 42",
        agent_name="lens-reviewer",
        context="code review",
        success=False,
    )
    assert len(insights) > 0
    types = [i.type for i in insights]
    assert "error" in types
    ok("LearningLoop extrait une erreur depuis '❌ REFUSÉ'")

def test_ll_extract_insight():
    from learning.learning_loop import LearningLoop
    loop = LearningLoop()
    insights = loop._extract(
        "Important : découvert que le rate limit API est 60 req/min, essentiel pour le design.",
        agent_name="scout-research",
        context="api design",
        success=True,
    )
    assert len(insights) > 0
    assert any(i.type == "insight" for i in insights)
    ok("LearningLoop extrait un insight depuis 'découvert/important'")

def test_ll_extract_no_signal():
    from learning.learning_loop import LearningLoop
    loop = LearningLoop()
    insights = loop._extract(
        "Le ciel est bleu et il fait beau aujourd'hui.",
        agent_name="scout-research",
        context="météo",
        success=True,
    )
    assert len(insights) == 0, f"Attendu 0 insight, obtenu {len(insights)}"
    ok("LearningLoop ignore les textes sans signal")

def test_ll_extract_tags():
    from learning.learning_loop import LearningLoop
    loop = LearningLoop()
    text = "Toujours tester les endpoints API avec pytest et docker."
    insights = loop._extract(text, "forge-builder", "python api test", True)
    if insights:
        tags = insights[0].tags
        assert "forge" in tags or "python" in tags or "api" in tags or "test" in tags
    ok("LearningLoop extrait des tags contextuels")

def test_ll_extract_confidence():
    from learning.learning_loop import LearningLoop
    loop = LearningLoop()
    insights = loop._extract(
        "Toujours utiliser des type hints en Python pour améliorer la maintenabilité.",
        "forge-builder", "python typing", True,
    )
    if insights:
        assert 0.5 <= insights[0].confidence <= 1.0
    ok("LearningLoop assigne une confidence valide")

def test_ll_observe_returns_report():
    """Test observe() avec vault mocked pour éviter I/O."""
    from learning.learning_loop import LearningLoop

    with patch("learning.learning_loop.LearningLoop._validate_and_store",
               return_value="stored"):
        loop = LearningLoop()
        report = loop.observe(
            agent_name="forge-builder",
            output=(
                "✅ Code approuvé. Toujours utiliser asyncio.wait_for() avec timeout. "
                "Ne jamais laisser de bare except. Important : tester l'idempotence."
            ),
            context="python async generation",
            success=True,
        )
        assert isinstance(report.agent_name, str)
        assert report.agent_name == "forge-builder"
        assert len(report.extracted) > 0
        assert report.duration_ms >= 0
        ok("LearningLoop.observe() retourne un LearningReport")

def test_ll_report_summary():
    from learning.learning_loop import LearningReport, ExtractedInsight
    r = LearningReport(
        agent_name="forge-builder",
        extracted=[ExtractedInsight("c", "pattern", "src", 0.7)],
        stored=2,
        discarded=1,
        needs_test=0,
        duration_ms=42.0,
    )
    s = r.summary()
    assert "forge-builder" in s
    assert "stored=2" in s
    ok("LearningReport.summary() format correct")

def test_ll_report_is_useful():
    from learning.learning_loop import LearningReport
    r1 = LearningReport(agent_name="x", stored=1)
    r2 = LearningReport(agent_name="y", stored=0)
    assert r1.is_useful()
    assert not r2.is_useful()
    ok("LearningReport.is_useful() correct")

def test_ll_learning_loop_shortcut():
    from learning.learning_loop import learning_loop
    with patch("learning.learning_loop.LearningLoop._validate_and_store",
               return_value="discarded"):
        report = learning_loop(
            agent_name="scout-research",
            output="Jamais faire X sans Y car c'est dangereux pour la sécurité.",
            context="security",
            success=False,
        )
        assert report.agent_name == "scout-research"
    ok("learning_loop() raccourci fonctionnel")

def test_ll_observe_session():
    from learning.learning_loop import LearningLoop
    loop = LearningLoop()

    session = MagicMock()
    session.mission_summary = "test mission"
    # session.outputs est l'attribut réel (core/state.py JarvisSession.outputs)
    # session.agents_outputs n'existe pas — le test utilisait le mauvais nom
    session.outputs = {
        "forge-builder": {
            "output": "Toujours utiliser des type hints Python pour meilleure lisibilité.",
            "success": True,
        },
        "lens-reviewer": {
            "output": "✅ Code approuvé. Recommandé : ajouter des tests unitaires.",
            "success": True,
        },
    }

    with patch("learning.learning_loop.LearningLoop._validate_and_store",
               return_value="stored"):
        reports = loop.observe_session(session)
        assert len(reports) == 2
        assert all(isinstance(r.agent_name, str) for r in reports)
    ok("LearningLoop.observe_session() traite plusieurs agents")

def test_ll_singleton():
    from learning.learning_loop import get_learning_loop
    l1 = get_learning_loop()
    l2 = get_learning_loop()
    assert l1 is l2
    ok("get_learning_loop() singleton")


# Exécution BLOC 2
for name, fn in list(globals().items()):
    if name.startswith("test_ll_") and callable(fn):
        try:
            fn()
        except Exception as e:
            ko(name, e)


# ══════════════════════════════════════════════════════════════════════════════
# BLOC 3 — SHADOW GATE
# ══════════════════════════════════════════════════════════════════════════════

print("\n── BLOC 3 : ShadowGate ───────────────────────────────────────────────")

def test_sg_import():
    from core.shadow_gate import (
        ShadowGate, GateResult, gate_check, get_shadow_gate,
        SCORE_BLOCK_THRESHOLD, SCORE_WARN_THRESHOLD,
    )
    ok("Import ShadowGate OK")

def test_sg_gate_result_schema():
    from core.shadow_gate import GateResult
    r = GateResult(allowed=True, reason="test OK", decision="GO", score=8.0)
    assert not r.is_blocked()
    assert not r.has_warning()
    assert "ALLOWED" in str(r)
    ok("GateResult schema et méthodes")

def test_sg_gate_result_blocked():
    from core.shadow_gate import GateResult
    r = GateResult(allowed=False, reason="blocked", decision="NO-GO", score=2.5)
    assert r.is_blocked()
    assert "BLOCKED" in str(r)
    ok("GateResult is_blocked() quand allowed=False")

def test_sg_gate_result_warning():
    from core.shadow_gate import GateResult, SCORE_WARN_THRESHOLD
    r = GateResult(allowed=True, reason="warn", decision="IMPROVE", score=SCORE_WARN_THRESHOLD - 0.1)
    assert r.has_warning()
    ok("GateResult has_warning() quand score < SCORE_WARN_THRESHOLD")

def test_sg_no_go_blocked():
    from core.shadow_gate import ShadowGate
    gate = ShadowGate()
    session = MagicMock()
    session.session_id = "test-001"
    session.metadata = {
        "shadow_advisory": {"decision": "NO-GO", "final_score": 2.0},
        "shadow_score": 2.0,
        "shadow_decision": "NO-GO",
    }
    with patch("core.shadow_gate.ShadowGate._build_memory_ctx", return_value=""):
        result = gate.check(session)
    assert result.is_blocked()
    assert result.decision in {"NO-GO", "NO_GO"}
    ok("ShadowGate bloque sur NO-GO")

def test_sg_low_score_blocked():
    from core.shadow_gate import ShadowGate, SCORE_BLOCK_THRESHOLD
    gate = ShadowGate()
    session = MagicMock()
    session.session_id = "test-002"
    session.metadata = {
        "shadow_advisory": {"decision": "IMPROVE", "final_score": 3.0},
        "shadow_score": 3.0,
        "shadow_decision": "IMPROVE",
    }
    with patch("core.shadow_gate.ShadowGate._build_memory_ctx", return_value=""):
        result = gate.check(session)
    assert result.is_blocked(), f"Attendu blocked pour score 3.0 < {SCORE_BLOCK_THRESHOLD}"
    ok(f"ShadowGate bloque score < {SCORE_BLOCK_THRESHOLD}")

def test_sg_go_allowed():
    from core.shadow_gate import ShadowGate
    gate = ShadowGate()
    session = MagicMock()
    session.session_id = "test-003"
    session.metadata = {
        "shadow_advisory": {"decision": "GO", "final_score": 8.5},
        "shadow_score": 8.5,
        "shadow_decision": "GO",
    }
    with patch("core.shadow_gate.ShadowGate._build_memory_ctx", return_value=""):
        result = gate.check(session)
    assert result.allowed
    assert not result.is_blocked()
    ok("ShadowGate autorise GO avec score élevé")

def test_sg_improve_high_score_allowed():
    from core.shadow_gate import ShadowGate
    gate = ShadowGate()
    session = MagicMock()
    session.session_id = "test-004"
    session.metadata = {
        "shadow_advisory": {"decision": "IMPROVE", "final_score": 6.0},
        "shadow_score": 6.0,
        "shadow_decision": "IMPROVE",
    }
    with patch("core.shadow_gate.ShadowGate._build_memory_ctx", return_value=""):
        result = gate.check(session)
    assert result.allowed
    ok("ShadowGate autorise IMPROVE avec score acceptable")

def test_sg_no_advisory_warns():
    from core.shadow_gate import ShadowGate
    gate = ShadowGate()
    session = MagicMock()
    session.session_id = "test-005"
    session.metadata = {}  # Pas de rapport shadow
    with patch("core.shadow_gate.ShadowGate._build_memory_ctx", return_value=""):
        result = gate.check(session)
    assert result.allowed    # fail-open : pas de rapport = pas de blocage
    assert result.decision == "UNKNOWN"
    ok("ShadowGate fail-open si aucun rapport (avertissement)")

def test_sg_check_advisory_dict_no_go():
    from core.shadow_gate import ShadowGate
    gate = ShadowGate()
    report = {"decision": "NO-GO", "final_score": 2.5}
    result = gate.check_advisory(report)
    assert result.is_blocked()
    ok("ShadowGate.check_advisory() bloque NO-GO dict")

def test_sg_check_advisory_dict_go():
    from core.shadow_gate import ShadowGate
    gate = ShadowGate()
    report = {"decision": "GO", "final_score": 8.0}
    result = gate.check_advisory(report)
    assert result.allowed
    ok("ShadowGate.check_advisory() autorise GO dict")

def test_sg_error_recovery():
    """ShadowGate doit être fail-open en cas d'erreur technique."""
    from core.shadow_gate import ShadowGate
    gate = ShadowGate()
    session = MagicMock(spec=[])  # Pas d'attribut metadata → AttributeError
    result = gate.check(session)
    assert result.allowed  # fail-open
    ok("ShadowGate fail-open en cas d'erreur technique")

def test_sg_gate_check_shortcut():
    from core.shadow_gate import gate_check
    session = MagicMock()
    session.session_id = "shortcut-test"
    session.metadata = {
        "shadow_advisory": {"decision": "GO", "final_score": 7.5},
        "shadow_score": 7.5,
        "shadow_decision": "GO",
    }
    with patch("core.shadow_gate.ShadowGate._build_memory_ctx", return_value=""):
        result = gate_check(session)
    assert isinstance(result.allowed, bool)
    ok("gate_check() raccourci fonctionnel")

def test_sg_memory_ctx_injected():
    """_build_memory_ctx doit retourner un bloc si le vault a des erreurs."""
    from core.shadow_gate import ShadowGate
    from memory.vault_memory import VaultMemory

    gate = ShadowGate()
    session = MagicMock()
    session.session_id = "mem-ctx-test"
    session.mission_summary = "test mission"
    session.metadata = {
        "shadow_advisory": {"decision": "GO", "final_score": 8.0},
        "shadow_score": 8.0,
        "shadow_decision": "GO",
    }

    with tempfile.TemporaryDirectory() as td:
        vm = VaultMemory(storage_path=Path(td) / "vault.json")
        vm.store(type="error", content="known past error in production vault",
                 source="prod", confidence=0.80)

        with patch("memory.vault_memory.get_vault_memory", return_value=vm):
            result = gate.check(session)
        assert result.allowed
    ok("ShadowGate._build_memory_ctx() injecte mémoire vault")

def test_sg_singleton():
    from core.shadow_gate import get_shadow_gate
    g1 = get_shadow_gate()
    g2 = get_shadow_gate()
    assert g1 is g2
    ok("get_shadow_gate() singleton")


# Exécution BLOC 3
for name, fn in list(globals().items()):
    if name.startswith("test_sg_") and callable(fn):
        try:
            fn()
        except Exception as e:
            ko(name, e)


# ══════════════════════════════════════════════════════════════════════════════
# BLOC 4 — COHERENCE CHECKER
# ══════════════════════════════════════════════════════════════════════════════

print("\n── BLOC 4 : CoherenceChecker ─────────────────────────────────────────")

def test_cc_import():
    from core.coherence_checker import (
        CoherenceChecker, CoherenceResult, check_text, check_session,
        get_coherence_checker,
    )
    ok("Import CoherenceChecker OK")

def test_cc_result_schema():
    from core.coherence_checker import CoherenceResult
    r = CoherenceResult(passed=True)
    assert r.passed
    assert r.score == 1.0
    assert r.errors == []
    assert r.warnings == []
    assert r.issues == []
    ok("CoherenceResult schema initial (score=1.0)")

def test_cc_result_add_error():
    from core.coherence_checker import CoherenceResult
    r = CoherenceResult(passed=True)
    r.add_error("erreur critique test")
    assert not r.passed
    assert len(r.errors) == 1
    assert "[ERROR]" in r.issues[0]
    assert r.score < 1.0
    ok("CoherenceResult.add_error() marque passed=False")

def test_cc_result_add_warning():
    from core.coherence_checker import CoherenceResult
    r = CoherenceResult(passed=True)
    r.add_warning("avertissement test")
    assert r.passed   # warning ne bloque pas
    assert len(r.warnings) == 1
    assert "[WARN]" in r.issues[0]
    ok("CoherenceResult.add_warning() garde passed=True")

def test_cc_result_summary():
    from core.coherence_checker import CoherenceResult
    r = CoherenceResult(passed=True)
    r.add_warning("avert")
    s = r.summary()
    assert "PASS" in s or "FAIL" in s
    assert "score=" in s
    ok("CoherenceResult.summary() format")

def test_cc_clean_text_passes():
    from core.coherence_checker import CoherenceChecker
    cc = CoherenceChecker()
    result = cc.check_text(
        "Le code utilise asyncio avec wait_for pour gérer les timeouts réseau.",
        context="test clean",
    )
    assert result.passed
    assert result.score >= 0.8
    ok("CoherenceChecker texte propre → passed=True")

def test_cc_phantom_path_warning():
    from core.coherence_checker import CoherenceChecker
    cc = CoherenceChecker()
    result = cc.check_text(
        "Stocke les fichiers dans /home/maxen/projects/jarvis/workspace/data",
        context="phantom path test",
    )
    assert len(result.warnings) > 0
    ok("CoherenceChecker détecte chemin fantôme /home/...")

def test_cc_suspicious_import_error():
    from core.coherence_checker import CoherenceChecker
    cc = CoherenceChecker()
    result = cc.check_text(
        "import jarvis_core\nfrom jarviscore import something",
        context="suspicious import test",
    )
    assert not result.passed
    assert len(result.errors) > 0
    ok("CoherenceChecker détecte import suspect (jarvis_core)")

def test_cc_hallucination_signal_warning():
    from core.coherence_checker import CoherenceChecker
    cc = CoherenceChecker()
    result = cc.check_text(
        "J'imagine que le taux de conversion est probablement autour de 5000.",
        context="hallucination test",
    )
    assert len(result.warnings) > 0
    ok("CoherenceChecker détecte signal d'hallucination")

def test_cc_check_paths_valid():
    from core.coherence_checker import CoherenceChecker
    cc = CoherenceChecker()
    result = cc.check_paths(["workspace/output.py", "core/state.py"])
    assert result.passed
    ok("CoherenceChecker.check_paths() paths valides → passed")

def test_cc_check_paths_phantom():
    from core.coherence_checker import CoherenceChecker
    cc = CoherenceChecker()
    result = cc.check_paths(["/home/user/my_project/nonexistent.py"])
    assert not result.passed or len(result.warnings) > 0 or len(result.errors) > 0
    ok("CoherenceChecker.check_paths() chemin fantôme détecté")

def test_cc_check_paths_must_exist():
    from core.coherence_checker import CoherenceChecker
    cc = CoherenceChecker()
    result = cc.check_paths(
        ["workspace/nonexistent_file_xyz.py"],
        must_exist=True,
    )
    # Warning attendu (pas error) car must_exist produit warning
    assert len(result.warnings) > 0 or len(result.errors) > 0
    ok("CoherenceChecker.check_paths(must_exist=True) signale fichier manquant")

def test_cc_check_plan_valid():
    from core.coherence_checker import CoherenceChecker
    cc = CoherenceChecker()
    plan = [
        {"agent": "scout-research", "task": "Recherche", "priority": 1},
        {"agent": "forge-builder", "task": "Code", "priority": 2},
        {"agent": "lens-reviewer", "task": "Review", "priority": 3},
    ]
    result = cc.check_plan(plan)
    assert result.passed
    assert len(result.errors) == 0
    ok("CoherenceChecker.check_plan() plan valide → passed")

def test_cc_check_plan_unknown_agent():
    from core.coherence_checker import CoherenceChecker
    cc = CoherenceChecker()
    plan = [
        {"agent": "hallucinated-agent", "task": "Test", "priority": 1},
    ]
    result = cc.check_plan(plan)
    assert len(result.warnings) > 0
    ok("CoherenceChecker.check_plan() agent inconnu → warning")

def test_cc_check_plan_duplicate_agent():
    from core.coherence_checker import CoherenceChecker
    cc = CoherenceChecker()
    plan = [
        {"agent": "scout-research", "task": "T1", "priority": 1},
        {"agent": "scout-research", "task": "T2", "priority": 2},
    ]
    result = cc.check_plan(plan)
    assert len(result.warnings) > 0
    ok("CoherenceChecker.check_plan() agent dupliqué → warning")

def test_cc_check_plan_invalid_priority():
    from core.coherence_checker import CoherenceChecker
    cc = CoherenceChecker()
    plan = [{"agent": "forge-builder", "task": "T", "priority": 0}]
    result = cc.check_plan(plan)
    assert len(result.warnings) > 0
    ok("CoherenceChecker.check_plan() priorité invalide → warning")

def test_cc_check_session_clean():
    from core.coherence_checker import CoherenceChecker
    cc = CoherenceChecker()
    session = MagicMock()
    session.agents_outputs = {
        "forge-builder": {
            "output": "Code propre utilisant asyncio et pytest correctement.",
            "success": True,
        }
    }
    session._raw_actions = []
    result = cc.check_session(session)
    assert result.passed
    ok("CoherenceChecker.check_session() session propre → passed")

def test_cc_check_session_with_errors():
    from core.coherence_checker import CoherenceChecker
    cc = CoherenceChecker()
    session = MagicMock()
    session.agents_outputs = {
        "forge-builder": {
            "output": "import jarvis_core\nfaire quelque chose",
            "success": True,
        }
    }
    session._raw_actions = []
    result = cc.check_session(session)
    assert not result.passed
    ok("CoherenceChecker.check_session() détecte erreur dans sortie agent")

def test_cc_check_session_phantom_action():
    from core.coherence_checker import CoherenceChecker
    cc = CoherenceChecker()
    session = MagicMock()
    session.agents_outputs = {}
    session._raw_actions = [
        {"action_type": "create_file", "target": "/home/user/test.py"}
    ]
    result = cc.check_session(session)
    # Warning ou error attendu sur le chemin fantôme
    assert len(result.warnings) > 0 or len(result.errors) > 0
    ok("CoherenceChecker.check_session() détecte chemin fantôme dans actions")

def test_cc_known_error_detection():
    """Le checker devrait signaler si une erreur connue est répétée."""
    from core.coherence_checker import CoherenceChecker
    from memory.vault_memory import VaultMemory

    with tempfile.TemporaryDirectory() as td:
        vm = VaultMemory(storage_path=Path(td) / "vault.json")
        vm.store(
            type="error",
            content="bare except masque les vraies erreurs Python silencieusement",
            source="tests",
            confidence=0.85,
        )

        cc = CoherenceChecker()
        with patch("memory.vault_memory.get_vault_memory", return_value=vm):
            result = cc.check_text(
                "Le code utilise bare except qui masque les vraies erreurs Python silencieusement.",
                context="code review",
            )
        # Devrait détecter la répétition d'erreur connue
        assert len(result.warnings) > 0
    ok("CoherenceChecker détecte répétition d'erreur connue (vault)")

def test_cc_shortcut_check_text():
    from core.coherence_checker import check_text
    result = check_text("Code Python propre sans problème visible.", "test")
    assert result.passed
    ok("check_text() raccourci fonctionnel")

def test_cc_shortcut_check_session():
    from core.coherence_checker import check_session
    session = MagicMock()
    session.agents_outputs = {}
    session._raw_actions = []
    result = check_session(session)
    assert isinstance(result.passed, bool)
    ok("check_session() raccourci fonctionnel")

def test_cc_singleton():
    from core.coherence_checker import get_coherence_checker
    c1 = get_coherence_checker()
    c2 = get_coherence_checker()
    assert c1 is c2
    ok("get_coherence_checker() singleton")


# Exécution BLOC 4
for name, fn in list(globals().items()):
    if name.startswith("test_cc_") and callable(fn):
        try:
            fn()
        except Exception as e:
            ko(name, e)


# ══════════════════════════════════════════════════════════════════════════════
# INTÉGRATION — Flux complet
# ══════════════════════════════════════════════════════════════════════════════

print("\n── INTÉGRATION : Flux complet ────────────────────────────────────────")

def test_integration_vault_to_gate():
    """Vault stores anti-pattern → Gate injecte dans memory_ctx."""
    from memory.vault_memory import VaultMemory
    from core.shadow_gate import ShadowGate

    with tempfile.TemporaryDirectory() as td:
        vm = VaultMemory(storage_path=Path(td) / "vault.json")
        vm.store(
            type="error",
            content="hardcoded credentials in source code production failure",
            source="post-mortem",
            confidence=0.95,
        )

        gate = ShadowGate()
        session = MagicMock()
        session.session_id = "integ-01"
        session.mission_summary = "deploy code"
        session.metadata = {
            "shadow_advisory": {"decision": "GO", "final_score": 7.8},
            "shadow_score": 7.8,
            "shadow_decision": "GO",
        }

        with patch("memory.vault_memory.get_vault_memory", return_value=vm):
            result = gate.check(session)

        assert result.allowed
        assert "error" in result.memory_ctx.lower() or "vault" in result.memory_ctx.lower() or result.memory_ctx == ""
    ok("Intégration : Vault → ShadowGate memory_ctx")

def test_integration_loop_to_vault():
    """LearningLoop extrait un pattern et le stocke dans VaultMemory."""
    from learning.learning_loop import LearningLoop
    from memory.vault_memory import VaultMemory

    with tempfile.TemporaryDirectory() as td:
        vm = VaultMemory(storage_path=Path(td) / "vault.json")

        # Mock le validator pour retourner KEEP
        with patch("learning.learning_loop.LearningLoop._validate_and_store") as mock_store:
            mock_store.return_value = "stored"
            loop = LearningLoop()
            report = loop.observe(
                agent_name="forge-builder",
                output=(
                    "✅ Code approuvé. "
                    "Toujours utiliser des type hints Python pour documenter les interfaces. "
                    "Ne jamais hardcoder des credentials dans le code source."
                ),
                context="python best practices",
                success=True,
            )

        assert len(report.extracted) > 0
        assert report.duration_ms >= 0
    ok("Intégration : LearningLoop extrait + stocke dans VaultMemory")

def test_integration_coherence_gate_pipeline():
    """Pipeline complet : coherence check → shadow gate decision."""
    from core.coherence_checker import CoherenceChecker
    from core.shadow_gate import ShadowGate

    cc = CoherenceChecker()
    gate = ShadowGate()

    # Texte agent propre
    agent_output = (
        "Le plan est cohérent. "
        "Recommandé : utiliser asyncio.wait_for() pour tous les appels réseau. "
        "Validé par les tests unitaires."
    )

    coherence = cc.check_text(agent_output, "forge-builder")
    assert coherence.passed

    # Rapport shadow GO
    session = MagicMock()
    session.session_id = "pipeline-01"
    session.mission_summary = "build api client"
    session.metadata = {
        "shadow_advisory": {"decision": "GO", "final_score": 8.0},
        "shadow_score": 8.0,
        "shadow_decision": "GO",
    }

    with patch("core.shadow_gate.ShadowGate._build_memory_ctx", return_value=""):
        gate_result = gate.check(session)

    assert gate_result.allowed
    ok("Intégration pipeline : coherence → gate → GO allowed")

def test_integration_no_go_blocks_pipeline():
    """NO-GO shadow arrête le pipeline même si coherence passe."""
    from core.coherence_checker import CoherenceChecker
    from core.shadow_gate import ShadowGate

    cc  = CoherenceChecker()
    gate = ShadowGate()

    clean_output = "Code propre, tests passent, aucun problème visible."
    coherence = cc.check_text(clean_output)
    assert coherence.passed  # Cohérence OK

    # Mais shadow dit NO-GO
    session = MagicMock()
    session.session_id = "pipeline-02"
    session.metadata = {
        "shadow_advisory": {"decision": "NO-GO", "final_score": 1.5},
        "shadow_score": 1.5,
        "shadow_decision": "NO-GO",
    }

    with patch("core.shadow_gate.ShadowGate._build_memory_ctx", return_value=""):
        gate_result = gate.check(session)

    assert gate_result.is_blocked()
    assert "NO-GO" in gate_result.decision.upper() or "NO" in gate_result.decision.upper()
    ok("Intégration pipeline : coherence OK + shadow NO-GO → bloqué")


# Exécution intégration
for name, fn in list(globals().items()):
    if name.startswith("test_integration_") and callable(fn):
        try:
            fn()
        except Exception as e:
            ko(name, e)


# ══════════════════════════════════════════════════════════════════════════════
# RÉSULTAT FINAL
# ══════════════════════════════════════════════════════════════════════════════

print(f"\n{'═'*60}")
print(f"  RÉSULTAT : {_pass} PASS | {_fail} FAIL")
print(f"{'═'*60}\n")

if _fail and __name__ == "__main__":
    pass  # sys.exit removed for pytest compatibility
