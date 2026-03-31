"""
tests/test_business_capability.py — Business reasoning tests.

Covers: opportunity detection, offer structuring, compliance,
feasibility scoring, landing page, acquisition, classification.
"""
from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestBusinessClassification(unittest.TestCase):

    def test_business_mission_detected(self):
        from core.orchestration.mission_classifier import classify
        c = classify("Identify 3 simple business opportunities for freelance consulting")
        self.assertEqual(c.task_type.value, "business")

    def test_non_business_not_flagged(self):
        from core.orchestration.mission_classifier import classify
        c = classify("What is the capital of France?")
        self.assertNotEqual(c.task_type.value, "business")

    def test_business_value_score_high(self):
        from core.orchestration.mission_classifier import classify
        c = classify("Propose a SaaS business opportunity for small businesses")
        self.assertGreater(c.value_score, 0.5)


class TestBusinessIntentDetection(unittest.TestCase):

    def test_detects_business_keywords(self):
        from core.skills.business_reasoning import is_business_mission
        self.assertTrue(is_business_mission("Identify 3 business opportunities"))
        self.assertTrue(is_business_mission("Generate a landing page for my service"))
        self.assertTrue(is_business_mission("Create a customer acquisition strategy"))

    def test_rejects_non_business(self):
        from core.skills.business_reasoning import is_business_mission
        self.assertFalse(is_business_mission("What is Docker?"))
        self.assertFalse(is_business_mission("Fix the database connection"))


class TestFeasibilityScoring(unittest.TestCase):

    def test_automation_service_feasible(self):
        from core.skills.business_reasoning import estimate_feasibility, OpportunityType
        fs = estimate_feasibility(OpportunityType.AUTOMATION_SERVICE, "simple automation")
        self.assertGreater(fs.score, 0.5)

    def test_micro_saas_less_feasible(self):
        from core.skills.business_reasoning import estimate_feasibility, OpportunityType
        auto = estimate_feasibility(OpportunityType.AUTOMATION_SERVICE)
        saas = estimate_feasibility(OpportunityType.MICRO_SAAS)
        self.assertGreater(auto.score, saas.score)

    def test_content_service_fast(self):
        from core.skills.business_reasoning import estimate_feasibility, OpportunityType
        fs = estimate_feasibility(OpportunityType.CONTENT_SERVICE)
        self.assertLess(fs.time_to_first_result, 0.3)

    def test_score_bounded(self):
        from core.skills.business_reasoning import estimate_feasibility, OpportunityType
        for otype in OpportunityType:
            fs = estimate_feasibility(otype)
            self.assertGreaterEqual(fs.score, 0.0)
            self.assertLessEqual(fs.score, 1.0)

    def test_to_dict(self):
        from core.skills.business_reasoning import estimate_feasibility, OpportunityType
        fs = estimate_feasibility(OpportunityType.ANALYSIS_SERVICE)
        d = fs.to_dict()
        self.assertIn("overall_score", d)
        self.assertIn("complexity", d)


class TestComplianceChecks(unittest.TestCase):

    def test_gdpr_triggered(self):
        from core.skills.business_reasoning import (
            check_compliance, BusinessOpportunity,
        )
        opp = BusinessOpportunity(
            summary="Email newsletter service",
            solution="Collect emails and send newsletters",
        )
        notes = check_compliance(opp)
        gdpr_notes = [n for n in notes if "GDPR" in n]
        self.assertGreater(len(gdpr_notes), 0)

    def test_high_risk_flagged(self):
        from core.skills.business_reasoning import (
            check_compliance, BusinessOpportunity,
        )
        opp = BusinessOpportunity(
            summary="Investment advice platform",
            solution="Provide investment advice to retail investors",
        )
        notes = check_compliance(opp)
        caution_notes = [n for n in notes if "CAUTION" in n]
        self.assertGreater(len(caution_notes), 0)

    def test_always_includes_basics(self):
        from core.skills.business_reasoning import (
            check_compliance, BusinessOpportunity,
        )
        opp = BusinessOpportunity(summary="Simple service")
        notes = check_compliance(opp)
        # Should always include provider identity and no false claims
        provider_notes = [n for n in notes if "provider" in n.lower()]
        self.assertGreater(len(provider_notes), 0)


class TestOfferStructuring(unittest.TestCase):

    def test_opportunity_to_markdown(self):
        from core.skills.business_reasoning import (
            BusinessOpportunity, OpportunityType, FeasibilityScore,
        )
        opp = BusinessOpportunity(
            summary="AI Report Generation Service",
            target_customer="Small marketing agencies",
            problem="Agencies spend hours writing client reports manually",
            solution="AI-generated weekly client performance reports",
            value_proposition="Save 5 hours per week on reporting",
            opportunity_type=OpportunityType.AUTOMATION_SERVICE,
            delivery_format="Monthly subscription + dashboard",
            pricing_model="€99/month per client account",
            acquisition_idea="Direct outreach to agencies on LinkedIn",
            feasibility=FeasibilityScore(complexity=0.3, estimated_demand=0.7),
        )
        md = opp.to_markdown()
        self.assertIn("AI Report Generation", md)
        self.assertIn("marketing agencies", md)
        self.assertIn("€99", md)

    def test_opportunity_to_dict(self):
        from core.skills.business_reasoning import BusinessOpportunity
        opp = BusinessOpportunity(summary="Test")
        d = opp.to_dict()
        self.assertIn("summary", d)
        self.assertIn("feasibility", d)
        self.assertIn("compliance_notes", d)


class TestLandingPageGeneration(unittest.TestCase):

    def test_generates_structure(self):
        from core.skills.business_reasoning import (
            BusinessOpportunity, generate_landing_structure,
        )
        opp = BusinessOpportunity(
            summary="Automated Reports",
            problem="Manual reporting is slow",
            solution="AI-powered report generation",
            value_proposition="Save 5 hours per week",
            target_customer="Marketing agencies",
            delivery_format="SaaS dashboard",
            pricing_model="€99/month",
        )
        lp = generate_landing_structure(opp)
        self.assertIn("5 hours", lp.headline)
        self.assertEqual(lp.problem_statement, "Manual reporting is slow")
        self.assertEqual(len(lp.process_steps), 3)
        self.assertEqual(len(lp.trust_elements), 3)

    def test_to_dict(self):
        from core.skills.business_reasoning import (
            BusinessOpportunity, generate_landing_structure,
        )
        opp = BusinessOpportunity(summary="Test", problem="X", solution="Y")
        lp = generate_landing_structure(opp)
        d = lp.to_dict()
        self.assertIn("headline", d)
        self.assertIn("call_to_action", d)


class TestAcquisitionStrategy(unittest.TestCase):

    def test_automation_strategies(self):
        from core.skills.business_reasoning import suggest_acquisition, OpportunityType
        strats = suggest_acquisition(OpportunityType.AUTOMATION_SERVICE)
        self.assertGreater(len(strats), 2)
        self.assertTrue(any("outreach" in s.lower() for s in strats))

    def test_content_strategies(self):
        from core.skills.business_reasoning import suggest_acquisition, OpportunityType
        strats = suggest_acquisition(OpportunityType.CONTENT_SERVICE)
        self.assertGreater(len(strats), 2)

    def test_all_types_have_strategies(self):
        from core.skills.business_reasoning import suggest_acquisition, OpportunityType
        for otype in OpportunityType:
            strats = suggest_acquisition(otype)
            self.assertGreater(len(strats), 0)


if __name__ == "__main__":
    unittest.main()
