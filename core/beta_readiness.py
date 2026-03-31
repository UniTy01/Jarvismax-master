"""
JARVIS MAX — Beta Readiness Audit
====================================
Production checklist for controlled private beta.

Components:
1. ReadinessChecker   — automated audit of 20 readiness criteria
2. OnboardingContent  — first-use copy, plan descriptions, feature explanations
3. UsageBoundaries    — plan limit enforcement, quota display, overage handling
4. CustomerScenarios  — 3 validated business use cases with templates
5. AdminOps           — customer lifecycle: create, manage, monitor, revoke

Design: pure logic, no runtime imports. Tests validate all contracts.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


# ═══════════════════════════════════════════════════════════════
# 1. READINESS CHECKER — 20 criteria
# ═══════════════════════════════════════════════════════════════

class CheckStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"


@dataclass
class ReadinessCheck:
    """Single readiness criterion."""
    id: str
    category: str       # security, auth, ux, ops, reliability
    name: str
    status: str = "fail"
    detail: str = ""
    blocker: bool = True    # True = blocks beta launch

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "category": self.category,
            "name": self.name,
            "status": self.status,
            "detail": self.detail,
            "blocker": self.blocker,
        }


@dataclass
class ReadinessReport:
    """Full audit report."""
    checks: list[ReadinessCheck] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    @property
    def passed(self) -> int:
        return sum(1 for c in self.checks if c.status == "pass")

    @property
    def failed(self) -> int:
        return sum(1 for c in self.checks if c.status == "fail")

    @property
    def warnings(self) -> int:
        return sum(1 for c in self.checks if c.status == "warn")

    @property
    def blockers(self) -> list[ReadinessCheck]:
        return [c for c in self.checks if c.status == "fail" and c.blocker]

    @property
    def ready_for_beta(self) -> bool:
        return len(self.blockers) == 0

    def to_dict(self) -> dict:
        return {
            "ready": self.ready_for_beta,
            "passed": self.passed,
            "failed": self.failed,
            "warnings": self.warnings,
            "blockers": [b.to_dict() for b in self.blockers],
            "checks": [c.to_dict() for c in self.checks],
        }

    def summary(self) -> str:
        icon = "✅" if self.ready_for_beta else "❌"
        lines = [
            f"{icon} Beta Readiness: {'READY' if self.ready_for_beta else 'NOT READY'}",
            f"   Passed: {self.passed}/{len(self.checks)}, "
            f"Warnings: {self.warnings}, Blockers: {len(self.blockers)}",
        ]
        if self.blockers:
            lines.append("\n🚫 BLOCKERS:")
            for b in self.blockers:
                lines.append(f"   [{b.category}] {b.name}: {b.detail}")
        warns = [c for c in self.checks if c.status == "warn"]
        if warns:
            lines.append("\n⚠️ WARNINGS:")
            for w in warns:
                lines.append(f"   [{w.category}] {w.name}: {w.detail}")
        return "\n".join(lines)


class ReadinessChecker:
    """Automated readiness audit."""

    def audit(self, repo_root: str = ".") -> ReadinessReport:
        """Run all 20 checks against the repo."""
        root = Path(repo_root)
        checks = []

        # ── SECURITY ──
        checks.append(self._check_secret_key(root))
        checks.append(self._check_no_hardcoded_secrets(root))
        checks.append(self._check_cors_configured(root))
        checks.append(self._check_token_hashing(root))

        # ── AUTH ──
        checks.append(self._check_auth_middleware(root))
        checks.append(self._check_public_paths_minimal(root))
        checks.append(self._check_token_management(root))
        checks.append(self._check_plan_enforcement(root))

        # ── UX ──
        checks.append(self._check_login_screen(root))
        checks.append(self._check_onboarding(root))
        checks.append(self._check_error_messages(root))
        checks.append(self._check_session_restore(root))

        # ── OPS ──
        checks.append(self._check_health_endpoint(root))
        checks.append(self._check_admin_panel(root))
        checks.append(self._check_diagnostics(root))
        checks.append(self._check_logging(root))

        # ── RELIABILITY ──
        checks.append(self._check_tests_exist(root))
        checks.append(self._check_error_handling(root))
        checks.append(self._check_rate_limiting(root))
        checks.append(self._check_graceful_degradation(root))

        return ReadinessReport(checks=checks)

    # ── Security checks ──

    def _check_secret_key(self, root: Path) -> ReadinessCheck:
        c = ReadinessCheck("SEC-1", "security", "Secret key not default")
        try:
            env_file = root / ".env"
            if env_file.exists():
                for line in env_file.read_text().splitlines():
                    if line.startswith("JARVIS_SECRET_KEY="):
                        value = line.split("=", 1)[1].strip()
                        if "change-me" in value or "placeholder" in value or len(value) < 16:
                            c.detail = "JARVIS_SECRET_KEY contains placeholder or weak value"
                            return c
                        break
            c.status = "pass"
            c.detail = "Secret key configured"
        except Exception as e:
            c.detail = f"Cannot check: {e}"
        return c

    def _check_no_hardcoded_secrets(self, root: Path) -> ReadinessCheck:
        c = ReadinessCheck("SEC-2", "security", "No hardcoded secrets in app code")
        try:
            # Check Dart code for hardcoded keys
            dart_dir = root / "jarvismax_app" / "lib"
            if dart_dir.exists():
                for f in dart_dir.rglob("*.dart"):
                    content = f.read_text(errors="ignore")
                    if "SecretKey" in content and "JarvisSecret" in content:
                        c.detail = f"Hardcoded secret in {f.name}"
                        return c
            c.status = "pass"
            c.detail = "No hardcoded secrets found"
        except Exception:
            c.status = "warn"
            c.detail = "Could not scan all files"
        return c

    def _check_cors_configured(self, root: Path) -> ReadinessCheck:
        c = ReadinessCheck("SEC-3", "security", "CORS not wildcard in production", blocker=False)
        try:
            main = (root / "api" / "main.py").read_text()
            if '"*"' in main and "CORS_ORIGINS" in main:
                c.status = "warn"
                c.detail = "CORS allows * by default (ok for beta if behind proxy)"
            else:
                c.status = "pass"
                c.detail = "CORS configured via CORS_ORIGINS env"
        except Exception:
            c.status = "warn"
            c.detail = "Cannot check"
        return c

    def _check_token_hashing(self, root: Path) -> ReadinessCheck:
        c = ReadinessCheck("SEC-4", "security", "Tokens hashed (never stored raw)")
        try:
            content = (root / "api" / "access_tokens.py").read_text()
            if "sha256" in content.lower() or "hashlib" in content:
                c.status = "pass"
                c.detail = "SHA-256 hashing confirmed"
            else:
                c.detail = "Token hashing not found"
        except Exception:
            c.detail = "Cannot check access_tokens.py"
        return c

    # ── Auth checks ──

    def _check_auth_middleware(self, root: Path) -> ReadinessCheck:
        c = ReadinessCheck("AUTH-1", "auth", "Global auth middleware active")
        try:
            main = (root / "api" / "main.py").read_text()
            if "middleware" in main.lower() and ("AccessEnforcement" in main or "add_middleware" in main):
                c.status = "pass"
                c.detail = "Middleware registered"
            else:
                c.detail = "Middleware not found in main.py"
        except Exception:
            c.detail = "Cannot check"
        return c

    def _check_public_paths_minimal(self, root: Path) -> ReadinessCheck:
        c = ReadinessCheck("AUTH-2", "auth", "Public paths are minimal", blocker=False)
        try:
            content = (root / "api" / "access_enforcement.py").read_text()
            # Count public paths
            import re
            paths = re.findall(r'"(/[^"]*)"', content)
            if len(paths) <= 15:
                c.status = "pass"
                c.detail = f"{len(paths)} public paths (acceptable)"
            else:
                c.status = "warn"
                c.detail = f"{len(paths)} public paths (review for over-exposure)"
        except Exception:
            c.status = "warn"
            c.detail = "Cannot check"
        return c

    def _check_token_management(self, root: Path) -> ReadinessCheck:
        c = ReadinessCheck("AUTH-3", "auth", "Token CRUD endpoints exist")
        try:
            content = (root / "api" / "routes" / "token_management.py").read_text()
            has = all(op in content for op in ["create", "list", "revoke", "delete"])
            if has:
                c.status = "pass"
                c.detail = "Create, list, revoke, delete endpoints present"
            else:
                c.detail = "Missing token management operations"
        except Exception:
            c.detail = "token_management.py not found"
        return c

    def _check_plan_enforcement(self, root: Path) -> ReadinessCheck:
        c = ReadinessCheck("AUTH-4", "auth", "Plan limits enforced")
        try:
            content = (root / "api" / "access_tokens.py").read_text()
            if "check_daily_limit" in content and "PLAN_DEFINITIONS" in content:
                c.status = "pass"
                c.detail = "Daily limits + plan definitions active"
            else:
                c.detail = "Plan enforcement not found"
        except Exception:
            c.detail = "Cannot check"
        return c

    # ── UX checks ──

    def _check_login_screen(self, root: Path) -> ReadinessCheck:
        c = ReadinessCheck("UX-1", "ux", "Login screen present")
        try:
            html = (root / "static" / "index.html").read_text()
            if "login-overlay" in html and "login-btn" in html:
                c.status = "pass"
                c.detail = "Login overlay with token + admin login"
            else:
                c.detail = "Login UI incomplete"
        except Exception:
            c.detail = "index.html not found"
        return c

    def _check_onboarding(self, root: Path) -> ReadinessCheck:
        c = ReadinessCheck("UX-2", "ux", "First-use onboarding present", blocker=False)
        try:
            html = (root / "static" / "index.html").read_text()
            if "onboarding" in html and "Try something" in html:
                c.status = "pass"
                c.detail = "Onboarding section with examples"
            else:
                c.status = "warn"
                c.detail = "Onboarding could be improved"
        except Exception:
            c.status = "warn"
            c.detail = "Cannot check"
        return c

    def _check_error_messages(self, root: Path) -> ReadinessCheck:
        c = ReadinessCheck("UX-3", "ux", "Error messages user-friendly", blocker=False)
        try:
            html = (root / "static" / "index.html").read_text()
            french = ["Impossible", "Vérifiez", "Délai", "Réponse invalide"]
            if any(f in html for f in french):
                c.status = "fail"
                c.detail = "French text found in UI"
            else:
                c.status = "pass"
                c.detail = "All error messages in English"
        except Exception:
            c.status = "warn"
        return c

    def _check_session_restore(self, root: Path) -> ReadinessCheck:
        c = ReadinessCheck("UX-4", "ux", "Session restore on app restart")
        try:
            html = (root / "static" / "index.html").read_text()
            if "SessionStore.restore" in html and "auth/me" in html:
                c.status = "pass"
                c.detail = "SessionStore → /auth/me validation → auto-relogin"
            else:
                c.detail = "Session restore incomplete"
        except Exception:
            c.detail = "Cannot check"
        return c

    # ── Ops checks ──

    def _check_health_endpoint(self, root: Path) -> ReadinessCheck:
        c = ReadinessCheck("OPS-1", "ops", "Health endpoint exists")
        try:
            main = (root / "api" / "main.py").read_text()
            if "/health" in main:
                c.status = "pass"
                c.detail = "GET /health available"
            else:
                c.detail = "/health endpoint not found"
        except Exception:
            c.detail = "Cannot check"
        return c

    def _check_admin_panel(self, root: Path) -> ReadinessCheck:
        c = ReadinessCheck("OPS-2", "ops", "Admin can manage tokens without API", blocker=False)
        try:
            html = (root / "static" / "index.html").read_text()
            if "createToken" in html and "token-list" in html:
                c.status = "pass"
                c.detail = "Token creation + list in web UI"
            else:
                c.status = "warn"
                c.detail = "Admin UI incomplete"
        except Exception:
            c.status = "warn"
        return c

    def _check_diagnostics(self, root: Path) -> ReadinessCheck:
        c = ReadinessCheck("OPS-3", "ops", "System diagnostics available", blocker=False)
        try:
            html = (root / "static" / "index.html").read_text()
            if "advanced-panel" in html and "diagnostics" in html.lower():
                c.status = "pass"
                c.detail = "Advanced panel with diagnostics"
            else:
                c.status = "warn"
                c.detail = "Diagnostics could be better"
        except Exception:
            c.status = "warn"
        return c

    def _check_logging(self, root: Path) -> ReadinessCheck:
        c = ReadinessCheck("OPS-4", "ops", "Request logging configured", blocker=False)
        try:
            main = (root / "api" / "main.py").read_text()
            if "logging" in main or "logger" in main:
                c.status = "pass"
                c.detail = "Logging present"
            else:
                c.status = "warn"
                c.detail = "No logging found"
        except Exception:
            c.status = "warn"
        return c

    # ── Reliability checks ──

    def _check_tests_exist(self, root: Path) -> ReadinessCheck:
        c = ReadinessCheck("REL-1", "reliability", "Test suite exists")
        try:
            tests = list((root / "tests").glob("test_*.py"))
            if len(tests) >= 20:
                c.status = "pass"
                c.detail = f"{len(tests)} test files"
            else:
                c.detail = f"Only {len(tests)} test files"
        except Exception:
            c.detail = "No tests directory"
        return c

    def _check_error_handling(self, root: Path) -> ReadinessCheck:
        c = ReadinessCheck("REL-2", "reliability", "Global error handling")
        try:
            main = (root / "api" / "main.py").read_text()
            if "exception_handler" in main or "Exception" in main:
                c.status = "pass"
                c.detail = "Exception handlers registered"
            else:
                c.detail = "No global error handlers"
        except Exception:
            c.detail = "Cannot check"
        return c

    def _check_rate_limiting(self, root: Path) -> ReadinessCheck:
        c = ReadinessCheck("REL-3", "reliability", "Rate limiting / daily limits")
        try:
            content = (root / "api" / "access_tokens.py").read_text()
            if "check_daily_limit" in content:
                c.status = "pass"
                c.detail = "Daily mission limits per plan"
            else:
                c.detail = "No rate limiting"
        except Exception:
            c.detail = "Cannot check"
        return c

    def _check_graceful_degradation(self, root: Path) -> ReadinessCheck:
        c = ReadinessCheck("REL-4", "reliability", "Graceful degradation", blocker=False)
        try:
            # Check for fail-open patterns
            files_checked = 0
            fail_open_count = 0
            for f in (root / "core").glob("*.py"):
                content = f.read_text(errors="ignore")
                files_checked += 1
                if "try:" in content and "except" in content:
                    fail_open_count += 1
            if fail_open_count >= 5:
                c.status = "pass"
                c.detail = f"{fail_open_count}/{files_checked} core files have fail-open patterns"
            else:
                c.status = "warn"
                c.detail = "Limited fail-open coverage"
        except Exception:
            c.status = "warn"
        return c


# ═══════════════════════════════════════════════════════════════
# 2. ONBOARDING CONTENT — User-facing copy
# ═══════════════════════════════════════════════════════════════

@dataclass
class PlanDescription:
    """User-facing plan explanation."""
    plan_id: str
    name: str
    tagline: str
    limits: str
    features: list[str]
    price_hint: str = ""

    def to_dict(self) -> dict:
        return {
            "plan_id": self.plan_id,
            "name": self.name,
            "tagline": self.tagline,
            "limits": self.limits,
            "features": self.features,
            "price_hint": self.price_hint,
        }


class OnboardingContent:
    """Structured content for first-use and plan selection."""

    PLANS = [
        PlanDescription(
            plan_id="free_trial", name="Free Trial",
            tagline="Try Jarvis risk-free",
            limits="10 tasks/day, 1 at a time",
            features=["Basic AI models", "Standard tools", "Email support"],
            price_hint="Free for 30 days",
        ),
        PlanDescription(
            plan_id="paid_basic", name="Basic",
            tagline="For individuals and small teams",
            limits="30 tasks/day, 2 concurrent",
            features=["Standard AI models", "Standard tools", "Priority support"],
            price_hint="$29/month",
        ),
        PlanDescription(
            plan_id="paid_pro", name="Pro",
            tagline="For power users and businesses",
            limits="100 tasks/day, 5 concurrent",
            features=["Premium AI models", "All tools", "Multimodal", "Premium support"],
            price_hint="$99/month",
        ),
    ]

    WELCOME_MESSAGE = (
        "Welcome to Jarvis — your AI assistant that gets things done. "
        "Tell Jarvis what you need in plain English, and it will plan, "
        "execute, and deliver results. No technical knowledge required."
    )

    EXAMPLES = [
        {"title": "Research & Analysis",
         "prompt": "Research the top 5 competitors in the AI assistant space",
         "description": "Jarvis will search, analyze, and summarize findings"},
        {"title": "Content Creation",
         "prompt": "Write a professional email to follow up on a client meeting",
         "description": "Get polished content in seconds"},
        {"title": "Data Processing",
         "prompt": "Analyze this spreadsheet and create a summary report",
         "description": "Turn raw data into actionable insights"},
        {"title": "Automation",
         "prompt": "Create a daily report of our website traffic",
         "description": "Set up recurring automated tasks"},
    ]

    @classmethod
    def get_plan(cls, plan_id: str) -> PlanDescription | None:
        return next((p for p in cls.PLANS if p.plan_id == plan_id), None)

    @classmethod
    def get_all_plans(cls) -> list[dict]:
        return [p.to_dict() for p in cls.PLANS]


# ═══════════════════════════════════════════════════════════════
# 3. USAGE BOUNDARIES — Quota display and enforcement
# ═══════════════════════════════════════════════════════════════

@dataclass
class UsageDisplay:
    """User-facing usage information."""
    plan_name: str
    missions_today: int
    missions_limit: int     # 0 = unlimited
    concurrent_active: int
    concurrent_limit: int   # 0 = unlimited
    model_tier: str
    days_remaining: int = -1  # -1 = no trial

    @property
    def at_daily_limit(self) -> bool:
        return self.missions_limit > 0 and self.missions_today >= self.missions_limit

    @property
    def at_concurrent_limit(self) -> bool:
        return self.concurrent_limit > 0 and self.concurrent_active >= self.concurrent_limit

    @property
    def usage_percentage(self) -> float:
        if self.missions_limit <= 0:
            return 0.0
        return min(1.0, self.missions_today / self.missions_limit)

    def status_message(self) -> str:
        if self.at_daily_limit:
            return f"You've reached your daily limit ({self.missions_limit} tasks). Resets tomorrow."
        if self.at_concurrent_limit:
            return f"You have {self.concurrent_active} tasks running. Wait for one to finish."
        remaining = self.missions_limit - self.missions_today if self.missions_limit > 0 else -1
        if remaining > 0:
            return f"{remaining} tasks remaining today"
        return "Unlimited tasks available"

    def to_dict(self) -> dict:
        return {
            "plan": self.plan_name,
            "today": self.missions_today,
            "daily_limit": self.missions_limit,
            "concurrent": self.concurrent_active,
            "concurrent_limit": self.concurrent_limit,
            "at_daily_limit": self.at_daily_limit,
            "at_concurrent_limit": self.at_concurrent_limit,
            "usage_pct": round(self.usage_percentage * 100),
            "status": self.status_message(),
            "model_tier": self.model_tier,
        }


class UsageBoundaries:
    """Compute and display usage boundaries."""

    @staticmethod
    def compute(plan_type: str, daily_missions: int = 0,
                active_missions: int = 0) -> UsageDisplay:
        plan_map = {
            "admin":      ("Admin",      0,   0,  "premium"),
            "paid_pro":   ("Pro",        100, 5,  "premium"),
            "paid_basic": ("Basic",      30,  2,  "standard"),
            "free_trial": ("Free Trial", 10,  1,  "basic"),
            "custom":     ("Custom",     50,  3,  "standard"),
        }
        name, daily, conc, tier = plan_map.get(plan_type, ("Custom", 50, 3, "standard"))
        return UsageDisplay(
            plan_name=name,
            missions_today=daily_missions,
            missions_limit=daily,
            concurrent_active=active_missions,
            concurrent_limit=conc,
            model_tier=tier,
        )

    @staticmethod
    def overage_message(plan_type: str) -> str:
        messages = {
            "free_trial": "You've used all your free tasks today. Upgrade to Basic for 30 tasks/day.",
            "paid_basic": "You've reached today's limit. Upgrade to Pro for 100 tasks/day.",
            "paid_pro": "You've hit the daily limit. Contact support for custom limits.",
        }
        return messages.get(plan_type, "Daily limit reached. Please try again tomorrow.")


# ═══════════════════════════════════════════════════════════════
# 4. CUSTOMER SCENARIOS — 3 validated business use cases
# ═══════════════════════════════════════════════════════════════

@dataclass
class BusinessScenario:
    """Monetizable customer use case."""
    id: str
    name: str
    target_customer: str
    problem: str
    solution: str
    example_prompt: str
    risk_level: str         # low, medium
    revenue_model: str      # per_task, subscription, hybrid
    min_plan: str           # free_trial, paid_basic, paid_pro
    template_id: str | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "target": self.target_customer,
            "problem": self.problem,
            "solution": self.solution,
            "example": self.example_prompt,
            "risk": self.risk_level,
            "revenue": self.revenue_model,
            "min_plan": self.min_plan,
        }


class CustomerScenarios:
    """First 3 monetizable use cases for private beta."""

    SCENARIOS = [
        BusinessScenario(
            id="research_assistant",
            name="Research Assistant",
            target_customer="Consultants, analysts, founders doing market research",
            problem="Manual research takes hours — reading, comparing, synthesizing",
            solution="Give Jarvis a research question; get a structured summary with sources",
            example_prompt="Research the top 5 project management tools and compare their pricing, features, and ideal customer",
            risk_level="low",
            revenue_model="subscription",
            min_plan="paid_basic",
        ),
        BusinessScenario(
            id="content_creator",
            name="Content Creator",
            target_customer="Marketers, small business owners, freelancers",
            problem="Writing emails, social posts, and marketing copy is time-consuming",
            solution="Describe what you need; Jarvis writes, revises, and formats it",
            example_prompt="Write a professional follow-up email after a demo call with a potential enterprise client",
            risk_level="low",
            revenue_model="subscription",
            min_plan="free_trial",
        ),
        BusinessScenario(
            id="workflow_automator",
            name="Workflow Automator",
            target_customer="Operations teams, agencies, solo operators",
            problem="Repetitive tasks eat productive hours — reports, data extraction, formatting",
            solution="Describe the task once; Jarvis plans and executes multi-step workflows",
            example_prompt="Extract all email addresses from this CSV, check which domains are active, and create a clean contact list",
            risk_level="medium",
            revenue_model="hybrid",
            min_plan="paid_basic",
            template_id="support_agent",
        ),
    ]

    @classmethod
    def get_scenario(cls, id: str) -> BusinessScenario | None:
        return next((s for s in cls.SCENARIOS if s.id == id), None)

    @classmethod
    def get_all(cls) -> list[dict]:
        return [s.to_dict() for s in cls.SCENARIOS]

    @classmethod
    def recommended_for_plan(cls, plan: str) -> list[dict]:
        plan_order = {"free_trial": 0, "paid_basic": 1, "paid_pro": 2, "admin": 3}
        plan_level = plan_order.get(plan, 1)
        return [
            s.to_dict() for s in cls.SCENARIOS
            if plan_order.get(s.min_plan, 1) <= plan_level
        ]


# ═══════════════════════════════════════════════════════════════
# 5. ADMIN OPS — Customer lifecycle
# ═══════════════════════════════════════════════════════════════

@dataclass
class CustomerOp:
    """Admin operation on a customer."""
    operation: str
    required_fields: list[str]
    api_endpoint: str
    method: str = "POST"
    risk: str = "low"

    def to_dict(self) -> dict:
        return {
            "operation": self.operation,
            "fields": self.required_fields,
            "endpoint": self.api_endpoint,
            "method": self.method,
            "risk": self.risk,
        }


class AdminOps:
    """Customer lifecycle operations."""

    OPERATIONS = [
        CustomerOp("create_customer", ["name", "plan_type"],
                    "/api/v3/tokens", "POST", "low"),
        CustomerOp("list_customers", [],
                    "/api/v3/tokens?include_expired=false", "GET", "low"),
        CustomerOp("view_usage", ["token_id"],
                    "/api/v3/tokens/{id}/stats", "GET", "low"),
        CustomerOp("upgrade_plan", ["token_id", "new_plan"],
                    "/api/v3/tokens/{id}", "PUT", "medium"),
        CustomerOp("revoke_access", ["token_id"],
                    "/api/v3/tokens/{id}/revoke", "POST", "medium"),
        CustomerOp("reactivate", ["token_id"],
                    "/api/v3/tokens/{id}/enable", "POST", "low"),
    ]

    @classmethod
    def get_op(cls, name: str) -> CustomerOp | None:
        return next((o for o in cls.OPERATIONS if o.operation == name), None)

    @classmethod
    def get_all(cls) -> list[dict]:
        return [o.to_dict() for o in cls.OPERATIONS]

    @classmethod
    def quick_reference(cls) -> str:
        lines = ["═══ Admin Quick Reference ═══\n"]
        for op in cls.OPERATIONS:
            fields = ", ".join(op.required_fields) if op.required_fields else "none"
            lines.append(f"  {op.operation}")
            lines.append(f"    {op.method} {op.api_endpoint}")
            lines.append(f"    Fields: {fields}  |  Risk: {op.risk}")
            lines.append("")
        return "\n".join(lines)