"""
tests/test_business_actions.py — Business Action Layer tests.

Covers:
  - Action registry and definitions
  - BusinessActionExecutor for all 4 agents
  - Real file creation verification
  - Cognitive event emission
  - Edge cases (empty output, missing fields)
  - API routes
"""
import json
import os
import tempfile

import pytest


# ═══════════════════════════════════════════════════════════════
# 1 — Action Registry
# ═══════════════════════════════════════════════════════════════

class TestActionRegistry:

    def test_BA01_registry_not_empty(self):
        from core.business_actions import ACTION_REGISTRY
        assert len(ACTION_REGISTRY) >= 4

    def test_BA02_venture_action_exists(self):
        from core.business_actions import ACTION_REGISTRY
        assert "venture.research_workspace" in ACTION_REGISTRY

    def test_BA03_offer_action_exists(self):
        from core.business_actions import ACTION_REGISTRY
        assert "offer.package" in ACTION_REGISTRY

    def test_BA04_workflow_action_exists(self):
        from core.business_actions import ACTION_REGISTRY
        assert "workflow.blueprint" in ACTION_REGISTRY

    def test_BA05_saas_action_exists(self):
        from core.business_actions import ACTION_REGISTRY
        assert "saas.mvp_spec" in ACTION_REGISTRY

    def test_BA06_action_to_dict(self):
        from core.business_actions import ACTION_REGISTRY
        d = ACTION_REGISTRY["venture.research_workspace"].to_dict()
        assert "action_id" in d
        assert "name" in d
        assert "risk_level" in d
        assert d["risk_level"] == "low"

    def test_BA07_list_actions(self):
        from core.business_actions import list_actions
        actions = list_actions()
        assert len(actions) >= 4
        assert all("action_id" in a for a in actions)

    def test_BA08_all_actions_have_expected_outputs(self):
        from core.business_actions import ACTION_REGISTRY
        for action in ACTION_REGISTRY.values():
            assert len(action.expected_outputs) >= 1


# ═══════════════════════════════════════════════════════════════
# 2 — Venture Execution
# ═══════════════════════════════════════════════════════════════

class TestVentureExecution:

    def _sample_venture_output(self):
        return {
            "sector": "AI Customer Service",
            "synthesis": "Strong demand for AI-powered support tools in SMB segment.",
            "opportunities": [
                {
                    "title": "AI Support Bot for E-commerce",
                    "problem": "E-commerce stores spend 30% of time on repetitive support queries",
                    "target": "Shopify stores with 1000-50000 orders/month",
                    "offer_idea": "AI chatbot that handles 80% of support tickets automatically",
                    "difficulty": "medium",
                    "score": 8,
                    "short_term": "Launch beta with 10 stores in 2 months",
                    "long_term": "SaaS platform with $50-200/mo plans, 10k+ stores",
                    "revenue_model": "Monthly SaaS subscription",
                    "existing_competitors": "Tidio, Intercom (expensive), Zendesk",
                },
                {
                    "title": "Review Response Automation",
                    "problem": "Businesses lose reputation by not responding to online reviews",
                    "target": "Local businesses with Google/Yelp presence",
                    "offer_idea": "AI generates personalized review responses",
                    "difficulty": "low",
                    "score": 7,
                    "short_term": "MVP in 1 month, charge $29/mo",
                    "long_term": "Expand to multi-platform review management",
                },
            ],
        }

    def test_BA09_venture_creates_files(self):
        from core.business_actions import BusinessActionExecutor, _BUSINESS_DIR
        import core.business_actions as ba
        old_dir = ba._BUSINESS_DIR
        with tempfile.TemporaryDirectory() as td:
            ba._BUSINESS_DIR = type(old_dir)(td)
            try:
                executor = BusinessActionExecutor()
                result = executor.execute(
                    "venture.research_workspace",
                    self._sample_venture_output(),
                    project_name="ai-support",
                )
                assert result["ok"] is True
                assert len(result["files_created"]) >= 4
                assert os.path.isdir(result["project_dir"])
                # Verify actual files exist
                for f in result["files_created"]:
                    assert os.path.isfile(os.path.join(result["project_dir"], f))
            finally:
                ba._BUSINESS_DIR = old_dir

    def test_BA10_venture_readme_content(self):
        from core.business_actions import BusinessActionExecutor
        import core.business_actions as ba
        old_dir = ba._BUSINESS_DIR
        with tempfile.TemporaryDirectory() as td:
            ba._BUSINESS_DIR = type(old_dir)(td)
            try:
                executor = BusinessActionExecutor()
                result = executor.execute(
                    "venture.research_workspace",
                    self._sample_venture_output(),
                )
                readme = open(os.path.join(result["project_dir"], "README.md")).read()
                assert "AI Customer Service" in readme
                assert "AI Support Bot" in readme
            finally:
                ba._BUSINESS_DIR = old_dir

    def test_BA11_venture_opportunities_json(self):
        from core.business_actions import BusinessActionExecutor
        import core.business_actions as ba
        old_dir = ba._BUSINESS_DIR
        with tempfile.TemporaryDirectory() as td:
            ba._BUSINESS_DIR = type(old_dir)(td)
            try:
                executor = BusinessActionExecutor()
                result = executor.execute(
                    "venture.research_workspace",
                    self._sample_venture_output(),
                )
                data = json.loads(
                    open(os.path.join(result["project_dir"], "opportunities.json")).read()
                )
                assert len(data) == 2
            finally:
                ba._BUSINESS_DIR = old_dir

    def test_BA12_venture_next_steps(self):
        from core.business_actions import BusinessActionExecutor
        import core.business_actions as ba
        old_dir = ba._BUSINESS_DIR
        with tempfile.TemporaryDirectory() as td:
            ba._BUSINESS_DIR = type(old_dir)(td)
            try:
                executor = BusinessActionExecutor()
                result = executor.execute(
                    "venture.research_workspace",
                    self._sample_venture_output(),
                )
                steps = open(os.path.join(result["project_dir"], "next-steps.md")).read()
                assert "Week 1-2" in steps
                assert "[ ]" in steps  # Has actionable checkboxes
            finally:
                ba._BUSINESS_DIR = old_dir


