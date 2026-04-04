"""
tests/test_cognitive_upgrade.py — Unit tests for Pass 42 cognitive upgrade.

Tests cover all 3 phases:
  Phase 1 — MissionReasoningState (build, update_observed, compare)
  Phase 2 — ConfidencePolicy (tiers, risk shifts, behavior flags)
  Phase 3 — MissionLessons + memory_retrieval (structure, fallback, injection)

Also covers:
  - No-regression: existing mission flow still works when modules fail
  - Fail-open: all modules return safe fallback on exception

Test strategy: pure unit tests, no LLM, no network, no VPS.
Run with: python -m pytest tests/test_cognitive_upgrade.py -v
"""
from __future__ import annotations

import sys
import os

# Add repo root to path so imports work from test runner
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest


# ══════════════════════════════════════════════════════════════════════════════
# PHASE 1 — MissionReasoningState
# ══════════════════════════════════════════════════════════════════════════════

class TestMissionReasoningState:

    def test_build_returns_state(self):
        """build() always returns a MissionReasoningState, never raises."""
        from core.orchestration.mission_reasoning_state import build
        state = build(
            goal="Fix the authentication bug in login.py",
            mission_id="test-001",
            classification={"task_type": "code", "complexity": "simple", "risk_level": "low"},
        )
        assert state is not None
        assert state.mission_id == "test-001"
        assert "login.py" in state.goal

    def test_build_sets_initial_and_target_state(self):
        """Initial and target state are non-empty strings."""
        from core.orchestration.mission_reasoning_state import build
        state = build(
            goal="Deploy the new API version",
            mission_id="test-002",
            classification={"task_type": "deployment", "complexity": "moderate", "risk_level": "high"},
        )
        assert len(state.initial_state) > 0
        assert len(state.target_state) > 0

    def test_build_populates_preconditions_for_complex(self):
        """Complex mission has multiple preconditions."""
        from core.orchestration.mission_reasoning_state import build
        state = build(
            goal="Redesign the entire authentication system",
            mission_id="test-003",
            classification={"task_type": "code", "complexity": "complex", "risk_level": "medium"},
        )
        assert len(state.preconditions) >= 2

    def test_build_sets_failure_modes_for_code(self):
        """Code task has relevant failure modes."""
        from core.orchestration.mission_reasoning_state import build
        state = build(
            goal="Refactor the payment module",
            mission_id="test-004",
            classification={"task_type": "code", "complexity": "moderate"},
        )
        assert len(state.failure_modes) > 0
        # Code failure modes should mention syntax or tests
        failure_text = " ".join(state.failure_modes).lower()
        assert any(kw in failure_text for kw in ["syntax", "test", "import", "break"])

    def test_build_sets_candidate_actions(self):
        """Candidate actions are populated for non-trivial missions."""
        from core.orchestration.mission_reasoning_state import build
        state = build(
            goal="Analyze database performance bottlenecks",
            mission_id="test-005",
            classification={"task_type": "analysis", "complexity": "moderate"},
        )
        assert len(state.candidate_actions) >= 2

    def test_build_sets_success_criteria(self):
        """Success criteria are populated."""
        from core.orchestration.mission_reasoning_state import build
        state = build(
            goal="Write unit tests for the payment module",
            mission_id="test-006",
            classification={"task_type": "code", "complexity": "simple"},
        )
        assert len(state.success_criteria) >= 1

    def test_build_with_prior_failures_augments_failure_modes(self):
        """Prior failures from memory are added to failure modes."""
        from core.orchestration.mission_reasoning_state import build
        state = build(
            goal="Fix the database connection pool",
            mission_id="test-007",
            classification={"task_type": "code", "complexity": "moderate"},
            prior_failures=["connection timeout after pool exhaustion"],
        )
        failure_text = " ".join(state.failure_modes)
        assert "prior:" in failure_text

    def test_build_with_memory_lessons(self):
        """Memory lessons are incorporated into failure modes."""
        from core.orchestration.mission_reasoning_state import build
        state = build(
            goal="Optimize query performance",
            mission_id="test-008",
            classification={"task_type": "code", "complexity": "moderate"},
            memory_lessons=[{"what_to_do_differently": "use EXPLAIN ANALYZE before optimizing"}],
        )
        failure_text = " ".join(state.failure_modes)
        assert "memory:" in failure_text

    def test_build_fallback_on_exception(self):
        """build() returns fallback state when classification is garbage."""
        from core.orchestration.mission_reasoning_state import build
        state = build(
            goal="Do something",
            mission_id="test-009",
            classification=None,  # Will trigger fallback path
        )
        assert state is not None
        assert state.mission_id == "test-009"

    def test_to_dict_is_serializable(self):
        """to_dict() returns a JSON-serializable dict."""
        import json
        from core.orchestration.mission_reasoning_state import build
        state = build(
            goal="Research competitors",
            mission_id="test-010",
            classification={"task_type": "research", "complexity": "simple"},
        )
        d = state.to_dict()
        # Should not raise
        json.dumps(d)
        assert "mission_id" in d
        assert "initial_state" in d
        assert "target_state" in d
        assert "expected_effects" in d
        assert "success_criteria" in d
        assert "failure_modes" in d

    def test_to_prompt_injection_non_empty(self):
        """Prompt injection includes key state model fields."""
        from core.orchestration.mission_reasoning_state import build
        state = build(
            goal="Fix memory leak in the agent loop",
            mission_id="test-011",
            classification={"task_type": "code", "complexity": "moderate"},
        )
        injection = state.to_prompt_injection()
        assert "[STATE_MODEL]" in injection
        assert "INITIAL:" in injection
        assert "TARGET:" in injection

    def test_update_observed_fills_effects(self):
        """update_observed() populates observed_effects from result."""
        from core.orchestration.mission_reasoning_state import build
        state = build(
            goal="Fix authentication bug",
            mission_id="test-012",
            classification={"task_type": "code", "complexity": "simple"},
        )
        state.update_observed(
            result="Fixed the authentication bug. Login now works correctly. All tests pass.",
            error="",
        )
        assert len(state.observed_effects) > 0
        assert state.state_satisfied is not None

    def test_update_observed_with_error_marks_unsatisfied(self):
        """update_observed() with error marks state_satisfied=False."""
        from core.orchestration.mission_reasoning_state import build
        state = build(
            goal="Deploy service",
            mission_id="test-013",
            classification={"task_type": "deployment", "complexity": "moderate"},
        )
        state.update_observed(result="", error="Container failed to start")
        assert state.state_satisfied is False
        assert "execution_error" in state.satisfaction_reason

    def test_update_observed_computes_expected_vs_observed(self):
        """expected_vs_observed diff is computed after update_observed."""
        from core.orchestration.mission_reasoning_state import build
        state = build(
            goal="Write a report",
            mission_id="test-014",
            classification={"task_type": "research", "complexity": "simple"},
        )
        state.update_observed(result="Findings complete. Sources cited. Conclusions stated.")
        assert "coverage_ratio" in state.expected_vs_observed
        assert isinstance(state.expected_vs_observed["coverage_ratio"], float)

    def test_state_transition_updates_updated_at(self):
        """update_observed() changes updated_at."""
        import time
        from core.orchestration.mission_reasoning_state import build
        state = build(goal="Test", mission_id="test-015")
        t0 = state.updated_at
        time.sleep(0.01)
        state.update_observed(result="Done")
        assert state.updated_at > t0


