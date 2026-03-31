"""Edge case tests for core/task_router.py — boundary conditions."""
import sys
from unittest.mock import MagicMock

sys.modules.setdefault("core.state", MagicMock())


def _route(text, **kwargs):
    from core.task_router import TaskRouter
    return TaskRouter().route(text, **kwargs)


# ── Unicode and accent handling ───────────────────────────────

def test_accented_code_request():
    """Accented verbs like 'écris' should match CODE pattern."""
    r = _route("écris un script Python")
    assert r.mode.value == "code"


def test_accented_improve_request():
    """'améliore-toi' should match IMPROVE."""
    r = _route("améliore-toi en ajoutant de meilleurs tests")
    assert r.mode.value == "improve"


# ── Edge case inputs ──────────────────────────────────────────

def test_whitespace_only():
    r = _route("   ")
    assert r.mode.value == "chat"


def test_very_long_input():
    """Very long input should not crash or timeout."""
    long_text = "analyse " + "les données " * 500
    r = _route(long_text)
    assert r.mode is not None
    assert r.reason is not None


def test_special_characters():
    """Special characters should not crash routing."""
    r = _route("🤖 bonjour! @test #tag $100")
    assert r.mode is not None


def test_newlines_in_input():
    r = _route("salut\n\ncomment ça va?")
    # Multi-line input — should still route
    assert r.mode is not None


# ── Explicit mode edge cases ─────────────────────────────────

def test_explicit_invalid_mode():
    """Invalid explicit mode should fall through to pattern matching."""
    r = _route("bonjour", explicit_mode="INVALID_MODE_XYZ")
    # Should fallback to pattern matching
    assert r.mode.value == "chat"


def test_explicit_mode_case():
    """Explicit modes should work case-sensitive (match enum value)."""
    r = _route("hello", explicit_mode="chat")
    assert r.mode.value == "chat"


# ── Routing decision properties ───────────────────────────────

def test_routing_decision_has_all_fields():
    r = _route("bonjour")
    assert hasattr(r, "mode")
    assert hasattr(r, "agents")
    assert hasattr(r, "confidence")
    assert hasattr(r, "reason")
    assert hasattr(r, "needs_actions")
    assert hasattr(r, "uncensored_mode")


def test_confidence_range():
    """Confidence should always be between 0 and 1."""
    inputs = ["", "salut", "écris un script", "a" * 100, "recherche les tendances AI"]
    for text in inputs:
        r = _route(text)
        assert 0.0 <= r.confidence <= 1.0, f"Confidence {r.confidence} out of range for '{text[:20]}'"


# ── Business routing ──────────────────────────────────────────

def test_business_venture():
    r = _route("venture builder analyse le marché des chatbots")
    assert r.mode.value == "business"


def test_business_saas():
    r = _route("créer un blueprint saas pour un outil de monitoring")
    assert r.mode.value == "business"


# ── Night mode ────────────────────────────────────────────────

def test_night_explicit_command():
    r = _route("/night analyse complète du codebase")
    assert r.mode.value == "night"


def test_night_keyword():
    r = _route("lance une mission longue multi-cycle de refactoring")
    assert r.mode.value == "night"


# ── Agents plan structure ─────────────────────────────────────

def test_agent_plan_deep_copy():
    """Agent plans should be deep copies (no shared mutation)."""
    r1 = _route("recherche les tendances AI")
    r2 = _route("recherche les tendances crypto")
    # Modify r1's agents
    if r1.agents:
        r1.agents[0]["task"] = "MUTATED"
    # r2's agents should be unaffected
    if r2.agents:
        assert r2.agents[0]["task"] != "MUTATED"


def test_agent_plan_has_required_fields():
    """Each agent in the plan should have agent, task, priority."""
    r = _route("recherche les tendances AI")
    for a in r.agents:
        assert "agent" in a
        assert "task" in a
        assert "priority" in a