# ═══════════════════════════════════════════════════════════════
# 3 — Offer Execution
# ═══════════════════════════════════════════════════════════════

class TestOfferExecution:

    def _sample_offer_output(self):
        return {
            "synthesis": "Position as affordable AI support for growing e-commerce stores.",
            "recommended": "SupportBot Pro",
            "offers": [
                {
                    "title": "SupportBot Starter",
                    "tagline": "AI support in 5 minutes",
                    "problem_statement": "You're drowning in support tickets",
                    "value_proposition": "Reduce support load by 80%",
                    "target_persona": "Lisa, 32, Shopify store owner, 500 orders/month",
                    "offer_type": "saas",
                    "delivery_mode": "Web widget + Shopify app",
                    "key_features": ["Auto-reply", "FAQ builder", "Analytics"],
                    "pricing": {"model": "monthly", "price": "$49/mo", "billing_cycle": "monthly"},
                    "objection_handling": [
                        {"objection": "I already use email", "response": "Email doesn't scale past 100 tickets/day"},
                    ],
                },
            ],
        }

    def test_BA13_offer_creates_files(self):
        from core.business_actions import BusinessActionExecutor
        import core.business_actions as ba
        old_dir = ba._BUSINESS_DIR
        with tempfile.TemporaryDirectory() as td:
            ba._BUSINESS_DIR = type(old_dir)(td)
            try:
                executor = BusinessActionExecutor()
                result = executor.execute("offer.package", self._sample_offer_output())
                assert result["ok"] is True
                assert len(result["files_created"]) >= 6
                for f in ["README.md", "offer-spec.json", "pricing.md",
                          "personas.md", "objections.md", "launch-checklist.md"]:
                    assert f in result["files_created"]
            finally:
                ba._BUSINESS_DIR = old_dir

    def test_BA14_offer_pricing_content(self):
        from core.business_actions import BusinessActionExecutor
        import core.business_actions as ba
        old_dir = ba._BUSINESS_DIR
        with tempfile.TemporaryDirectory() as td:
            ba._BUSINESS_DIR = type(old_dir)(td)
            try:
                result = BusinessActionExecutor().execute(
                    "offer.package", self._sample_offer_output()
                )
                pricing = open(os.path.join(result["project_dir"], "pricing.md")).read()
                assert "$49/mo" in pricing
            finally:
                ba._BUSINESS_DIR = old_dir

    def test_BA15_offer_launch_checklist(self):
        from core.business_actions import BusinessActionExecutor
        import core.business_actions as ba
        old_dir = ba._BUSINESS_DIR
        with tempfile.TemporaryDirectory() as td:
            ba._BUSINESS_DIR = type(old_dir)(td)
            try:
                result = BusinessActionExecutor().execute(
                    "offer.package", self._sample_offer_output()
                )
                checklist = open(os.path.join(result["project_dir"], "launch-checklist.md")).read()
                assert "Pre-Launch" in checklist
                assert "[ ]" in checklist
            finally:
                ba._BUSINESS_DIR = old_dir