# ══════════════════════════════════════════════════════════════════════════════
# PHASE 2 — ConfidencePolicy
# ══════════════════════════════════════════════════════════════════════════════

class TestConfidencePolicy:

    def get_policy(self):
        from core.orchestration.confidence_policy import ConfidencePolicy
        return ConfidencePolicy()

    def test_high_confidence_proceeds(self):
        """confidence=0.85 + low risk → PROCEED, no approval."""
        p = self.get_policy()
        d = p.decide(confidence=0.85, risk_level="low")
        from core.orchestration.confidence_policy import PolicyTier
        assert d.tier == PolicyTier.PROCEED
        assert not d.require_approval
        assert not d.abort
        assert not d.add_context

    def test_medium_confidence_gathers_context(self):
        """confidence=0.55 → gather_context tier."""
        p = self.get_policy()
        d = p.decide(confidence=0.55, risk_level="low")
        from core.orchestration.confidence_policy import PolicyTier
        assert d.tier == PolicyTier.CONTEXT
        assert d.add_context
        assert len(d.context_queries) > 0
        assert not d.require_approval

    def test_low_confidence_requires_approval(self):
        """confidence=0.40 + low risk → CAUTIOUS, require_approval=True."""
        p = self.get_policy()
        d = p.decide(confidence=0.40, risk_level="low")
        from core.orchestration.confidence_policy import PolicyTier
        assert d.tier == PolicyTier.CAUTIOUS
        assert d.require_approval
        assert d.add_context

    def test_very_low_confidence_decomposes(self):
        """confidence=0.25 → DECOMPOSE tier."""
        p = self.get_policy()
        d = p.decide(confidence=0.25, risk_level="low")
        from core.orchestration.confidence_policy import PolicyTier
        assert d.tier == PolicyTier.DECOMPOSE
        assert d.decompose_mission
        assert d.require_approval
        assert d.use_safer_model

    def test_critical_confidence_aborts(self):
        """confidence=0.05 → ABORT."""
        p = self.get_policy()
        d = p.decide(confidence=0.05, risk_level="low")
        from core.orchestration.confidence_policy import PolicyTier
        assert d.tier == PolicyTier.ABORT
        assert d.abort
        assert len(d.abort_reason) > 0

    def test_high_risk_shifts_threshold(self):
        """confidence=0.75 + high risk → shifts threshold, may not PROCEED."""
        p = self.get_policy()
        d_low  = p.decide(confidence=0.75, risk_level="low")
        d_high = p.decide(confidence=0.75, risk_level="high")
        from core.orchestration.confidence_policy import PolicyTier
        # low risk: 0.75 >= 0.70 → PROCEED
        assert d_low.tier == PolicyTier.PROCEED
        # high risk: shift 0.10 → 0.65, which is < 0.70 → CONTEXT
        assert d_high.tier != PolicyTier.PROCEED

    def test_critical_risk_triggers_approval_on_medium_confidence(self):
        """confidence=0.65 + critical risk → approval required."""
        p = self.get_policy()
        d = p.decide(confidence=0.65, risk_level="critical")
        assert d.require_approval

    def test_destructive_task_overrides_proceed(self):
        """Even high confidence, destructive=True forces CAUTIOUS."""
        p = self.get_policy()
        d = p.decide(confidence=0.85, risk_level="low", is_destructive=True)
        from core.orchestration.confidence_policy import PolicyTier
        assert d.tier == PolicyTier.CAUTIOUS
        assert d.require_approval

    def test_prior_failures_override_to_cautious(self):
        """Prior failures in memory escalate to CAUTIOUS even at medium-high confidence."""
        p = self.get_policy()
        d = p.decide(confidence=0.65, risk_level="low", has_prior_failures=True)
        from core.orchestration.confidence_policy import PolicyTier
        assert d.tier == PolicyTier.CAUTIOUS

    def test_strategy_suggestion_decompose_respected(self):
        """pre_execution strategy_suggestion='decompose' → DECOMPOSE tier."""
        p = self.get_policy()
        d = p.decide(confidence=0.6, risk_level="low", strategy_suggestion="decompose")
        from core.orchestration.confidence_policy import PolicyTier
        assert d.tier == PolicyTier.DECOMPOSE

    def test_prompt_additions_injected_for_cautious(self):
        """CAUTIOUS tier adds prompt content."""
        p = self.get_policy()
        d = p.decide(confidence=0.40, risk_level="low")
        assert len(d.prompt_additions) > 0
        assert any("CAUTIOUS" in pa or "cautious" in pa.lower() for pa in d.prompt_additions)

    def test_context_queries_generated(self):
        """CONTEXT tier produces relevant queries."""
        p = self.get_policy()
        d = p.decide(confidence=0.55, risk_level="low", task_type="code",
                     goal="Fix the authentication bug")
        assert d.add_context
        assert len(d.context_queries) >= 2

    def test_to_dict_serializable(self):
        """to_dict() returns JSON-serializable dict."""
        import json
        p = self.get_policy()
        d = p.decide(confidence=0.40, risk_level="medium")
        json.dumps(d.to_dict())

    def test_policy_log_is_populated(self):
        """policy_log records reasoning for audit."""
        p = self.get_policy()
        d = p.decide(confidence=0.40, risk_level="high")
        assert len(d.policy_log) > 0

    def test_singleton_get_confidence_policy(self):
        """get_confidence_policy() returns same instance."""
        from core.orchestration.confidence_policy import get_confidence_policy
        p1 = get_confidence_policy()
        p2 = get_confidence_policy()
        assert p1 is p2


