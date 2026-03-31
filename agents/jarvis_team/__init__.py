"""
JARVIS MAX — Jarvis Agent Team
================================
Meta-level agents that work ON the JarvisMax codebase itself.

These are NOT mission-execution agents (scout-research, forge-builder, etc.).
These are system-building agents that improve, validate, and maintain JarvisMax.

Agents:
    jarvis-architect  — system architecture decisions
    jarvis-coder      — implement code changes
    jarvis-reviewer   — validate diffs and detect regressions
    jarvis-qa         — create and run tests
    jarvis-devops     — deployment and environment validation
    jarvis-watcher    — monitor logs and detect anomalies

Constraints:
    - Agents work on separate branches
    - All changes reviewed before merge
    - No direct push to main
    - Fail-open philosophy preserved
"""
from agents.jarvis_team.architect import JarvisArchitect
from agents.jarvis_team.coder import JarvisCoder
from agents.jarvis_team.reviewer import JarvisReviewer
from agents.jarvis_team.qa import JarvisQA
from agents.jarvis_team.devops import JarvisDevOps
from agents.jarvis_team.watcher import JarvisWatcher

JARVIS_TEAM_AGENTS = {
    "jarvis-architect": JarvisArchitect,
    "jarvis-coder":     JarvisCoder,
    "jarvis-reviewer":  JarvisReviewer,
    "jarvis-qa":        JarvisQA,
    "jarvis-devops":    JarvisDevOps,
    "jarvis-watcher":   JarvisWatcher,
}

__all__ = [
    "JarvisArchitect",
    "JarvisCoder",
    "JarvisReviewer",
    "JarvisQA",
    "JarvisDevOps",
    "JarvisWatcher",
    "JARVIS_TEAM_AGENTS",
]
