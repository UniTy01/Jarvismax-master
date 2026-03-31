"""
JARVIS MAX — Business Agent Registry API
==========================================
Exposes generated business agents through a structured registry.

For each agent exposes:
  id, template_source, business_type, capabilities,
  enabled_tools, health, last_test_result, current_score, version

Designed for integration with mobile dashboard and diagnostics.
"""
from __future__ import annotations

from typing import Any

from business_agents.factory import AgentFactory, GeneratedAgent
from business_agents.template_registry import list_templates, get_all_templates
from business_agents.test_harness import run_test_suite
from business_agents.improvement_bridge import get_improvement_bridge


def get_agent_registry(factory: AgentFactory | None = None) -> list[dict]:
    """Get full registry of all generated business agents."""
    if factory is None:
        factory = AgentFactory()

    bridge = get_improvement_bridge()
    agents = factory.list_agents()

    for agent_data in agents:
        # Enrich with performance stats
        stats = bridge.get_stats(agent_data["id"])
        if stats:
            agent_data["performance"] = {
                "success_rate": stats["success_rate"],
                "avg_score": stats["avg_score"],
                "total_executions": stats["total_executions"],
                "needs_improvement": stats["needs_improvement"],
            }
        else:
            agent_data["performance"] = {
                "success_rate": 0,
                "avg_score": 0,
                "total_executions": 0,
                "needs_improvement": False,
            }

        # Health classification
        perf = agent_data["performance"]
        if perf["total_executions"] == 0:
            agent_data["health"] = "untested"
        elif perf["success_rate"] >= 0.9:
            agent_data["health"] = "healthy"
        elif perf["success_rate"] >= 0.7:
            agent_data["health"] = "degraded"
        else:
            agent_data["health"] = "failing"

    return agents


def get_registry_summary(factory: AgentFactory | None = None) -> dict:
    """Summary for dashboard display."""
    if factory is None:
        factory = AgentFactory()

    agents = get_agent_registry(factory)
    templates = list_templates()

    return {
        "total_agents": len(agents),
        "total_templates": len(templates),
        "templates": templates,
        "by_health": {
            "healthy": sum(1 for a in agents if a.get("health") == "healthy"),
            "degraded": sum(1 for a in agents if a.get("health") == "degraded"),
            "failing": sum(1 for a in agents if a.get("health") == "failing"),
            "untested": sum(1 for a in agents if a.get("health") == "untested"),
        },
        "by_status": {
            "created": sum(1 for a in agents if a.get("status") == "created"),
            "tested": sum(1 for a in agents if a.get("status") == "tested"),
            "active": sum(1 for a in agents if a.get("status") == "active"),
            "disabled": sum(1 for a in agents if a.get("status") == "disabled"),
        },
        "agents": agents,
    }


def test_agent(factory: AgentFactory, agent_id: str) -> dict:
    """Run test suite for a specific agent and update its status."""
    agent = factory.get(agent_id)
    if not agent:
        return {"error": f"Agent not found: {agent_id}"}

    result = run_test_suite(agent)
    factory.update_test_result(agent_id, {
        "passed": result.passed == result.total_tests,
        "score": result.score,
        "total": result.total_tests,
        "passed_count": result.passed,
        "failed_count": result.failed,
    })

    return result.to_dict()