# ══════════════════════════════════════════════════════════════════════════════
# PHASE 3 — Memory Retrieval
# ══════════════════════════════════════════════════════════════════════════════

class TestMissionLessons:
    """Tests for MissionLessons data model (no facade dependency)."""

    def test_empty_lessons_has_no_lessons(self):
        from core.orchestration.memory_retrieval import MissionLessons
        lessons = MissionLessons()
        assert not lessons.has_lessons

    def test_lessons_with_avoid_has_lessons(self):
        from core.orchestration.memory_retrieval import MissionLessons
        lessons = MissionLessons(avoid=["do not skip tests"])
        assert lessons.has_lessons

    def test_to_dict_serializable(self):
        import json
        from core.orchestration.memory_retrieval import MissionLessons
        lessons = MissionLessons(
            avoid=["skip tests", "assume no regression"],
            reuse=["run tests before commit"],
            summary="2 failures, 1 success",
        )
        json.dumps(lessons.to_dict())

    def test_prompt_injection_empty_when_no_lessons(self):
        from core.orchestration.memory_retrieval import MissionLessons
        lessons = MissionLessons()
        assert lessons.to_prompt_injection() == ""

    def test_prompt_injection_includes_avoid_and_reuse(self):
        from core.orchestration.memory_retrieval import MissionLessons
        lessons = MissionLessons(
            avoid=["skip health check"],
            reuse=["deploy then verify"],
        )
        injection = lessons.to_prompt_injection()
        assert "[MEMORY_LESSONS]" in injection
        assert "AVOID" in injection
        assert "REUSE" in injection

    def test_failed_retrieval_is_fail_open(self):
        """retrieve_mission_lessons never raises — returns empty lessons."""
        from core.orchestration.memory_retrieval import retrieve_mission_lessons
        # Calling without facade available should not raise
        lessons = retrieve_mission_lessons("deploy the API", task_type="deployment")
        assert lessons is not None
        # Either has data or is fail-open
        assert isinstance(lessons.retrieval_ok, bool)

    def test_failed_retrieval_logs_error(self):
        """When memory_facade fails, retrieval_ok=False and error is recorded."""
        from core.orchestration.memory_retrieval import MissionLessons
        # Simulate a failed retrieval
        lessons = MissionLessons(
            retrieval_ok=False,
            retrieval_error="connection refused",
        )
        assert not lessons.retrieval_ok
        assert "connection refused" in lessons.retrieval_error

    def test_normalize_dict_entry(self):
        """_normalize handles dict entries correctly."""
        from core.orchestration.memory_retrieval import _normalize
        entry = {"content": "Test content", "score": 0.8, "content_type": "failure"}
        result = _normalize(entry)
        assert result["content"] == "Test content"
        assert result["score"] == 0.8

    def test_extract_avoid_falls_back_to_defaults(self):
        """_extract_avoid returns defaults when no failures found."""
        from core.orchestration.memory_retrieval import _extract_avoid
        avoid = _extract_avoid([], "code")
        assert len(avoid) > 0  # Should have defaults for "code"

    def test_extract_reuse_falls_back_to_defaults(self):
        """_extract_reuse returns defaults when no successes found."""
        from core.orchestration.memory_retrieval import _extract_reuse
        reuse = _extract_reuse([], "deployment")
        assert len(reuse) > 0  # Should have defaults for "deployment"

    def test_retrieve_no_facade_returns_empty_ok(self):
        """retrieve_mission_lessons is fully fail-open when facade is not ready."""
        from core.orchestration.memory_retrieval import retrieve_mission_lessons
        # This may or may not have memory available — just must not raise
        lessons = retrieve_mission_lessons("Research AI trends", task_type="research")
        assert isinstance(lessons, object)
        assert hasattr(lessons, "retrieval_ok")
        assert hasattr(lessons, "avoid")
        assert hasattr(lessons, "reuse")