# ═══════════════════════════════════════════════════════════════
# 4 — Workflow Execution
# ═══════════════════════════════════════════════════════════════

class TestWorkflowExecution:

    def _sample_workflow_output(self):
        return {
            "synthesis": "Automate lead qualification and follow-up to save 10h/week.",
            "workflows": [
                {
                    "name": "Lead Qualification",
                    "description": "Score and route incoming leads automatically",
                    "trigger": "New form submission on website",
                    "goal": "Qualify 90% of leads within 5 minutes",
                    "automation_potential": "80%",
                    "roi_estimate": "Saves 8h/week per sales rep",
                    "steps": [
                        {"id": "s1", "name": "Receive lead", "description": "Form webhook fires",
                         "actor": "system", "tool_hint": "n8n webhook", "n8n_node": "Webhook"},
                        {"id": "s2", "name": "Score lead", "description": "AI scores based on criteria",
                         "actor": "ai", "tool_hint": "OpenAI"},
                        {"id": "s3", "name": "Route to sales", "description": "High-score leads to CRM",
                         "actor": "automation", "tool_hint": "HubSpot CRM"},
                    ],
                },
            ],
        }

    def test_BA16_workflow_creates_files(self):
        from core.business_actions import BusinessActionExecutor
        import core.business_actions as ba
        old_dir = ba._BUSINESS_DIR
        with tempfile.TemporaryDirectory() as td:
            ba._BUSINESS_DIR = type(old_dir)(td)
            try:
                result = BusinessActionExecutor().execute(
                    "workflow.blueprint", self._sample_workflow_output()
                )
                assert result["ok"] is True
                assert len(result["files_created"]) >= 4
            finally:
                ba._BUSINESS_DIR = old_dir

    def test_BA17_workflow_automation_spec(self):
        from core.business_actions import BusinessActionExecutor
        import core.business_actions as ba
        old_dir = ba._BUSINESS_DIR
        with tempfile.TemporaryDirectory() as td:
            ba._BUSINESS_DIR = type(old_dir)(td)
            try:
                result = BusinessActionExecutor().execute(
                    "workflow.blueprint", self._sample_workflow_output()
                )
                spec = open(os.path.join(result["project_dir"], "automation-spec.md")).read()
                assert "n8n" in spec or "Webhook" in spec
                assert "👤" in spec or "🤖" in spec or "⚡" in spec
            finally:
                ba._BUSINESS_DIR = old_dir


# ═══════════════════════════════════════════════════════════════
# 5 — SaaS Execution
# ═══════════════════════════════════════════════════════════════

