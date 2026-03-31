"""
Tests for Chantier A (External Action Layer) + Chantier B (Self-Improvement V2)

Validates:
- Browser bridge registration in ToolExecutor + ToolRegistry
- Browser bridge function contracts
- Login detection
- Internal address blocking
- Self-improvement engine: analyze → propose → evaluate → promote cycle
- Sandbox evaluation scoring
- Safe promoter file writes
- Long-horizon mission stability (50 missions)
- API endpoint existence
"""
import os
import sys
import time
import json
import types
import shutil
import unittest

# ── Structlog stub ────────────────────────────────────────────────────────────
if 'structlog' not in sys.modules:
    _sl = types.ModuleType('structlog')
    class _ML:
        def info(self, *a, **k): pass
        def debug(self, *a, **k): pass
        def warning(self, *a, **k): pass
        def error(self, *a, **k): pass
        def bind(self, **k): return self
    _sl.get_logger = lambda *a, **k: _ML()
    sys.modules['structlog'] = _sl

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


# ═══════════════════════════════════════════════════════════════
# CHANTIER A — BROWSER BRIDGE REGISTRATION
# ═══════════════════════════════════════════════════════════════

class TestBrowserBridgeRegistration(unittest.TestCase):
    """Browser tools are registered in ToolExecutor."""

    def test_browser_tools_in_executor(self):
        from core.tool_executor import ToolExecutor
        expected = [
            "browser_navigate", "browser_get_text", "browser_click",
            "browser_fill", "browser_screenshot", "browser_extract_links",
            "browser_search", "browser_close",
        ]
        for name in expected:
            self.assertIn(name, ToolExecutor._tools,
                          f"Browser tool '{name}' not registered in ToolExecutor")

    def test_browser_tools_callable(self):
        from core.tool_executor import ToolExecutor
        browser_tools = [k for k in ToolExecutor._tools if k.startswith("browser_")]
        for name in browser_tools:
            self.assertTrue(callable(ToolExecutor._tools[name]),
                            f"Browser tool '{name}' is not callable")

    def test_browser_tools_in_registry(self):
        from core.tool_registry import get_tool_registry
        registry = get_tool_registry()
        browser_defs = [t for t in registry.list_tools() if t.name.startswith("browser_")]
        self.assertGreaterEqual(len(browser_defs), 7,
                                f"Expected >=7 browser tools in registry, got {len(browser_defs)}")

    def test_browser_tools_have_risk_levels(self):
        from core.tool_executor import ToolExecutor
        for name in ["browser_navigate", "browser_click", "browser_fill"]:
            self.assertIn(name, ToolExecutor._TOOL_RISK_LEVELS,
                          f"{name} missing risk level")

    def test_browser_tools_have_action_types(self):
        from core.tool_executor import ToolExecutor
        for name in ["browser_navigate", "browser_click", "browser_fill"]:
            self.assertIn(name, ToolExecutor._action_types,
                          f"{name} missing action type")

    def test_browser_tools_in_mission_routing(self):
        from core.tool_registry import _MISSION_TOOLS
        # Browser tools should be routed for research, business, info queries
        for mtype in ["research_task", "business_task", "info_query"]:
            tools = _MISSION_TOOLS.get(mtype, [])
            browser_in = any(t.startswith("browser_") for t in tools)
            self.assertTrue(browser_in,
                            f"No browser tools routed for {mtype}")


class TestBrowserBridgeFunctions(unittest.TestCase):
    """Browser bridge functions have correct signatures and contracts."""

    def test_navigate_blocks_internal(self):
        from core.tools.browser_bridge import browser_navigate
        for addr in ["localhost", "127.0.0.1", "10.0.0.1", "192.168.1.1"]:
            result = browser_navigate(url=f"http://{addr}/admin")
            self.assertFalse(result["ok"], f"Should block {addr}")
            self.assertIn("blocked", result["error"])

    def test_navigate_requires_url(self):
        from core.tools.browser_bridge import browser_navigate
        result = browser_navigate()
        self.assertFalse(result["ok"])
        self.assertIn("url required", result["error"])

    def test_click_requires_selector(self):
        from core.tools.browser_bridge import browser_click
        result = browser_click()
        self.assertFalse(result["ok"])
        self.assertIn("selector required", result["error"])

    def test_fill_requires_selector(self):
        from core.tools.browser_bridge import browser_fill
        result = browser_fill()
        self.assertFalse(result["ok"])
        self.assertIn("selector required", result["error"])

    def test_search_requires_query(self):
        from core.tools.browser_bridge import browser_search
        result = browser_search()
        self.assertFalse(result["ok"])
        self.assertIn("query required", result["error"])

    def test_close_always_ok(self):
        from core.tools.browser_bridge import browser_close
        result = browser_close()
        self.assertTrue(result["ok"])

    def test_all_return_dict(self):
        from core.tools.browser_bridge import BROWSER_TOOLS
        for name, func in BROWSER_TOOLS.items():
            result = func()  # Call with no args
            self.assertIsInstance(result, dict, f"{name} should return dict")
            self.assertIn("ok", result, f"{name} missing 'ok' key")
            self.assertIn("error", result, f"{name} missing 'error' key")


