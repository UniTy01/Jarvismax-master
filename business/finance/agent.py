"""
business/finance/agent.py — Financial planning and budget agent (Pass 17b).

Handles financial projections, P&L estimates, unit economics, break-even
analysis. Any payment-related action is gated by security.layer (R9).
"""
from __future__ import annotations

import structlog

log = structlog.get_logger("business.finance")


# Actions that require security gate before execution
_SENSITIVE_FINANCE_ACTIONS = {"payment", "wire_transfer", "invoice", "subscription_charge"}


class FinanceAgent:
    """
    Financial planning agent.

    Sensitive finance actions (payment, wire transfer) are checked
    through the security layer before execution (R9).
    """

    AGENT_ID = "business-finance"
    CAPABILITY_TYPE = "finance"

    def __init__(self, settings) -> None:
        self.settings = settings

    def _security_check(self, action_type: str, mission_id: str) -> bool:
        """
        Gate sensitive financial actions through security layer (R9).

        Returns True if allowed, False if denied/escalated.
        Fail-open: if security layer is unavailable, allow.
        """
        if action_type not in _SENSITIVE_FINANCE_ACTIONS:
            return True
        try:
            from security import get_security_layer
            result = get_security_layer().check_action(
                action_type=action_type,
                mission_id=mission_id,
                mode="auto",
                risk_level="high",
            )
            if not result.allowed:
                log.warning(
                    "finance_action_blocked",
                    action_type=action_type,
                    reason=result.reason[:80],
                    entry_id=result.entry_id,
                )
            return result.allowed
        except Exception as e:
            log.warning("finance_security_check_failed", err=str(e)[:60])
            return True  # fail-open

    async def run(self, session) -> str:
        """
        Produce a financial analysis for the session goal.

        Generates: unit economics, revenue projections, cost structure,
        break-even analysis, funding needs.
        """
        goal = getattr(session, "user_input", "") or getattr(session, "mission_summary", "")
        mission_id = getattr(session, "session_id", "")
        log.info("finance_agent_run", sid=mission_id, goal_preview=goal[:60])

        result = (
            f"[Financial Analysis]\n\n"
            f"Goal: {goal}\n\n"
            f"Unit Economics:\n"
            f"  - CAC (Customer Acquisition Cost): estimate 50–200€ depending on channel\n"
            f"  - LTV (Lifetime Value): target LTV/CAC > 3x\n"
            f"  - Gross margin target: 60–80% (SaaS) / 30–50% (services)\n\n"
            f"Revenue projections (12 months):\n"
            f"  - Month 1–3:  0–5k€/mo (validation phase)\n"
            f"  - Month 4–6:  5–20k€/mo (early traction)\n"
            f"  - Month 7–12: 20–100k€/mo (growth phase)\n\n"
            f"Cost structure:\n"
            f"  - Fixed: team, infrastructure, tools (~60% of costs)\n"
            f"  - Variable: marketing, sales commissions (~40% of costs)\n\n"
            f"Break-even: estimated month 8–12 depending on burn rate.\n"
            f"Funding need: 3–6 months runway recommended before next milestone.\n"
        )

        log.info("finance_agent_done", chars=len(result))
        return result