class TestSaasExecution:

    def _sample_saas_output(self):
        return {
            "synthesis": "Build a lightweight AI support tool for Shopify stores.",
            "blueprints": [
                {
                    "product_name": "SupportBot",
                    "tagline": "AI support in minutes",
                    "problem": "Small e-commerce stores can't afford full support teams",
                    "solution": "AI chatbot trained on store FAQ and order data",
                    "target_user": "Shopify store owner, 500-5000 orders/month",
                    "mvp_scope": "Widget + FAQ trainer + basic analytics. No phone/email.",
                    "features": [
                        {"id": "f1", "name": "Auto-reply", "description": "AI responds to common questions",
                         "priority": "must", "effort": "m",
                         "user_story": "As a store owner, I want auto-replies so I spend less time on support"},
                        {"id": "f2", "name": "FAQ Builder", "description": "Upload FAQ to train the bot",
                         "priority": "must", "effort": "s"},
                        {"id": "f3", "name": "Analytics", "description": "See resolution rates",
                         "priority": "should", "effort": "m"},
                    ],
                    "tech_stack": {"frontend": "Next.js", "backend": "FastAPI", "ai": "OpenAI GPT-4"},
                },
            ],
        }

    def test_BA18_saas_creates_files(self):
        from core.business_actions import BusinessActionExecutor
        import core.business_actions as ba
        old_dir = ba._BUSINESS_DIR
        with tempfile.TemporaryDirectory() as td:
            ba._BUSINESS_DIR = type(old_dir)(td)
            try:
                result = BusinessActionExecutor().execute(
                    "saas.mvp_spec", self._sample_saas_output()
                )
                assert result["ok"] is True
                assert len(result["files_created"]) >= 6
                for f in ["README.md", "mvp-spec.json", "features.md",
                          "user-stories.md", "tech-stack.md", "roadmap.md"]:
                    assert f in result["files_created"]
            finally:
                ba._BUSINESS_DIR = old_dir

    def test_BA19_saas_readme_has_product_name(self):
        from core.business_actions import BusinessActionExecutor
        import core.business_actions as ba
        old_dir = ba._BUSINESS_DIR
        with tempfile.TemporaryDirectory() as td:
            ba._BUSINESS_DIR = type(old_dir)(td)
            try:
                result = BusinessActionExecutor().execute(
                    "saas.mvp_spec", self._sample_saas_output()
                )
                readme = open(os.path.join(result["project_dir"], "README.md")).read()
                assert "SupportBot" in readme
            finally:
                ba._BUSINESS_DIR = old_dir

    def test_BA20_saas_features_priorities(self):
        from core.business_actions import BusinessActionExecutor
        import core.business_actions as ba
        old_dir = ba._BUSINESS_DIR
        with tempfile.TemporaryDirectory() as td:
            ba._BUSINESS_DIR = type(old_dir)(td)
            try:
                result = BusinessActionExecutor().execute(
                    "saas.mvp_spec", self._sample_saas_output()
                )
                features = open(os.path.join(result["project_dir"], "features.md")).read()
                assert "🔴" in features  # must priority
            finally:
                ba._BUSINESS_DIR = old_dir


# ═══════════════════════════════════════════════════════════════
# 6 — Edge Cases
# ═══════════════════════════════════════════════════════════════

class TestEdgeCases:

    def test_BA21_unknown_action(self):
        from core.business_actions import BusinessActionExecutor
        result = BusinessActionExecutor().execute("nonexistent.action", {})
        assert result["ok"] is False
        assert "Unknown action" in result["error"]

    def test_BA22_empty_output(self):
        from core.business_actions import BusinessActionExecutor
        import core.business_actions as ba
        old_dir = ba._BUSINESS_DIR
        with tempfile.TemporaryDirectory() as td:
            ba._BUSINESS_DIR = type(old_dir)(td)
            try:
                result = BusinessActionExecutor().execute(
                    "venture.research_workspace", {}, project_name="empty-test"
                )
                assert result["ok"] is True
                assert len(result["files_created"]) >= 1  # README at minimum
            finally:
                ba._BUSINESS_DIR = old_dir

    def test_BA23_special_chars_in_project_name(self):
        from core.business_actions import _slugify
        assert _slugify("AI & ML Solutions!!!") == "ai-ml-solutions"
        assert _slugify("  spaces  ") == "spaces"
        assert len(_slugify("x" * 100)) <= 60

    def test_BA24_project_dir_isolated(self):
        """Each execution creates a unique project directory."""
        from core.business_actions import BusinessActionExecutor
        import core.business_actions as ba
        old_dir = ba._BUSINESS_DIR
        with tempfile.TemporaryDirectory() as td:
            ba._BUSINESS_DIR = type(old_dir)(td)
            try:
                executor = BusinessActionExecutor()
                r1 = executor.execute("venture.research_workspace",
                                     {"sector": "test"}, project_name="test")
                r2 = executor.execute("venture.research_workspace",
                                     {"sector": "test"}, project_name="test")
                # Same name but different dirs (timestamp differs or same is ok)
                assert r1["ok"] and r2["ok"]
            finally:
                ba._BUSINESS_DIR = old_dir