class TestLoginDetection(unittest.TestCase):
    """Login page detection works for common patterns."""

    def test_login_url_detected(self):
        from core.tools.browser_bridge import _detect_login
        self.assertTrue(_detect_login("https://example.com/login"))
        self.assertTrue(_detect_login("https://app.example.com/sign-in"))
        self.assertTrue(_detect_login("https://auth.example.com/oauth"))

    def test_login_text_detected(self):
        from core.tools.browser_bridge import _detect_login
        self.assertTrue(_detect_login("https://example.com", "Please enter your password"))
        self.assertTrue(_detect_login("https://example.com", "Sign in to your account"))

    def test_normal_url_not_flagged(self):
        from core.tools.browser_bridge import _detect_login
        self.assertFalse(_detect_login("https://example.com/about"))
        self.assertFalse(_detect_login("https://news.example.com/article/123"))

    def test_empty_input(self):
        from core.tools.browser_bridge import _detect_login
        self.assertFalse(_detect_login(""))
        self.assertFalse(_detect_login("", ""))


# ═══════════════════════════════════════════════════════════════
# CHANTIER B — SELF-IMPROVEMENT ENGINE V2
# ═══════════════════════════════════════════════════════════════

class TestPerformanceAnalyzer(unittest.TestCase):
    """PerformanceAnalyzer detects weak spots from mission history."""

    def test_analyze_returns_list(self):
        from core.self_improvement_engine import PerformanceAnalyzer
        analyzer = PerformanceAnalyzer()
        spots = analyzer.analyze()
        self.assertIsInstance(spots, list)

    def test_weak_spots_have_required_fields(self):
        from core.self_improvement_engine import PerformanceAnalyzer, WeakSpot
        analyzer = PerformanceAnalyzer()
        spots = analyzer.analyze()
        for spot in spots:
            self.assertIsInstance(spot, WeakSpot)
            self.assertTrue(spot.category)
            self.assertTrue(spot.mission_type)
            self.assertTrue(spot.metric_name)
            self.assertIn(spot.severity, ("low", "medium", "high"))

    def test_max_10_spots(self):
        from core.self_improvement_engine import PerformanceAnalyzer
        analyzer = PerformanceAnalyzer()
        spots = analyzer.analyze()
        self.assertLessEqual(len(spots), 10)

    def test_spots_sorted_by_severity(self):
        from core.self_improvement_engine import PerformanceAnalyzer
        analyzer = PerformanceAnalyzer()
        spots = analyzer.analyze()
        if len(spots) >= 2:
            sev_order = {"high": 3, "medium": 2, "low": 1}
            for i in range(len(spots) - 1):
                self.assertGreaterEqual(
                    sev_order.get(spots[i].severity, 0),
                    sev_order.get(spots[i + 1].severity, 0),
                    "Spots not sorted by severity"
                )


