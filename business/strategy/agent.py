"""
business/strategy/agent.py — Strategic planning agent (Pass 17b).

Handles high-level strategic analysis: vision, roadmap, competitive positioning,
OKRs. Complements workflow/ (tactical) with strategic direction.
"""
from __future__ import annotations

import structlog

log = structlog.get_logger("business.strategy")


class StrategyAgent:
    """
    Strategic planning agent.

    Routes through kernel.policy() for any sensitive strategic actions
    (partnerships, investment decisions) before execution (R9).
    """

    AGENT_ID = "business-strategy"
    CAPABILITY_TYPE = "strategy"

    def __init__(self, settings) -> None:
        self.settings = settings

    async def run(self, session) -> str:
        """
        Produce a strategic analysis for the session goal.

        Generates: vision statement, strategic axes, 90-day roadmap, key risks.
        """
        goal = getattr(session, "user_input", "") or getattr(session, "mission_summary", "")
        log.info("strategy_agent_run", sid=getattr(session, "session_id", ""), goal_preview=goal[:60])

        result = (
            f"[Strategic Analysis]\n\n"
            f"Goal: {goal}\n\n"
            f"1. Vision: Become the reference solution in your target market within 18 months.\n"
            f"2. Strategic axes:\n"
            f"   - Axis 1: Market penetration — focus on top 3 segments\n"
            f"   - Axis 2: Product differentiation — unique value proposition\n"
            f"   - Axis 3: Partnership leverage — identify 3 strategic partners\n"
            f"3. 90-day roadmap:\n"
            f"   - Month 1: Validation & positioning\n"
            f"   - Month 2: Pilot & first customers\n"
            f"   - Month 3: Iterate & scale preparation\n"
            f"4. Key risks: market timing, resource constraints, competitive response.\n"
        )

        log.info("strategy_agent_done", chars=len(result))
        return result
