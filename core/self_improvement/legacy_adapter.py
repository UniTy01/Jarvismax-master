"""
Self-improvement adapter — runs the canonical pipeline.
"""
import logging
logger = logging.getLogger(__name__)


def run_improve_cycle(context: dict = None) -> dict:
    """Run self-improvement cycle via canonical pipeline."""
    try:
        from core.self_improvement import check_improvement_allowed
        from core.self_improvement.weakness_detector import WeaknessDetector
        from core.self_improvement.candidate_generator import CandidateGenerator
        from core.self_improvement.improvement_scorer import ImprovementScorer
        from core.self_improvement.safe_executor import SafeSelfImprovementExecutor
        from core.self_improvement.improvement_memory import SelfImprovementMemory

        result_check = check_improvement_allowed()
        if not result_check.get("allowed", False):
            return {"status": "skipped", "reason": result_check.get("reason", "not_allowed")}

        detector = WeaknessDetector()
        weaknesses = detector.detect()
        if not weaknesses:
            return {"status": "no_weakness_detected"}

        generator = CandidateGenerator()
        candidates = generator.generate(weaknesses)
        if not candidates:
            return {"status": "no_candidates"}

        scorer = ImprovementScorer()
        ranked = scorer.rank(candidates)

        executor = SafeSelfImprovementExecutor()
        result = executor.execute(ranked[0])

        memory = SelfImprovementMemory()
        memory.record(
            candidate_type=getattr(ranked[0], "type", "UNKNOWN"),
            description=getattr(ranked[0], "description", ""),
            score=getattr(ranked[0], "score", 0.0),
            outcome="SUCCESS" if result.success else "FAILURE",
            applied_change=result.applied_change,
        )

        return {"status": "ok", "result": result.__dict__ if hasattr(result, "__dict__") else str(result)}

    except Exception as e:
        logger.error("[self_improvement] Pipeline failed: %s", e)
        return {"status": "error", "error": str(e)}
