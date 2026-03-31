"""
kernel/capabilities/registry.py — Capability-first routing registry.

Capabilities are the primary abstraction — agents are just bundles of capabilities.
The orchestrator routes based on what the system CAN DO, not who does it.

Delegates to core/capability_routing/ for actual resolution.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field


@dataclass
class Capability:
    """A discrete capability the system can execute."""
    id: str
    name: str = ""
    description: str = ""
    category: str = ""  # planning, execution, analysis, tool, memory, policy
    providers: list[str] = field(default_factory=list)  # agent roles or tool IDs
    risk_level: str = "low"
    requires_approval: bool = False

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name or self.id,
            "description": self.description,
            "category": self.category,
            "providers": self.providers,
            "risk_level": self.risk_level,
            "requires_approval": self.requires_approval,
        }


# ── Kernel Capabilities ──────────────────────────────────────

KERNEL_CAPABILITIES: dict[str, Capability] = {
    "plan_generation": Capability(
        id="plan_generation",
        name="Plan Generation",
        description="Generate an execution plan from a goal",
        category="planning",
        providers=["ceo", "architect"],
    ),
    "plan_validation": Capability(
        id="plan_validation",
        name="Plan Validation",
        description="Validate a plan for correctness and safety",
        category="planning",
        providers=["architect", "reviewer"],
    ),
    "decision_evaluation": Capability(
        id="decision_evaluation",
        name="Decision Evaluation",
        description="Evaluate a decision for confidence and risk",
        category="planning",
        providers=["ceo", "reviewer"],
    ),
    "skill_execution": Capability(
        id="skill_execution",
        name="Skill Execution",
        description="Execute a domain skill (market research, persona, etc.)",
        category="execution",
        providers=["analyst"],
    ),
    "tool_invocation": Capability(
        id="tool_invocation",
        name="Tool Invocation",
        description="Invoke an external tool safely",
        category="execution",
        providers=["operator"],
        requires_approval=True,
    ),
    "code_generation": Capability(
        id="code_generation",
        name="Code Generation",
        description="Generate or modify code",
        category="execution",
        providers=["engineer"],
        risk_level="medium",
    ),
    "quality_review": Capability(
        id="quality_review",
        name="Quality Review",
        description="Review outputs for quality and correctness",
        category="execution",
        providers=["reviewer"],
    ),
    "memory_write": Capability(
        id="memory_write",
        name="Memory Write",
        description="Persist a memory record",
        category="memory",
        providers=["system"],
    ),
    "memory_recall": Capability(
        id="memory_recall",
        name="Memory Recall",
        description="Retrieve relevant memories",
        category="memory",
        providers=["system"],
    ),
    "risk_evaluation": Capability(
        id="risk_evaluation",
        name="Risk Evaluation",
        description="Compute risk score for an action",
        category="policy",
        providers=["system"],
    ),
    "policy_check": Capability(
        id="policy_check",
        name="Policy Check",
        description="Check if an action is allowed by policy",
        category="policy",
        providers=["system"],
    ),
    "artifact_generation": Capability(
        id="artifact_generation",
        name="Artifact Generation",
        description="Produce structured output artifacts",
        category="execution",
        providers=["analyst", "engineer"],
    ),

    # ── Economic Intelligence Capabilities ─────────────────

    "market_intelligence": Capability(
        id="market_intelligence",
        name="Market Intelligence",
        description="Analyze markets, identify opportunities, estimate TAM/SAM/SOM",
        category="economic",
        providers=["analyst"],
    ),
    "product_design": Capability(
        id="product_design",
        name="Product Design",
        description="Structure business concepts, value propositions, delivery mechanisms",
        category="economic",
        providers=["analyst", "architect"],
    ),
    "financial_reasoning": Capability(
        id="financial_reasoning",
        name="Financial Reasoning",
        description="Heuristic pricing, cost estimation, break-even analysis",
        category="economic",
        providers=["analyst"],
    ),
    "compliance_reasoning": Capability(
        id="compliance_reasoning",
        name="Compliance Reasoning",
        description="Identify regulatory considerations and risk flags (not legal advice)",
        category="economic",
        providers=["analyst"],
        risk_level="medium",
    ),
    "risk_assessment": Capability(
        id="risk_assessment",
        name="Risk Assessment",
        description="Evaluate business and execution risks for ventures",
        category="economic",
        providers=["analyst", "reviewer"],
    ),
    "venture_planning": Capability(
        id="venture_planning",
        name="Venture Planning",
        description="Create milestone-based venture plans from business concepts",
        category="economic",
        providers=["analyst", "ceo"],
    ),
    "strategy_reasoning": Capability(
        id="strategy_reasoning",
        name="Strategy Reasoning",
        description="Evaluate strategic options, positioning, competitive advantage",
        category="economic",
        providers=["analyst", "ceo"],
    ),
}


class KernelCapabilityRegistry:
    """Thread-safe registry of kernel capabilities."""

    def __init__(self):
        self._lock = threading.Lock()
        self._capabilities: dict[str, Capability] = dict(KERNEL_CAPABILITIES)

    def get(self, capability_id: str) -> Capability | None:
        with self._lock:
            return self._capabilities.get(capability_id)

    def list_all(self) -> list[Capability]:
        with self._lock:
            return list(self._capabilities.values())

    def list_by_category(self, category: str) -> list[Capability]:
        return [c for c in self.list_all() if c.category == category]

    def providers_for(self, capability_id: str) -> list[str]:
        cap = self.get(capability_id)
        return cap.providers if cap else []

    def register(self, capability: Capability) -> None:
        with self._lock:
            self._capabilities[capability.id] = capability

    def stats(self) -> dict:
        caps = self.list_all()
        categories = {}
        for c in caps:
            categories[c.category] = categories.get(c.category, 0) + 1
        return {
            "total": len(caps),
            "by_category": categories,
            "approval_required": sum(1 for c in caps if c.requires_approval),
        }


_registry: KernelCapabilityRegistry | None = None
_lock = threading.Lock()


def get_capability_registry() -> KernelCapabilityRegistry:
    global _registry
    if _registry is None:
        with _lock:
            if _registry is None:
                _registry = KernelCapabilityRegistry()
    return _registry
