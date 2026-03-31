"""Shadow-Advisor V2 — structured critical validator."""
from agents.shadow_advisor.schema import AdvisoryReport, parse_advisory, AdvisoryDecision
from agents.shadow_advisor.scorer import AdvisoryScorer

__all__ = ["AdvisoryReport", "parse_advisory", "AdvisoryDecision", "AdvisoryScorer"]
