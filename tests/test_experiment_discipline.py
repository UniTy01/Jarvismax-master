"""
Tests — Experiment Discipline

Prioritization
  D1.  Reliability fix prioritized over cosmetic
  D2.  Low-value experiments rejected
  D3.  Low-frequency non-reliability rejected
  D4.  High impact scored higher

Hypothesis Enforcement
  D5.  Valid hypothesis passes
  D6.  Missing fields rejected
  D7.  Multi-target hypothesis rejected
  D8.  Scope too large rejected
  D9.  Create from task produces valid hypothesis

Patch Evaluation
  D10. Score improvement → promote verdict
  D11. Score regression → reject verdict
  D12. Mixed (improve overall, regress dimension) → review
  D13. No change → review
  D14. Improved/regressed dimensions tracked

Lesson Reuse
  D15. Find similar past lessons
  D16. Skip strategy that failed twice on similar problem
  D17. Cooldown prevents re-trying too soon
  D18. Success resets cooldown
  D19. Advice includes reuse/warning

Promotion Gate
  D20. All checks pass → promote
  D21. Sandbox fail → reject
  D22. Regression → reject
  D23. Lesson conflict → reject
  D24. Scope too large → reject

Rollback
  D25. Rejected experiment not promoted

Report
  D26. Report has all fields
  D27. Summary text includes all sections
  D28. Summary includes score delta

Integration
  D29. Full pipeline: prioritize → hypothesis → evaluate → promote
  D30. Low-value → never reaches evaluation
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.experiment_discipline import (
    ExperimentCategory, PrioritizedExperiment, ExperimentPrioritizer,
    Hypothesis, HypothesisValidator,
    ScoreSnapshot, PatchEvaluation, PatchEvaluator,
    LessonMatch, LessonReuser,
    PromotionDecision, PromotionGate,
    ExperimentReport,
)


# ═══════════════════════════════════════════════════════════════
# PRIORITIZATION
# ═══════════════════════════════════════════════════════════════

class TestPrioritization:

    def test_reliability_over_cosmetic(self):
        """D1: Reliability fix prioritized over cosmetic."""
        p = ExperimentPrioritizer()
        tasks = [
            {"id": "t1", "suggested_strategy": "formatting", "frequency": 5, "confidence_score": 0.8},
            {"id": "t2", "suggested_strategy": "timeout_tuning", "frequency": 5, "confidence_score": 0.8},
        ]
        result = p.prioritize(tasks)
        # Timeout (reliability) should be first
        ids = [r.task_id for r in result]
        assert ids[0] == "t2"

    def test_low_value_rejected(self):
        """D2: Low-value experiments rejected."""
        p = ExperimentPrioritizer()
        tasks = [
            {"id": "low", "suggested_strategy": "micro_optimization", "frequency": 10},
        ]
        result = p.prioritize(tasks)
        assert len(result) == 0

    def test_low_frequency_rejected(self):
        """D3: Low-frequency non-reliability rejected."""
        p = ExperimentPrioritizer()
        tasks = [
            {"id": "rare", "suggested_strategy": "general_fix", "frequency": 1, "confidence_score": 0.5},
        ]
        result = p.prioritize(tasks)
        assert len(result) == 0

    def test_high_impact_higher(self):
        """D4: High impact scored higher."""
        p = ExperimentPrioritizer()
        tasks = [
            {"id": "low_impact", "suggested_strategy": "error_handling", "frequency": 3, "confidence_score": 0.3, "risk_level": "high"},
            {"id": "high_impact", "suggested_strategy": "error_handling", "frequency": 10, "confidence_score": 0.9, "risk_level": "low"},
        ]
        result = p.prioritize(tasks)
        assert result[0].task_id == "high_impact"


# ═══════════════════════════════════════════════════════════════
# HYPOTHESIS ENFORCEMENT
# ═══════════════════════════════════════════════════════════════

class TestHypothesis:

    def test_valid(self):
        """D5: Valid hypothesis passes."""
        h = Hypothesis(
            experiment_id="e1", weakness="Timeout in tool_executor",
            change="Increase timeout from 30s to 45s",
            expected_gain="Reduce timeout rate", metric="timeout_rate",
        )
        valid, errors = HypothesisValidator().validate(h)
        assert valid
        assert len(errors) == 0

    def test_missing_fields(self):
        """D6: Missing fields rejected."""
        h = Hypothesis(experiment_id="e2", weakness="", change="", expected_gain="", metric="")
        valid, errors = HypothesisValidator().validate(h)
        assert not valid
        assert len(errors) >= 4

    def test_multi_target(self):
        """D7: Multi-target rejected."""
        h = Hypothesis(
            experiment_id="e3",
            weakness="Multiple issues",
            change="Fix timeouts and retries and error handling and caching",
            expected_gain="Everything better", metric="all",
        )
        valid, errors = HypothesisValidator().validate(h)
        assert not valid

    def test_scope_too_large(self):
        """D8: Scope too large rejected."""
        h = Hypothesis(
            experiment_id="e4", weakness="Big problem",
            change="Rewrite everything", expected_gain="Better",
            metric="all", max_files=10,
        )
        valid, errors = HypothesisValidator().validate(h)
        assert not valid

    def test_create_from_task(self):
        """D9: Create from task produces valid hypothesis."""
        task = {
            "id": "task-1",
            "suggested_strategy": "timeout_tuning",
            "problem_description": "Recurring timeouts in tool_executor",
            "target_files": ["core/tool_executor.py"],
        }
        h = HypothesisValidator().create_from_task(task)
        assert h.metric == "timeout_rate"
        assert h.weakness
        valid, _ = HypothesisValidator().validate(h)
        assert valid


# ═══════════════════════════════════════════════════════════════
# PATCH EVALUATION
# ═══════════════════════════════════════════════════════════════

class TestPatchEvaluation:

    def test_improvement_promotes(self):
        """D10: Score improvement → promote."""
        ev = PatchEvaluator()
        baseline = ScoreSnapshot(overall=7.0, dimensions={"stability": 6.0, "cost": 8.0})
        candidate = ScoreSnapshot(overall=7.5, dimensions={"stability": 7.0, "cost": 8.0})
        result = ev.evaluate("e1", baseline, candidate)
        assert result.verdict == "promote"
        assert result.score_delta > 0

    def test_regression_rejects(self):
        """D11: Score regression → reject."""
        ev = PatchEvaluator()
        baseline = ScoreSnapshot(overall=8.0, dimensions={"stability": 8.0, "cost": 8.0})
        candidate = ScoreSnapshot(overall=7.0, dimensions={"stability": 6.0, "cost": 7.0})
        result = ev.evaluate("e2", baseline, candidate)
        assert result.verdict == "reject"

    def test_mixed_review(self):
        """D12: Mixed → review."""
        ev = PatchEvaluator()
        baseline = ScoreSnapshot(overall=7.0, dimensions={"stability": 7.0, "cost": 7.0})
        candidate = ScoreSnapshot(overall=7.2, dimensions={"stability": 8.0, "cost": 6.5})
        result = ev.evaluate("e3", baseline, candidate)
        assert result.verdict == "review"
        assert "cost" in result.regressed_dimensions

    def test_no_change_review(self):
        """D13: No change → review."""
        ev = PatchEvaluator()
        baseline = ScoreSnapshot(overall=7.0, dimensions={"stability": 7.0})
        candidate = ScoreSnapshot(overall=7.05, dimensions={"stability": 7.0})
        result = ev.evaluate("e4", baseline, candidate)
        assert result.verdict == "review"

    def test_dimensions_tracked(self):
        """D14: Improved/regressed dimensions tracked."""
        ev = PatchEvaluator()
        baseline = ScoreSnapshot(overall=7.0, dimensions={"a": 5.0, "b": 8.0, "c": 6.0})
        candidate = ScoreSnapshot(overall=7.5, dimensions={"a": 7.0, "b": 7.0, "c": 6.0})
        result = ev.evaluate("e5", baseline, candidate)
        assert "a" in result.improved_dimensions
        assert "b" in result.regressed_dimensions


# ═══════════════════════════════════════════════════════════════
# LESSON REUSE
# ═══════════════════════════════════════════════════════════════

class TestLessonReuse:

    LESSONS = [
        {"task_id": "l1", "problem": "Timeout in executor tool",
         "strategy": "timeout_tuning", "result": "success"},
        {"task_id": "l2", "problem": "Timeout in executor tool handler",
         "strategy": "retry_optimization", "result": "failure"},
        {"task_id": "l3", "problem": "Memory leak in cache module",
         "strategy": "performance_fix", "result": "success"},
    ]

    def test_find_similar(self):
        """D15: Find similar past lessons."""
        lr = LessonReuser()
        matches = lr.find_matches("Timeout in executor", "timeout_tuning", self.LESSONS)
        assert len(matches) >= 1
        assert matches[0].similarity > 0.3

    def test_skip_failed_strategy(self):
        """D16: Skip strategy that failed twice."""
        lessons = self.LESSONS + [
            {"task_id": "l4", "problem": "Timeout in executor handler",
             "strategy": "retry_optimization", "result": "failure"},
        ]
        lr = LessonReuser()
        skip, reason = lr.should_skip("retry_optimization", "Timeout in executor", lessons)
        assert skip
        assert "failed" in reason.lower()

    def test_cooldown(self):
        """D17: Cooldown prevents re-trying."""
        lr = LessonReuser()
        lr.record_failure("timeout_tuning", cycle=10)
        skip, reason = lr.should_skip("timeout_tuning", "Different problem", [], current_cycle=12)
        assert skip
        assert "cooldown" in reason.lower()

    def test_success_resets(self):
        """D18: Success resets cooldown."""
        lr = LessonReuser()
        lr.record_failure("timeout_tuning", cycle=5)
        lr.record_success("timeout_tuning")
        skip, _ = lr.should_skip("timeout_tuning", "New problem", [], current_cycle=6)
        assert not skip

    def test_advice_content(self):
        """D19: Advice includes reuse/warning."""
        lr = LessonReuser()
        matches = lr.find_matches("Timeout in executor", "timeout_tuning", self.LESSONS)
        assert len(matches) >= 1
        assert any("Reuse" in m.reuse_advice or "Warning" in m.reuse_advice for m in matches)


# ═══════════════════════════════════════════════════════════════
# PROMOTION GATE
# ═══════════════════════════════════════════════════════════════

class TestPromotionGate:

    def _make_eval(self, delta=0.5, regression="none", verdict="promote"):
        return PatchEvaluation(
            experiment_id="test",
            baseline=ScoreSnapshot(overall=7.0),
            candidate=ScoreSnapshot(overall=7.0 + delta),
            score_delta=delta,
            regression_risk=regression,
            verdict=verdict,
        )

    def _make_hyp(self, files=1):
        return Hypothesis(experiment_id="test", weakness="w", change="c",
                          expected_gain="g", metric="m", max_files=files)

    def test_all_pass(self):
        """D20: All checks pass → promote."""
        gate = PromotionGate()
        d = gate.decide(self._make_eval(), self._make_hyp())
        assert d.promote
        assert len(d.checks_failed) == 0

    def test_sandbox_fail(self):
        """D21: Sandbox fail → reject."""
        gate = PromotionGate()
        d = gate.decide(self._make_eval(), self._make_hyp(), sandbox_passed=False)
        assert not d.promote

    def test_regression_reject(self):
        """D22: Regression → reject."""
        gate = PromotionGate()
        d = gate.decide(self._make_eval(delta=-0.5, regression="high", verdict="reject"),
                        self._make_hyp())
        assert not d.promote

    def test_lesson_conflict(self):
        """D23: Lesson conflict → reject."""
        gate = PromotionGate()
        d = gate.decide(self._make_eval(), self._make_hyp(), lesson_skip=True)
        assert not d.promote

    def test_scope_large(self):
        """D24: Scope too large → reject."""
        gate = PromotionGate()
        d = gate.decide(self._make_eval(), self._make_hyp(files=5))
        assert not d.promote


# ═══════════════════════════════════════════════════════════════
# ROLLBACK
# ═══════════════════════════════════════════════════════════════

class TestRollback:

    def test_rejected_not_promoted(self):
        """D25: Rejected experiment not promoted."""
        gate = PromotionGate()
        ev = PatchEvaluation(
            experiment_id="bad",
            baseline=ScoreSnapshot(overall=8.0),
            candidate=ScoreSnapshot(overall=6.0),
            score_delta=-2.0,
            regression_risk="high",
            verdict="reject",
        )
        h = Hypothesis(experiment_id="bad", weakness="w", change="c",
                       expected_gain="g", metric="m")
        d = gate.decide(ev, h)
        assert not d.promote
        assert "regress" in d.reason.lower() or "reject" in d.reason.lower() or len(d.checks_failed) > 0


# ═══════════════════════════════════════════════════════════════
# REPORT
# ═══════════════════════════════════════════════════════════════

class TestReport:

    def test_report_fields(self):
        """D26: Report has all fields."""
        r = ExperimentReport(
            experiment_id="exp-001", cycle=1,
            hypothesis={"weakness": "timeouts", "change": "increase timeout"},
            strategy="timeout_tuning",
            files_changed=["core/tool_executor.py"],
            score_before=7.0, score_after=7.5,
            outcome="promoted",
        )
        d = r.to_dict()
        assert "experiment_id" in d
        assert "hypothesis" in d
        assert "score_before" in d
        assert "outcome" in d

    def test_summary_sections(self):
        """D27: Summary includes all sections."""
        r = ExperimentReport(
            experiment_id="exp-002", cycle=3,
            hypothesis={"weakness": "high retry rate"},
            prioritization={"priority_score": 0.85, "category": "reliability_fix"},
            strategy="retry_optimization",
            files_changed=["executor/retry_policy.py"],
            evaluation={"improved": ["stability"], "regressed": []},
            promotion={"reason": "All checks passed"},
            score_before=7.0, score_after=7.8,
            outcome="promoted",
        )
        text = r.summary()
        assert "WHY CHOSEN" in text
        assert "WHAT CHANGED" in text
        assert "WHAT IMPROVED" in text
        assert "OUTCOME" in text

    def test_summary_score_delta(self):
        """D28: Summary includes score delta."""
        r = ExperimentReport(
            experiment_id="exp-003", cycle=1,
            hypothesis={"weakness": "slow"},
            score_before=6.0, score_after=7.5,
            outcome="promoted",
            promotion={"reason": "ok"},
        )
        text = r.summary()
        assert "6.0" in text
        assert "7.5" in text


# ═══════════════════════════════════════════════════════════════
# INTEGRATION
# ═══════════════════════════════════════════════════════════════

class TestIntegration:

    def test_full_pipeline(self):
        """D29: Full pipeline: prioritize → hypothesis → evaluate → promote."""
        # 1. Prioritize
        prioritizer = ExperimentPrioritizer()
        tasks = [{"id": "t1", "suggested_strategy": "timeout_tuning",
                  "frequency": 5, "confidence_score": 0.8,
                  "risk_level": "low", "problem_description": "Timeouts in executor",
                  "target_files": ["core/tool_executor.py"]}]
        ranked = prioritizer.prioritize(tasks)
        assert len(ranked) == 1
        assert ranked[0].category == ExperimentCategory.RELIABILITY_FIX

        # 2. Hypothesis
        validator = HypothesisValidator()
        hyp = validator.create_from_task(tasks[0])
        valid, errors = validator.validate(hyp)
        assert valid

        # 3. Evaluate
        evaluator = PatchEvaluator()
        baseline = ScoreSnapshot(overall=7.0, dimensions={"stability": 6.0})
        candidate = ScoreSnapshot(overall=7.5, dimensions={"stability": 7.5})
        eval_result = evaluator.evaluate("t1", baseline, candidate)
        assert eval_result.score_delta > 0

        # 4. Promote
        gate = PromotionGate()
        decision = gate.decide(eval_result, hyp)
        assert decision.promote

    def test_low_value_never_evaluated(self):
        """D30: Low-value never reaches evaluation."""
        prioritizer = ExperimentPrioritizer()
        tasks = [{"id": "noise", "suggested_strategy": "micro_optimization", "frequency": 100}]
        ranked = prioritizer.prioritize(tasks)
        assert len(ranked) == 0
