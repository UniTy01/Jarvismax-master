"""
core/goal_decomposer.py — Converts vague goals into structured task plans.

Works WITH the existing Planner — called before build_plan() to break
high-level business goals into concrete, executable steps.

Does NOT replace the Planner. Provides structured input to it.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field, asdict
from typing import Optional

log = logging.getLogger("jarvis.goal_decomposer")


@dataclass
class TaskStep:
    """A single step in a decomposed plan."""
    id: int = 0
    action: str = ""
    tool: str = ""       # suggested tool name
    input_desc: str = ""
    output_desc: str = ""
    depends_on: list[int] = field(default_factory=list)
    retryable: bool = True
    skippable: bool = False
    validation: str = ""  # how to verify this step succeeded

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DecomposedGoal:
    """A vague goal decomposed into structured tasks."""
    original_goal: str = ""
    goal_type: str = ""   # website, document, data, api, research
    steps: list[TaskStep] = field(default_factory=list)
    estimated_complexity: str = "medium"
    tools_needed: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["step_count"] = len(self.steps)
        return d

    def to_plan(self) -> dict:
        """Convert to planner-compatible format."""
        return {
            "goal": self.original_goal,
            "steps": [
                {
                    "step": s.id,
                    "action": s.action,
                    "tool": s.tool,
                    "input": s.input_desc,
                    "expected_output": s.output_desc,
                    "depends_on": s.depends_on,
                    "validation": s.validation,
                }
                for s in self.steps
            ],
            "complexity": self.estimated_complexity,
            "tools": self.tools_needed,
        }


# ── Goal type detection ───────────────────────────────────────────────────────

_GOAL_PATTERNS: list[tuple[str, list[str]]] = [
    ("website", ["website", "landing page", "web page", "site web", "page web", "homepage"]),
    ("document", ["document", "report", "pdf", "markdown", "summary", "résumé", "compte-rendu"]),
    ("data", ["extract", "scrape", "parse", "json", "csv", "data", "données"]),
    ("api", ["api", "endpoint", "webhook", "integration", "intégration"]),
    ("email", ["email", "mail", "newsletter", "send", "envoyer"]),
    ("research", ["research", "analyse", "study", "compare", "find", "chercher", "recherche"]),
]


def detect_goal_type(goal: str) -> str:
    """Detect the type of goal from natural language."""
    goal_lower = goal.lower()
    scores = {}
    for gtype, keywords in _GOAL_PATTERNS:
        score = sum(1 for kw in keywords if kw in goal_lower)
        if score > 0:
            scores[gtype] = score
    if scores:
        return max(scores, key=scores.get)
    return "general"


# ── Template decompositions ───────────────────────────────────────────────────

_TEMPLATES: dict[str, list[dict]] = {
    "website": [
        {"action": "Define site structure", "tool": "markdown_generate", "validation": "structure document exists"},
        {"action": "Generate page content", "tool": "html_generate", "validation": "HTML file valid"},
        {"action": "Add styling and layout", "tool": "html_generate", "validation": "CSS applied"},
        {"action": "Create contact/CTA section", "tool": "html_generate", "validation": "form/CTA present"},
        {"action": "Verify all pages", "tool": "http_test", "validation": "HTTP 200 on all pages"},
    ],
    "document": [
        {"action": "Research topic", "tool": "web_search", "validation": "sources collected"},
        {"action": "Create outline", "tool": "markdown_generate", "validation": "outline with sections"},
        {"action": "Generate content", "tool": "markdown_generate", "validation": "content >500 words"},
        {"action": "Format and finalize", "tool": "file_write", "validation": "file written to workspace"},
    ],
    "data": [
        {"action": "Identify data source", "tool": "web_search", "validation": "source URL found"},
        {"action": "Fetch raw data", "tool": "http_request", "validation": "data retrieved"},
        {"action": "Parse and structure", "tool": "json_schema_generate", "validation": "structured output"},
        {"action": "Validate output", "tool": "file_read", "validation": "schema valid"},
        {"action": "Save results", "tool": "file_write", "validation": "file saved"},
    ],
    "api": [
        {"action": "Define API requirements", "tool": "json_schema_generate", "validation": "schema defined"},
        {"action": "Implement endpoint logic", "tool": "code_execute", "validation": "code written"},
        {"action": "Test endpoint", "tool": "http_test", "validation": "HTTP 200 response"},
    ],
    "email": [
        {"action": "Draft email content", "tool": "markdown_generate", "validation": "draft created"},
        {"action": "Review and approve", "tool": "file_read", "validation": "content approved"},
        {"action": "Send email", "tool": "email_send", "validation": "email sent confirmation"},
    ],
    "research": [
        {"action": "Search for information", "tool": "web_search", "validation": "results found"},
        {"action": "Fetch detailed sources", "tool": "web_fetch", "validation": "content extracted"},
        {"action": "Analyze and summarize", "tool": "markdown_generate", "validation": "summary created"},
        {"action": "Save findings", "tool": "file_write", "validation": "report saved"},
    ],
}


def decompose(goal: str) -> DecomposedGoal:
    """
    Decompose a vague goal into structured, executable steps.

    Uses template-based decomposition with goal type detection.
    Falls back to generic 3-step plan for unknown goal types.
    """
    goal_type = detect_goal_type(goal)
    template = _TEMPLATES.get(goal_type, [
        {"action": "Analyze requirements", "tool": "web_search", "validation": "requirements clear"},
        {"action": "Execute primary task", "tool": "file_write", "validation": "output produced"},
        {"action": "Verify results", "tool": "file_read", "validation": "output valid"},
    ])

    steps = []
    tools_needed = set()
    for i, tmpl in enumerate(template):
        step = TaskStep(
            id=i + 1,
            action=tmpl["action"],
            tool=tmpl.get("tool", ""),
            input_desc=goal if i == 0 else f"Output of step {i}",
            output_desc=tmpl.get("validation", ""),
            depends_on=[i] if i > 0 else [],
            retryable=True,
            skippable=i > 0,
            validation=tmpl.get("validation", ""),
        )
        steps.append(step)
        if step.tool:
            tools_needed.add(step.tool)

    complexity = "simple" if len(steps) <= 3 else "medium" if len(steps) <= 5 else "complex"

    return DecomposedGoal(
        original_goal=goal,
        goal_type=goal_type,
        steps=steps,
        estimated_complexity=complexity,
        tools_needed=sorted(tools_needed),
    )