class TestStrategyMutator(unittest.TestCase):
    """StrategyMutator generates proposals from weak spots."""

    def test_propose_from_tool_failure(self):
        from core.self_improvement_engine import StrategyMutator, WeakSpot
        mutator = StrategyMutator()
        spot = WeakSpot(
            category="tool_failure",
            mission_type="coding_task",
            metric_name="tool_success_rate",
            current_value=0.4,
            threshold=0.7,
            occurrences=10,
            severity="high",
            details="Tool 'broken_tool': 40% success",
        )
        proposals = mutator.propose([spot])
        self.assertEqual(len(proposals), 1)
        self.assertEqual(proposals[0].change_type, "tool_preference")
        self.assertIn("tool_prefs.json", proposals[0].target_file)

    def test_propose_from_repeated_error(self):
        from core.self_improvement_engine import StrategyMutator, WeakSpot
        mutator = StrategyMutator()
        spot = WeakSpot(
            category="repeated_error",
            mission_type="debug_task",
            metric_name="error_count",
            current_value=5,
            threshold=3,
            occurrences=5,
            severity="medium",
            details="Error 'timeout_error' repeated 5x in debug_task",
        )
        proposals = mutator.propose([spot])
        self.assertEqual(len(proposals), 1)
        self.assertEqual(proposals[0].change_type, "skip_pattern")

    def test_propose_from_low_success(self):
        from core.self_improvement_engine import StrategyMutator, WeakSpot
        mutator = StrategyMutator()
        spot = WeakSpot(
            category="low_success_rate",
            mission_type="system_task",
            metric_name="success_rate",
            current_value=0.5,
            threshold=0.7,
            occurrences=20,
            severity="high",
        )
        proposals = mutator.propose([spot])
        self.assertEqual(len(proposals), 1)
        self.assertEqual(proposals[0].change_type, "retry_strategy")

    def test_propose_from_high_fallback(self):
        from core.self_improvement_engine import StrategyMutator, WeakSpot
        mutator = StrategyMutator()
        spot = WeakSpot(
            category="high_fallback",
            mission_type="business_task",
            metric_name="avg_fallback_level",
            current_value=0.8,
            threshold=0.5,
            occurrences=10,
            severity="medium",
        )
        proposals = mutator.propose([spot])
        self.assertEqual(len(proposals), 1)
        self.assertEqual(proposals[0].change_type, "prompt_tweak")

    def test_max_5_proposals(self):
        from core.self_improvement_engine import StrategyMutator, WeakSpot
        mutator = StrategyMutator()
        spots = [
            WeakSpot(category="tool_failure", mission_type=f"type_{i}",
                     metric_name="x", current_value=0.3, threshold=0.7,
                     occurrences=5, severity="high", details=f"Tool 'tool_{i}': 30%")
            for i in range(10)
        ]
        proposals = mutator.propose(spots)
        self.assertLessEqual(len(proposals), 5)


class TestEvaluationRunner(unittest.TestCase):
    """EvaluationRunner scores proposals correctly."""

    def test_evaluate_returns_sandbox_result(self):
        from core.self_improvement_engine import (
            EvaluationRunner, Proposal, WeakSpot, SandboxResult,
        )
        runner = EvaluationRunner()
        spot = WeakSpot("tool_failure", "coding_task", "x", 0.5, 0.7, 10, "medium")
        proposal = Proposal(
            proposal_id="test_prop",
            weak_spot=spot,
            change_type="tool_preference",
            description="Test",
            target_file="workspace/test.json",
            content="{}",
            expected_impact="test",
        )
        result = runner.evaluate(proposal)
        self.assertIsInstance(result, SandboxResult)
        self.assertEqual(result.proposal_id, "test_prop")
        self.assertIsInstance(result.baseline_score, float)
        self.assertIsInstance(result.proposal_score, float)

    def test_improvement_positive_for_weak_spot(self):
        from core.self_improvement_engine import (
            EvaluationRunner, Proposal, WeakSpot,
        )
        runner = EvaluationRunner()
        spot = WeakSpot("low_success_rate", "coding_task", "success_rate",
                        0.4, 0.7, 20, "high")
        proposal = Proposal("p1", spot, "retry_strategy", "test",
                            "workspace/test.json", "{}", "test")
        result = runner.evaluate(proposal)
        self.assertGreater(result.proposal_score, result.baseline_score)
        self.assertTrue(result.passed)


class TestSafePromoter(unittest.TestCase):
    """SafePromoter writes files atomically and only when sandbox passes."""

    def setUp(self):
        self._test_dir = "/tmp/jarvis_promoter_test"
        os.makedirs(self._test_dir, exist_ok=True)

    def test_promote_writes_json(self):
        from core.self_improvement_engine import (
            SafePromoter, Proposal, WeakSpot, SandboxResult,
        )
        promoter = SafePromoter()
        spot = WeakSpot("test", "test", "x", 0.5, 0.7, 5, "medium")
        proposal = Proposal(
            "p1", spot, "tool_preference", "test",
            f"{self._test_dir}/prefs.json",
            '{"test_key": "test_value"}',
            "test",
        )
        sr = SandboxResult("p1", 0.5, 0.6, 20.0, True)
        ok = promoter.promote(proposal, sr)
        self.assertTrue(ok)
        self.assertTrue(os.path.exists(f"{self._test_dir}/prefs.json"))
        with open(f"{self._test_dir}/prefs.json") as f:
            data = json.load(f)
        self.assertEqual(data["test_key"], "test_value")

    def test_promote_rejects_failed_sandbox(self):
        from core.self_improvement_engine import (
            SafePromoter, Proposal, WeakSpot, SandboxResult,
        )
        promoter = SafePromoter()
        spot = WeakSpot("test", "test", "x", 0.5, 0.7, 5, "medium")
        proposal = Proposal(
            "p2", spot, "tool_preference", "test",
            f"{self._test_dir}/rejected.json",
            '{"rejected": true}',
            "test",
        )
        sr = SandboxResult("p2", 0.5, 0.4, -20.0, False)
        ok = promoter.promote(proposal, sr)
        self.assertFalse(ok)
        self.assertFalse(os.path.exists(f"{self._test_dir}/rejected.json"))

    def test_promote_merges_existing(self):
        from core.self_improvement_engine import (
            SafePromoter, Proposal, WeakSpot, SandboxResult,
        )
        # Pre-existing file
        target = f"{self._test_dir}/merge.json"
        with open(target, "w") as f:
            json.dump({"existing_key": "existing_value"}, f)

        promoter = SafePromoter()
        spot = WeakSpot("test", "test", "x", 0.5, 0.7, 5, "medium")
        proposal = Proposal(
            "p3", spot, "tool_preference", "test",
            target,
            '{"new_key": "new_value"}',
            "test",
        )
        sr = SandboxResult("p3", 0.5, 0.6, 20.0, True)
        promoter.promote(proposal, sr)

        with open(target) as f:
            data = json.load(f)
        self.assertEqual(data["existing_key"], "existing_value")
        self.assertEqual(data["new_key"], "new_value")

    def tearDown(self):
        shutil.rmtree(self._test_dir, ignore_errors=True)