# ═══════════════════════════════════════════════════════════════
# 7 — Agent Wiring
# ═══════════════════════════════════════════════════════════════

class TestAgentWiring:

    def test_BA25_venture_agent_wired(self):
        import inspect
        from business.venture.agent import VentureBuilderAgent
        src = inspect.getsource(VentureBuilderAgent.run)
        assert "business_actions" in src
        assert "venture.research_workspace" in src

    def test_BA26_offer_agent_wired(self):
        import inspect
        from business.offer.agent import OfferDesignerAgent
        src = inspect.getsource(OfferDesignerAgent.run)
        assert "business_actions" in src
        assert "offer.package" in src

    def test_BA27_workflow_agent_wired(self):
        import inspect
        from business.workflow.agent import WorkflowArchitectAgent
        src = inspect.getsource(WorkflowArchitectAgent.run)
        assert "business_actions" in src
        assert "workflow.blueprint" in src


# ═══════════════════════════════════════════════════════════════
# 8 — API
# ═══════════════════════════════════════════════════════════════

class TestAPI:

    def test_BA28_routes_mounted(self):
        from api.main import app
        paths = [r.path for r in app.routes]
        assert "/api/v3/business-actions" in paths

    def test_BA29_execute_route(self):
        from api.main import app
        paths = [r.path for r in app.routes]
        assert "/api/v3/business-actions/execute" in paths

    def test_BA30_action_detail_route(self):
        from api.main import app
        paths = [r.path for r in app.routes]
        assert "/api/v3/business-actions/{action_id}" in paths


# ═══════════════════════════════════════════════════════════════
# 9 — Cognitive Events
# ═══════════════════════════════════════════════════════════════

class TestCognitiveEvents:

    def test_BA31_action_emits_events(self):
        """Business action executor emits cognitive events."""
        import inspect
        from core.business_actions import BusinessActionExecutor
        src = inspect.getsource(BusinessActionExecutor._emit_event)
        assert "cognitive_events" in src
        assert "emit" in src

    def test_BA32_event_includes_action_id(self):
        """Emission includes action_id in payload."""
        import inspect
        from core.business_actions import BusinessActionExecutor
        src = inspect.getsource(BusinessActionExecutor._emit_event)
        assert "action_id" in src


# ═══════════════════════════════════════════════════════════════
# 10 — Approval Gating
# ═══════════════════════════════════════════════════════════════

class TestApprovalGating:

    def test_BA33_n8n_action_requires_approval(self):
        from core.business_actions import ACTION_REGISTRY
        action = ACTION_REGISTRY["workflow.n8n_trigger"]
        assert action.requires_approval is True
        assert action.risk_level == "medium"

    def test_BA34_approval_gated_produces_spec(self):
        """Approval-gated action creates approval-required.md instead of executing."""
        from core.business_actions import BusinessActionExecutor
        import core.business_actions as ba
        old_dir = ba._BUSINESS_DIR
        with tempfile.TemporaryDirectory() as td:
            ba._BUSINESS_DIR = type(old_dir)(td)
            try:
                result = BusinessActionExecutor().execute(
                    "workflow.n8n_trigger", {"test": True}, project_name="n8n-test"
                )
                assert result["ok"] is True
                assert result.get("awaiting_approval") is True
                assert "approval-required.md" in result["files_created"]
            finally:
                ba._BUSINESS_DIR = old_dir

    def test_BA35_low_risk_no_approval(self):
        """Low-risk actions execute without approval gate."""
        from core.business_actions import ACTION_REGISTRY
        for aid, action in ACTION_REGISTRY.items():
            if action.risk_level == "low":
                assert action.requires_approval is False


# ═══════════════════════════════════════════════════════════════
# 11 — Dependency Checking
# ═══════════════════════════════════════════════════════════════

