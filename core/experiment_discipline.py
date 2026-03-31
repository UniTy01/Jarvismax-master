"""
JARVIS MAX — Experiment Discipline Layer
==========================================
Strengthens the self-improvement loop into a disciplined autonomous maintainer.

Components:
1. ExperimentPrioritizer  — reliability-first, high-impact-first selection
2. HypothesisValidator    — one-hypothesis-one-experiment enforcement
3. PatchEvaluator         — baseline vs candidate scoring with deltas
4. LessonReuser           — past fix/failure pattern matching
5. PromotionGate          — multi-check promotion decision
6. ExperimentReport       — structured report per experiment

Design: composable helpers consumed by JarvisImprovementLoop.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


# ═══════════════════════════════════════════════════════════════
# 1. EXPERIMENT PRIORITIZER
# ═══════════════════════════════════════════════════════════════

class ExperimentCategory(str, Enum):
    RELIABILITY_FIX = "reliability_fix"       # crashes, errors, timeouts
    PERFORMANCE_FIX = "performance_fix"       # latency, cost
    QUALITY_IMPROVEMENT = "quality_improvement" # output quality
    COSMETIC = "cosmetic"                      # formatting, naming
    LOW_VALUE = "low_value"                    # micro-optimization, noise


# Category → priority weight (higher = more important)
_CATEGORY_WEIGHTS = {
    ExperimentCategory.RELIABILITY_FIX: 1.0,
    ExperimentCategory.PERFORMANCE_FIX: 0.7,
    ExperimentCategory.QUALITY_IMPROVEMENT: 0.5,
    ExperimentCategory.COSMETIC: 0.1,
    ExperimentCategory.LOW_VALUE: 0.0,
}

# Strategies classified by category
_STRATEGY_CATEGORY = {
    "timeout_tuning": ExperimentCategory.RELIABILITY_FIX,
    "retry_optimization": ExperimentCategory.RELIABILITY_FIX,
    "error_handling": ExperimentCategory.RELIABILITY_FIX,
    "performance_fix": ExperimentCategory.PERFORMANCE_FIX,
    "general_fix": ExperimentCategory.QUALITY_IMPROVEMENT,
    "formatting": ExperimentCategory.COSMETIC,
    "naming": ExperimentCategory.COSMETIC,
    "micro_optimization": ExperimentCategory.LOW_VALUE,
}


@dataclass
class PrioritizedExperiment:
    """An experiment ranked by disciplined prioritization."""
    task_id: str
    category: str
    priority_score: float     # 0.0-1.0
    frequency: int            # how often this issue occurs
    impact_estimate: float    # estimated improvement 0.0-1.0
    reason: str               # why this was prioritized

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "category": self.category,
            "priority_score": round(self.priority_score, 3),
            "frequency": self.frequency,
            "impact_estimate": round(self.impact_estimate, 3),
            "reason": self.reason[:200],
        }


class ExperimentPrioritizer:
    """
    Ranks experiments: reliability > performance > quality > cosmetic.
    Rejects low-value experiments entirely.
    Uses frequency × impact × category_weight for composite score.
    """

    MIN_FREQUENCY = 2       # Must occur at least twice
    MIN_IMPACT = 0.1        # Must have >10% estimated impact

    def prioritize(self, tasks: list[dict]) -> list[PrioritizedExperiment]:
        """Rank and filter experiments from ImprovementTasks."""
        experiments = []
        for task in tasks:
            strategy = task.get("suggested_strategy", task.get("strategy", "general_fix"))
            category = _STRATEGY_CATEGORY.get(strategy, ExperimentCategory.QUALITY_IMPROVEMENT)
            weight = _CATEGORY_WEIGHTS.get(category, 0.3)

            # Reject low-value
            if category == ExperimentCategory.LOW_VALUE:
                continue

            frequency = task.get("frequency", 1)
            if frequency < self.MIN_FREQUENCY and category != ExperimentCategory.RELIABILITY_FIX:
                continue

            # Compute impact estimate
            confidence = task.get("confidence_score", task.get("confidence", 0.5))
            risk = task.get("risk_level", "medium")
            risk_factor = {"low": 1.0, "medium": 0.7, "high": 0.4}.get(risk, 0.5)

            impact = min(1.0, confidence * risk_factor)
            if impact < self.MIN_IMPACT:
                continue

            # Composite priority
            freq_norm = min(1.0, frequency / 10)
            priority = weight * 0.4 + freq_norm * 0.3 + impact * 0.3

            reason_parts = []
            if category == ExperimentCategory.RELIABILITY_FIX:
                reason_parts.append("Reliability fix (highest priority)")
            reason_parts.append(f"frequency={frequency}")
            reason_parts.append(f"impact={impact:.0%}")
            reason_parts.append(f"category={category}")

            experiments.append(PrioritizedExperiment(
                task_id=task.get("id", ""),
                category=category,
                priority_score=priority,
                frequency=frequency,
                impact_estimate=impact,
                reason=", ".join(reason_parts),
            ))

        experiments.sort(key=lambda e: e.priority_score, reverse=True)
        return experiments


# ═══════════════════════════════════════════════════════════════
# 2. HYPOTHESIS VALIDATOR
# ═══════════════════════════════════════════════════════════════

@dataclass
class Hypothesis:
    """Single, testable hypothesis for an experiment."""
    experiment_id: str
    weakness: str        # What problem are we fixing?
    change: str          # What specific change are we making?
    expected_gain: str   # What measurable improvement do we expect?
    metric: str          # Which metric will we measure?
    max_files: int = 3   # Bounded scope

    def to_dict(self) -> dict:
        return {
            "experiment_id": self.experiment_id,
            "weakness": self.weakness[:200],
            "change": self.change[:200],
            "expected_gain": self.expected_gain[:200],
            "metric": self.metric,
            "max_files": self.max_files,
        }


class HypothesisValidator:
    """
    Enforces: one experiment = one hypothesis.
    Rejects multi-target or unbounded experiments.
    """

    MAX_FILES = 3
    MAX_DESCRIPTION_LENGTH = 500

    def validate(self, hypothesis: Hypothesis) -> tuple[bool, list[str]]:
        """Validate a hypothesis. Returns (valid, errors)."""
        errors = []

        if not hypothesis.weakness:
            errors.append("Missing weakness description")
        if not hypothesis.change:
            errors.append("Missing change description")
        if not hypothesis.expected_gain:
            errors.append("Missing expected gain")
        if not hypothesis.metric:
            errors.append("Missing target metric")

        if hypothesis.max_files > self.MAX_FILES:
            errors.append(f"Scope too large: {hypothesis.max_files} files (max {self.MAX_FILES})")

        # Check for multi-target (multiple 'and' in change)
        if hypothesis.change.lower().count(" and ") >= 2:
            errors.append("Hypothesis appears to target multiple changes (keep it to one)")

        return len(errors) == 0, errors

    def create_from_task(self, task: dict) -> Hypothesis:
        """Create a well-formed hypothesis from an ImprovementTask."""
        strategy = task.get("suggested_strategy", task.get("strategy", ""))
        problem = task.get("problem_description", task.get("problem", ""))
        files = task.get("target_files", [])

        # Map strategy to metric
        metric_map = {
            "timeout_tuning": "timeout_rate",
            "retry_optimization": "retry_rate",
            "error_handling": "exception_count",
            "performance_fix": "avg_latency_ms",
            "general_fix": "success_rate",
        }
        metric = metric_map.get(strategy, "success_rate")

        # Map strategy to expected gain
        gain_map = {
            "timeout_tuning": "Reduce timeout rate by increasing timeout values",
            "retry_optimization": "Reduce retry waste by optimizing retry policy",
            "error_handling": "Reduce unhandled exceptions with proper error handling",
            "performance_fix": "Reduce average latency",
            "general_fix": "Improve overall success rate",
        }
        expected_gain = gain_map.get(strategy, "Improve targeted metric")

        return Hypothesis(
            experiment_id=task.get("id", ""),
            weakness=problem[:200],
            change=f"Apply {strategy} to {', '.join(files[:2])}",
            expected_gain=expected_gain,
            metric=metric,
            max_files=min(len(files), self.MAX_FILES),
        )


# ═══════════════════════════════════════════════════════════════
# 3. PATCH EVALUATOR
# ═══════════════════════════════════════════════════════════════

@dataclass
class ScoreSnapshot:
    """Point-in-time score for comparison."""
    overall: float = 0.0
    dimensions: dict[str, float] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class PatchEvaluation:
    """Baseline vs candidate comparison."""
    experiment_id: str = ""
    baseline: ScoreSnapshot = field(default_factory=ScoreSnapshot)
    candidate: ScoreSnapshot = field(default_factory=ScoreSnapshot)
    score_delta: float = 0.0
    risk_delta: float = 0.0
    regression_risk: str = "none"   # none, low, medium, high
    improved_dimensions: list[str] = field(default_factory=list)
    regressed_dimensions: list[str] = field(default_factory=list)
    verdict: str = ""              # promote, reject, review

    def to_dict(self) -> dict:
        return {
            "experiment_id": self.experiment_id,
            "baseline_score": round(self.baseline.overall, 2),
            "candidate_score": round(self.candidate.overall, 2),
            "score_delta": round(self.score_delta, 2),
            "risk_delta": round(self.risk_delta, 2),
            "regression_risk": self.regression_risk,
            "improved": self.improved_dimensions,
            "regressed": self.regressed_dimensions,
            "verdict": self.verdict,
        }


class PatchEvaluator:
    """
    Compares baseline vs candidate scores to decide patch fate.
    Shows clear deltas and regression risk.
    """

    MIN_IMPROVEMENT = 0.1      # Score must improve by at least 0.1
    REGRESSION_THRESHOLD = -0.2  # Any dimension drop > 0.2 = regression risk

    def evaluate(self, experiment_id: str, baseline: ScoreSnapshot,
                 candidate: ScoreSnapshot) -> PatchEvaluation:
        """Compare baseline vs candidate."""
        score_delta = candidate.overall - baseline.overall
        improved = []
        regressed = []

        for dim, val in candidate.dimensions.items():
            base_val = baseline.dimensions.get(dim, val)
            delta = val - base_val
            if delta > 0.05:
                improved.append(dim)
            elif delta < -0.05:
                regressed.append(dim)

        # Risk assessment
        worst_regression = 0.0
        for dim in regressed:
            base_val = baseline.dimensions.get(dim, 0)
            cand_val = candidate.dimensions.get(dim, 0)
            worst_regression = min(worst_regression, cand_val - base_val)

        if worst_regression < -1.0:
            regression_risk = "high"
        elif worst_regression < -0.5:
            regression_risk = "medium"
        elif worst_regression < -0.2:
            regression_risk = "low"
        else:
            regression_risk = "none"

        # Verdict
        if score_delta < 0 and regression_risk in ("medium", "high"):
            verdict = "reject"
        elif score_delta < self.MIN_IMPROVEMENT and regression_risk != "none":
            verdict = "reject"
        elif score_delta >= self.MIN_IMPROVEMENT and regression_risk == "none":
            verdict = "promote"
        elif score_delta >= 0 and len(regressed) > 0:
            verdict = "review"  # Improved overall but some regression
        else:
            verdict = "review"

        risk_delta = abs(worst_regression) if worst_regression < 0 else 0

        return PatchEvaluation(
            experiment_id=experiment_id,
            baseline=baseline,
            candidate=candidate,
            score_delta=score_delta,
            risk_delta=risk_delta,
            regression_risk=regression_risk,
            improved_dimensions=improved,
            regressed_dimensions=regressed,
            verdict=verdict,
        )


# ═══════════════════════════════════════════════════════════════
# 4. LESSON REUSER
# ═══════════════════════════════════════════════════════════════

@dataclass
class LessonMatch:
    """A matched past lesson."""
    lesson_id: str
    problem: str
    strategy: str
    result: str     # success, failure
    similarity: float  # 0-1
    reuse_advice: str

    def to_dict(self) -> dict:
        return {
            "lesson_id": self.lesson_id,
            "problem": self.problem[:100],
            "strategy": self.strategy,
            "result": self.result,
            "similarity": round(self.similarity, 3),
            "advice": self.reuse_advice[:200],
        }


class LessonReuser:
    """
    Matches current experiment against past lessons.
    Advises: reuse successful patterns, avoid failed ones.
    """

    # Cooldown: don't retry the same failed strategy within N cycles
    FAILURE_COOLDOWN = 5

    def __init__(self):
        self._failure_tracker: dict[str, int] = {}  # strategy → last_failure_cycle

    def find_matches(self, problem: str, strategy: str,
                     lessons: list[dict], current_cycle: int = 0) -> list[LessonMatch]:
        """Find past lessons similar to current experiment."""
        matches = []
        problem_words = set(problem.lower().split())

        for lesson in lessons:
            lesson_problem = lesson.get("problem", "")
            lesson_words = set(lesson_problem.lower().split())

            overlap = len(problem_words & lesson_words)
            if overlap == 0:
                continue

            similarity = overlap / max(len(problem_words), 1)
            if similarity < 0.2:
                continue

            result = lesson.get("result", "")
            lesson_strategy = lesson.get("strategy", "")

            # Generate advice
            if result == "success" and lesson_strategy == strategy:
                advice = f"Reuse: same strategy '{strategy}' succeeded before"
            elif result == "failure" and lesson_strategy == strategy:
                advice = f"Warning: strategy '{strategy}' failed before — consider alternative"
            elif result == "success":
                advice = f"Related success with different strategy: {lesson_strategy}"
            else:
                advice = f"Related failure: {lesson_strategy}"

            matches.append(LessonMatch(
                lesson_id=lesson.get("task_id", ""),
                problem=lesson_problem,
                strategy=lesson_strategy,
                result=result,
                similarity=similarity,
                reuse_advice=advice,
            ))

        matches.sort(key=lambda m: m.similarity, reverse=True)
        return matches[:5]

    def should_skip(self, strategy: str, problem: str,
                    lessons: list[dict], current_cycle: int = 0) -> tuple[bool, str]:
        """Check if this experiment should be skipped based on past failures."""
        # Check cooldown
        last_fail = self._failure_tracker.get(strategy, -999)
        if current_cycle - last_fail < self.FAILURE_COOLDOWN:
            return True, f"Strategy '{strategy}' failed recently (cycle {last_fail}), cooldown active"

        # Check if same strategy failed >2 times on similar problems
        matches = self.find_matches(problem, strategy, lessons)
        same_strategy_failures = [
            m for m in matches
            if m.strategy == strategy and m.result == "failure" and m.similarity > 0.5
        ]
        if len(same_strategy_failures) >= 2:
            return True, f"Strategy '{strategy}' failed {len(same_strategy_failures)} times on similar problems"

        return False, "ok"

    def record_failure(self, strategy: str, cycle: int) -> None:
        self._failure_tracker[strategy] = cycle

    def record_success(self, strategy: str) -> None:
        # Reset cooldown on success
        self._failure_tracker.pop(strategy, None)


# ═══════════════════════════════════════════════════════════════
# 5. PROMOTION GATE
# ═══════════════════════════════════════════════════════════════

@dataclass
class PromotionDecision:
    """Structured promotion decision."""
    promote: bool
    reason: str
    checks_passed: list[str]
    checks_failed: list[str]
    requires_approval: bool = False

    def to_dict(self) -> dict:
        return {
            "promote": self.promote,
            "reason": self.reason[:300],
            "checks_passed": self.checks_passed,
            "checks_failed": self.checks_failed,
            "requires_approval": self.requires_approval,
        }


class PromotionGate:
    """
    Multi-check promotion decision.
    All checks must pass for auto-promotion.
    """

    def decide(self, evaluation: PatchEvaluation, hypothesis: Hypothesis,
               sandbox_passed: bool = True, lesson_skip: bool = False) -> PromotionDecision:
        """Run all promotion checks."""
        passed = []
        failed = []

        # Check 1: Sandbox
        if sandbox_passed:
            passed.append("sandbox_passed")
        else:
            failed.append("sandbox_failed")

        # Check 2: Score improved
        if evaluation.score_delta >= 0:
            passed.append("score_improved_or_stable")
        else:
            failed.append(f"score_regressed ({evaluation.score_delta:+.2f})")

        # Check 3: No regression
        if evaluation.regression_risk in ("none", "low"):
            passed.append("no_significant_regression")
        else:
            failed.append(f"regression_risk={evaluation.regression_risk}")

        # Check 4: Evaluation verdict
        if evaluation.verdict == "promote":
            passed.append("evaluator_promotes")
        elif evaluation.verdict == "review":
            passed.append("evaluator_review")
        else:
            failed.append("evaluator_rejects")

        # Check 5: Lesson skip
        if not lesson_skip:
            passed.append("no_lesson_conflict")
        else:
            failed.append("lesson_conflict_detected")

        # Check 6: Scope bounded
        if hypothesis.max_files <= 3:
            passed.append("scope_bounded")
        else:
            failed.append(f"scope_too_large ({hypothesis.max_files} files)")

        # Decision
        if not failed:
            return PromotionDecision(
                promote=True,
                reason=f"All {len(passed)} checks passed",
                checks_passed=passed,
                checks_failed=failed,
            )

        # Partial pass → needs approval
        if len(failed) == 1 and "review" in failed[0]:
            return PromotionDecision(
                promote=False,
                reason=f"Needs review: {failed[0]}",
                checks_passed=passed,
                checks_failed=failed,
                requires_approval=True,
            )

        return PromotionDecision(
            promote=False,
            reason=f"{len(failed)} check(s) failed: {', '.join(failed)}",
            checks_passed=passed,
            checks_failed=failed,
        )


# ═══════════════════════════════════════════════════════════════
# 6. EXPERIMENT REPORT
# ═══════════════════════════════════════════════════════════════

@dataclass
class ExperimentReport:
    """Structured report for one experiment cycle."""
    experiment_id: str
    cycle: int

    # Why chosen
    hypothesis: dict = field(default_factory=dict)
    prioritization: dict = field(default_factory=dict)
    lesson_matches: list[dict] = field(default_factory=list)

    # What changed
    files_changed: list[str] = field(default_factory=list)
    strategy: str = ""

    # What improved
    evaluation: dict = field(default_factory=dict)
    score_before: float = 0.0
    score_after: float = 0.0

    # Decision
    promotion: dict = field(default_factory=dict)
    outcome: str = ""  # promoted, rejected, review_pending

    duration_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "experiment_id": self.experiment_id,
            "cycle": self.cycle,
            "hypothesis": self.hypothesis,
            "prioritization": self.prioritization,
            "lesson_matches": self.lesson_matches[:3],
            "files_changed": self.files_changed,
            "strategy": self.strategy,
            "evaluation": self.evaluation,
            "score_before": round(self.score_before, 2),
            "score_after": round(self.score_after, 2),
            "promotion": self.promotion,
            "outcome": self.outcome,
            "duration_ms": round(self.duration_ms, 1),
        }

    def summary(self) -> str:
        """Human-readable experiment summary."""
        lines = [
            f"═══ Experiment {self.experiment_id} (cycle {self.cycle}) ═══",
            "",
            f"🎯 WHY CHOSEN:",
            f"   Weakness: {self.hypothesis.get('weakness', '?')[:80]}",
            f"   Priority: {self.prioritization.get('priority_score', '?')} "
            f"({self.prioritization.get('category', '?')})",
        ]

        if self.lesson_matches:
            lines.append(f"   Past lessons: {len(self.lesson_matches)} relevant")
            for lm in self.lesson_matches[:2]:
                lines.append(f"     → {lm.get('advice', '')[:60]}")

        lines.extend([
            "",
            f"🔧 WHAT CHANGED:",
            f"   Strategy: {self.strategy}",
            f"   Files: {', '.join(self.files_changed[:3])}",
            "",
            f"📊 WHAT IMPROVED:",
            f"   Score: {self.score_before:.1f} → {self.score_after:.1f} "
            f"(Δ{self.score_after - self.score_before:+.1f})",
        ])

        eval_data = self.evaluation
        if eval_data.get("improved"):
            lines.append(f"   ✅ Improved: {', '.join(eval_data['improved'])}")
        if eval_data.get("regressed"):
            lines.append(f"   ⚠️ Regressed: {', '.join(eval_data['regressed'])}")

        lines.extend([
            "",
            f"{'✅' if self.outcome == 'promoted' else '❌' if self.outcome == 'rejected' else '⏳'} "
            f"OUTCOME: {self.outcome.upper()}",
            f"   Reason: {self.promotion.get('reason', '?')[:80]}",
        ])

        return "\n".join(lines)