class TestFullImprovementCycle(unittest.TestCase):
    """Full run_improvement_cycle() works end-to-end."""

    def test_cycle_returns_report(self):
        from core.self_improvement_engine import run_improvement_cycle, CycleReport
        report = run_improvement_cycle()
        self.assertIsInstance(report, CycleReport)
        self.assertTrue(report.cycle_id)
        self.assertGreaterEqual(report.timestamp, 0)
        self.assertGreaterEqual(report.duration_s, 0)

    def test_cycle_report_has_all_fields(self):
        from core.self_improvement_engine import run_improvement_cycle
        report = run_improvement_cycle()
        d = report.to_dict()
        for key in ["cycle_id", "timestamp", "duration_s", "weak_spots_found",
                     "proposals_generated", "proposals_tested", "proposals_promoted",
                     "weak_spots", "proposals", "sandbox_results", "promoted"]:
            self.assertIn(key, d, f"Missing key: {key}")

    def test_cycle_persists_report(self):
        from core.self_improvement_engine import run_improvement_cycle, _REPORTS_DIR
        report = run_improvement_cycle()
        report_path = _REPORTS_DIR / f"{report.cycle_id}.json"
        self.assertTrue(report_path.exists(), "Report not persisted to disk")

    def test_get_report_returns_last(self):
        from core.self_improvement_engine import (
            run_improvement_cycle, get_improvement_report,
        )
        run_improvement_cycle()
        report = get_improvement_report()
        self.assertIsNotNone(report)
        self.assertIn("cycle_id", report)

    def test_cycle_is_fast(self):
        from core.self_improvement_engine import run_improvement_cycle
        t0 = time.time()
        run_improvement_cycle()
        elapsed = time.time() - t0
        self.assertLess(elapsed, 5.0, f"Cycle took {elapsed:.2f}s (max 5s)")


# ═══════════════════════════════════════════════════════════════
# LONG-HORIZON STABILITY
# ═══════════════════════════════════════════════════════════════

class TestLongHorizonStability(unittest.TestCase):
    """50 sequential missions don't crash or diverge."""

    def test_50_missions_stable(self):
        from core.mission_system import get_mission_system, MissionStatus
        ms = get_mission_system()
        results = []
        for i in range(50):
            r = ms.submit(f"Long horizon test mission {i}: analyze trend {i}")
            results.append(r)

        # All should have valid IDs
        ids = [r.mission_id for r in results]
        self.assertEqual(len(set(ids)), 50, "Non-unique mission IDs")

        # All should be retrievable
        for r in results:
            m = ms.get(r.mission_id)
            self.assertIsNotNone(m, f"Mission {r.mission_id} lost")

        # Complete all
        completed = 0
        for r in results:
            r.status = MissionStatus.APPROVED
            ms.complete(r.mission_id, f"Result for mission {r.mission_id}")
            m = ms.get(r.mission_id)
            status_val = m.status.value if hasattr(m.status, 'value') else str(m.status)
            if status_val in ("DONE", "PLAN_ONLY"):
                completed += 1
        self.assertEqual(completed, 50, f"Only {completed}/50 completed")

    def test_improvement_after_50_missions(self):
        """Self-improvement engine runs cleanly after 50 missions."""
        from core.self_improvement_engine import run_improvement_cycle
        report = run_improvement_cycle()
        # Should not crash, should have some analysis
        self.assertIsNotNone(report)
        self.assertGreaterEqual(report.weak_spots_found, 0)