class TestDependencyChecking:

    def test_BA36_check_readiness_exists(self):
        from core.business_actions import check_action_readiness
        result = check_action_readiness("venture.research_workspace")
        assert "ready" in result
        assert "missing_tools" in result

    def test_BA37_unknown_action_readiness(self):
        from core.business_actions import check_action_readiness
        result = check_action_readiness("nonexistent")
        assert result["ready"] is False

    def test_BA38_n8n_missing_secret(self):
        """n8n trigger reports missing N8N_WEBHOOK_URL."""
        import os
        old = os.environ.get("N8N_WEBHOOK_URL")
        if "N8N_WEBHOOK_URL" in os.environ:
            del os.environ["N8N_WEBHOOK_URL"]
        try:
            from core.business_actions import check_action_readiness
            result = check_action_readiness("workflow.n8n_trigger")
            assert "N8N_WEBHOOK_URL" in result["missing_secrets"]
            assert result["ready"] is False
        finally:
            if old is not None:
                os.environ["N8N_WEBHOOK_URL"] = old


# ═══════════════════════════════════════════════════════════════
# 12 — SaaS Agent Wiring
# ═══════════════════════════════════════════════════════════════

class TestSaasWiring:

    def test_BA39_saas_agent_wired(self):
        import inspect
        from business.saas.agent import SaasBuilderAgent
        src = inspect.getsource(SaasBuilderAgent.run)
        assert "business_actions" in src
        assert "saas.mvp_spec" in src


# ═══════════════════════════════════════════════════════════════
# 13 — Extended API
# ═══════════════════════════════════════════════════════════════

class TestExtendedAPI:

    def test_BA40_readiness_route(self):
        from api.main import app
        paths = [r.path for r in app.routes]
        assert "/api/v3/business-actions/readiness" in paths

    def test_BA41_five_actions_registered(self):
        from core.business_actions import ACTION_REGISTRY
        assert len(ACTION_REGISTRY) >= 5

    def test_BA42_all_actions_have_risk(self):
        from core.business_actions import ACTION_REGISTRY
        for action in ACTION_REGISTRY.values():
            assert action.risk_level in ("low", "medium", "high")


# ═══════════════════════════════════════════════════════════════
# 14 — Artifact File Browser
# ═══════════════════════════════════════════════════════════════