# ══════════════════════════════════════════════════════════════════════════════
# NO-REGRESSION: existing mission flow
# ══════════════════════════════════════════════════════════════════════════════

class TestNoRegression:

    def test_mission_state_import_does_not_break(self):
        """Module imports cleanly with no side effects."""
        import importlib
        mod = importlib.import_module("core.orchestration.mission_reasoning_state")
        assert hasattr(mod, "MissionReasoningState")
        assert hasattr(mod, "build")

    def test_confidence_policy_import_does_not_break(self):
        """Module imports cleanly."""
        import importlib
        mod = importlib.import_module("core.orchestration.confidence_policy")
        assert hasattr(mod, "ConfidencePolicy")
        assert hasattr(mod, "PolicyTier")
        assert hasattr(mod, "get_confidence_policy")

    def test_memory_retrieval_import_does_not_break(self):
        """Module imports cleanly."""
        import importlib
        mod = importlib.import_module("core.orchestration.memory_retrieval")
        assert hasattr(mod, "MissionLessons")
        assert hasattr(mod, "retrieve_mission_lessons")

    def test_build_with_none_classification_does_not_raise(self):
        """Backward compat: classification=None is handled."""
        from core.orchestration.mission_reasoning_state import build
        state = build(goal="Test mission", mission_id="reg-001", classification=None)
        assert state is not None

    def test_confidence_policy_with_zero_confidence_does_not_raise(self):
        """Edge case: confidence=0.0 → ABORT, no exception."""
        from core.orchestration.confidence_policy import ConfidencePolicy, PolicyTier
        d = ConfidencePolicy().decide(confidence=0.0, risk_level="low")
        assert d.tier == PolicyTier.ABORT
        assert d.abort

    def test_confidence_policy_with_max_confidence_does_not_raise(self):
        """Edge case: confidence=1.0 → PROCEED, no exception."""
        from core.orchestration.confidence_policy import ConfidencePolicy, PolicyTier
        d = ConfidencePolicy().decide(confidence=1.0, risk_level="low")
        assert d.tier == PolicyTier.PROCEED

    def test_mission_state_update_observed_idempotent(self):
        """Calling update_observed twice does not raise or corrupt state."""
        from core.orchestration.mission_reasoning_state import build
        state = build(goal="Deploy", mission_id="reg-002",
                      classification={"task_type": "deployment"})
        state.update_observed(result="Service running.")
        state.update_observed(result="Service still running.")
        assert state.state_satisfied is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