# ═══════════════════════════════════════════════════════════════
# BUSINESS WORKFLOW E2E
# ═══════════════════════════════════════════════════════════════

class TestBusinessWorkflowE2E(unittest.TestCase):
    """Simulates: research → offer → content → outreach → track."""

    def test_full_business_pipeline(self):
        from core.mission_system import get_mission_system, MissionStatus
        ms = get_mission_system()

        # Step 1: Market research
        r1 = ms.submit("Research SaaS competitors in project management space")
        r1.status = MissionStatus.APPROVED
        ms.complete(r1.mission_id, "Found 5 competitors: Asana, Monday, Notion, ClickUp, Linear")
        m1 = ms.get(r1.mission_id)
        self.assertIn("DONE", str(m1.status) + m1.status.value if hasattr(m1.status, 'value') else str(m1.status))

        # Step 2: Create offer
        r2 = ms.submit("Create competitive pricing offer based on market analysis")
        r2.status = MissionStatus.APPROVED
        ms.complete(r2.mission_id, "Pricing: Starter $9, Pro $29, Enterprise $99")

        # Step 3: Generate landing page copy
        r3 = ms.submit("Generate landing page copy for project management tool")
        r3.status = MissionStatus.APPROVED
        ms.complete(r3.mission_id, "Hero: Ship faster. Tagline: The PM tool that thinks ahead.")

        # Step 4: Create outreach emails
        r4 = ms.submit("Draft 3 cold outreach emails for SaaS founders")
        r4.status = MissionStatus.APPROVED
        ms.complete(r4.mission_id, "Email 1: Subject: Your team deserves better PM...")

        # Step 5: Track responses via lead pipeline
        from core.business_pipeline import LeadTracker
        tracker = LeadTracker(persist_path="/tmp/test_biz_leads.json")
        leads = []
        for name in ["Acme Corp", "TechStart", "DevFlow"]:
            lead = tracker.add_lead(name=name, source="cold_email", value_estimate=5000)
            leads.append(lead)

        # Advance one lead through pipeline
        tracker.advance_lead(leads[0].lead_id, "qualified", "Responded positively")
        tracker.advance_lead(leads[0].lead_id, "proposal_sent", "Sent pricing deck")

        # Verify pipeline state
        summary = tracker.get_pipeline_summary()
        self.assertGreaterEqual(summary["total_leads"], 3)

        # All missions completed
        for r in [r1, r2, r3, r4]:
            m = ms.get(r.mission_id)
            self.assertIsNotNone(m.final_output)


# ═══════════════════════════════════════════════════════════════
# CONNECTOR COVERAGE
# ═══════════════════════════════════════════════════════════════

class TestConnectorCoverage(unittest.TestCase):
    """All required connectors exist in the registry."""

    def test_required_connectors_exist(self):
        from core.connectors import CONNECTOR_REGISTRY
        required = [
            "http_request", "web_search", "json_storage",
            "email", "lead_manager", "content_manager",
            "scheduler", "workflow_trigger", "web_scrape",
            "file_export", "budget_tracker",
        ]
        for name in required:
            self.assertIn(name, CONNECTOR_REGISTRY,
                          f"Required connector '{name}' not in registry")

    def test_all_connectors_have_execute(self):
        from core.connectors import CONNECTOR_REGISTRY
        for name, entry in CONNECTOR_REGISTRY.items():
            self.assertTrue(callable(entry["execute"]),
                            f"Connector '{name}' has no callable execute")


# ═══════════════════════════════════════════════════════════════
# TOOL REGISTRY COMPLETENESS
# ═══════════════════════════════════════════════════════════════

class TestToolRegistryCompleteness(unittest.TestCase):
    """ToolRegistry validates all tools including new browser tools."""

    def test_validate_all_includes_browser(self):
        from core.tool_registry import get_tool_registry
        registry = get_tool_registry()
        validation = registry.validate_all()
        browser_valid = [t for t in validation["valid"] if t.startswith("browser_")]
        self.assertGreaterEqual(len(browser_valid), 5,
                                f"Only {len(browser_valid)} browser tools valid")

    def test_total_tools_minimum(self):
        from core.tool_registry import get_tool_registry
        registry = get_tool_registry()
        total = len(registry.list_tools())
        self.assertGreaterEqual(total, 14,
                                f"Only {total} tools registered (expected >=14)")


if __name__ == "__main__":
    unittest.main()