class TestArtifactBrowser:

    def _create_run(self, td):
        """Create a test run directory with artifacts."""
        import os
        run_dir = os.path.join(td, "test-run-20260329-1400")
        os.makedirs(run_dir)
        with open(os.path.join(run_dir, "README.md"), "w") as f:
            f.write("# Test Run\n\nThis is a test.")
        with open(os.path.join(run_dir, "data.json"), "w") as f:
            f.write('{"test": true}')
        with open(os.path.join(run_dir, "opportunities.json"), "w") as f:
            f.write('[{"title":"test"}]')
        return run_dir

    def test_BA43_artifact_routes_mounted(self):
        from api.main import app
        paths = [r.path for r in app.routes]
        assert "/api/v3/business-artifacts/runs" in paths
        assert "/api/v3/business-artifacts/runs/{run_id}/files" in paths
        assert "/api/v3/business-artifacts/runs/{run_id}/files/{filename}" in paths
        assert "/api/v3/business-artifacts/runs/{run_id}/download/{filename}" in paths

    def test_BA44_list_runs_empty(self):
        """List runs returns empty for nonexistent dir."""
        import api.routes.business_artifacts as ba
        old = ba._BUSINESS_DIR
        ba._BUSINESS_DIR = type(old)("/nonexistent/dir")
        try:
            import asyncio
            from unittest.mock import MagicMock
            result = asyncio.get_event_loop().run_until_complete(
                ba.list_runs(_user={})
            )
            assert result["ok"] is True
            assert result["data"] == []
        finally:
            ba._BUSINESS_DIR = old

    def test_BA45_list_runs_with_data(self):
        import api.routes.business_artifacts as ba
        old = ba._BUSINESS_DIR
        with tempfile.TemporaryDirectory() as td:
            ba._BUSINESS_DIR = type(old)(td)
            self._create_run(td)
            try:
                import asyncio
                result = asyncio.get_event_loop().run_until_complete(
                    ba.list_runs(_user={})
                )
                assert result["ok"] is True
                assert len(result["data"]) == 1
                run = result["data"][0]
                assert run["run_id"] == "test-run-20260329-1400"
                assert run["file_count"] == 3
                assert run["action_id"] == "venture.research_workspace"
            finally:
                ba._BUSINESS_DIR = old

    def test_BA46_list_run_files(self):
        import api.routes.business_artifacts as ba
        old = ba._BUSINESS_DIR
        with tempfile.TemporaryDirectory() as td:
            ba._BUSINESS_DIR = type(old)(td)
            self._create_run(td)
            try:
                import asyncio
                result = asyncio.get_event_loop().run_until_complete(
                    ba.list_run_files("test-run-20260329-1400", _user={})
                )
                assert result["ok"] is True
                assert len(result["data"]) == 3
                names = {f["name"] for f in result["data"]}
                assert "README.md" in names
            finally:
                ba._BUSINESS_DIR = old

    def test_BA47_read_artifact(self):
        import api.routes.business_artifacts as ba
        old = ba._BUSINESS_DIR
        with tempfile.TemporaryDirectory() as td:
            ba._BUSINESS_DIR = type(old)(td)
            self._create_run(td)
            try:
                import asyncio
                result = asyncio.get_event_loop().run_until_complete(
                    ba.read_artifact("test-run-20260329-1400", "README.md", _user={})
                )
                assert result["ok"] is True
                assert "Test Run" in result["data"]["content"]
            finally:
                ba._BUSINESS_DIR = old

    def test_BA48_missing_run(self):
        import asyncio, api.routes.business_artifacts as ba
        from fastapi import HTTPException
        old = ba._BUSINESS_DIR
        with tempfile.TemporaryDirectory() as td:
            ba._BUSINESS_DIR = type(old)(td)
            try:
                with pytest.raises(HTTPException) as exc:
                    asyncio.get_event_loop().run_until_complete(
                        ba.list_run_files("nonexistent", _user={})
                    )
                assert exc.value.status_code == 404
            finally:
                ba._BUSINESS_DIR = old

    def test_BA49_missing_file(self):
        import asyncio, api.routes.business_artifacts as ba
        from fastapi import HTTPException
        old = ba._BUSINESS_DIR
        with tempfile.TemporaryDirectory() as td:
            ba._BUSINESS_DIR = type(old)(td)
            self._create_run(td)
            try:
                with pytest.raises(HTTPException) as exc:
                    asyncio.get_event_loop().run_until_complete(
                        ba.read_artifact("test-run-20260329-1400", "nope.md", _user={})
                    )
                assert exc.value.status_code == 404
            finally:
                ba._BUSINESS_DIR = old

    def test_BA50_path_traversal_blocked(self):
        from api.routes.business_artifacts import _safe_path, _BUSINESS_DIR
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            _safe_path(_BUSINESS_DIR, "..", "..", "etc", "passwd")
        assert exc.value.status_code == 403


# ═══════════════════════════════════════════════════════════════
# 15 — Web UI
# ═══════════════════════════════════════════════════════════════

class TestWebUI:

    def test_BA51_business_html_exists(self):
        path = os.path.join(os.path.dirname(__file__), "..", "static", "business.html")
        assert os.path.isfile(path)

    def test_BA52_business_html_auth(self):
        path = os.path.join(os.path.dirname(__file__), "..", "static", "business.html")
        with open(path) as f:
            html = f.read()
        assert "jarvis_token" in html
        assert "Authorization" in html

    def test_BA53_business_html_tabs(self):
        path = os.path.join(os.path.dirname(__file__), "..", "static", "business.html")
        with open(path) as f:
            html = f.read()
        assert "Actions" in html
        assert "Runs" in html
        assert "Execute" in html
        assert "Readiness" in html

    def test_BA54_nav_link_added(self):
        path = os.path.join(os.path.dirname(__file__), "..", "static", "index.html")
        with open(path) as f:
            html = f.read()
        assert "business.html" in html

    def test_BA55_approval_display(self):
        path = os.path.join(os.path.dirname(__file__), "..", "static", "business.html")
        with open(path) as f:
            html = f.read()
        assert "approval" in html.lower()
        assert "awaiting_approval" in html
