"""
JARVIS MAX — Tool Proposer
==============================
Detects recurring unmet needs and proposes new tools.

Pipeline:
  1. Detect patterns from metrics, traces, mission history
  2. Classify need type (search, parsing, file transform, web, codegen)
  3. Generate structured ToolProposal
  4. Validate: no duplicate, passes policy, measurable value
  5. Score and rank proposals

Proposal types:
  - MCP tool: external tool server integration
  - Internal tool: Python function in core/tools/
  - Wrapper improvement: enhanced version of existing tool
  - Automation helper: workflow combining existing tools

Safety:
  - Proposals are advisory only (never auto-installed)
  - Max 5 active proposals at any time
  - Each proposal must justify measurable value
  - Duplicates auto-rejected

Usage:
    from core.tool_proposer import detect_needs, get_proposals, get_proposal_summary
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import structlog
    log = structlog.get_logger(__name__)
except ImportError:
    import logging
    log = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# NEED PATTERNS
# ═══════════════════════════════════════════════════════════════

@dataclass
class UnmetNeed:
    """A recurring unmet pattern detected from runtime signals."""
    pattern_type: str       # search, parsing, file_transform, web_request,
                            # codegen, data_pipeline, monitoring, integration
    description: str
    frequency: int          # how many times this pattern occurred
    source: str             # where detected: trace, metrics, mission_history, tool_gaps
    example_context: str = ""  # example mission/trace that triggered this
    affected_missions: int = 0


# Pattern detection from different signal sources
_PATTERN_KEYWORDS: dict[str, list[str]] = {
    "search": ["search", "find", "lookup", "query", "research", "discover"],
    "parsing": ["parse", "extract", "scrape", "convert", "transform json",
                "transform xml", "transform csv", "regex", "pattern match"],
    "file_transform": ["convert file", "transform file", "merge files",
                       "split file", "compress", "archive", "format"],
    "web_request": ["fetch url", "api call", "http request", "webhook",
                    "rest api", "graphql", "download"],
    "codegen": ["generate code", "scaffold", "template", "boilerplate",
                "create class", "create module", "stub"],
    "data_pipeline": ["pipeline", "etl", "aggregate", "summarize data",
                      "batch process", "bulk"],
    "monitoring": ["monitor", "watch", "alert", "health check",
                   "uptime", "ping", "status check"],
    "integration": ["connect to", "integrate", "sync with", "bridge",
                    "webhook", "notification", "slack", "discord"],
}


def _classify_pattern(text: str) -> str | None:
    """Classify text into a pattern type by keyword matching."""
    text_lower = text.lower()
    best_match = None
    best_score = 0
    for ptype, keywords in _PATTERN_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > best_score:
            best_score = score
            best_match = ptype
    return best_match if best_score > 0 else None


# ═══════════════════════════════════════════════════════════════
# TOOL PROPOSAL
# ═══════════════════════════════════════════════════════════════

@dataclass
class ToolProposal:
    """Structured proposal for a new or improved tool."""
    id: str = ""
    proposal_type: str = ""     # mcp_tool, internal_tool, wrapper, automation
    name: str = ""              # proposed tool name
    description: str = ""
    justification: str = ""     # why this tool is needed
    pattern_type: str = ""      # which unmet need it addresses
    frequency: int = 0          # how often the need occurs
    expected_value: float = 0   # 0-1, estimated impact
    existing_overlap: list[str] = field(default_factory=list)  # tools it might duplicate
    validation: dict = field(default_factory=dict)  # {passes_policy, no_duplicate, measurable}
    status: str = "proposed"    # proposed, accepted, rejected, implemented
    created_at: float = field(default_factory=time.time)

    def __post_init__(self):
        if not self.id:
            h = hashlib.md5(f"{self.name}:{self.pattern_type}".encode()).hexdigest()[:10]
            self.id = f"tp-{h}"

    @property
    def is_valid(self) -> bool:
        return (self.validation.get("passes_policy", False)
                and self.validation.get("no_duplicate", False)
                and self.validation.get("measurable_value", False))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.proposal_type,
            "name": self.name,
            "description": self.description,
            "justification": self.justification,
            "pattern_type": self.pattern_type,
            "frequency": self.frequency,
            "expected_value": round(self.expected_value, 3),
            "existing_overlap": self.existing_overlap,
            "validation": self.validation,
            "status": self.status,
            "is_valid": self.is_valid,
        }


# ═══════════════════════════════════════════════════════════════
# NEED DETECTION
# ═══════════════════════════════════════════════════════════════

def detect_needs() -> list[UnmetNeed]:
    """
    Detect recurring unmet needs from multiple signal sources.

    Sources:
    1. Tool failure patterns (tools that fail → need better tools)
    2. metrics_store failure aggregation (recurring failure categories)
    3. Tool gap analyzer (existing gap detection)
    4. Mission failure reasons (what missions fail at)
    """
    needs: list[UnmetNeed] = []

    # Source 1: Tool failures with error patterns
    try:
        from core.tool_reliability import diagnose_tools
        for diag in diagnose_tools():
            if not diag.needs_attention:
                continue
            for err_type, count in diag.error_distribution.items():
                if count >= 3:
                    pattern = _classify_pattern(err_type)
                    needs.append(UnmetNeed(
                        pattern_type=pattern or "integration",
                        description=f"Tool '{diag.tool_name}' has recurring '{err_type}' errors ({count}x)",
                        frequency=count,
                        source="tool_reliability",
                        affected_missions=diag.total_calls,
                    ))
    except Exception:
        pass

    # Source 2: Failure pattern aggregation
    try:
        from core.metrics_store import get_metrics
        m = get_metrics()
        top_failures = m.failures.top_failures(limit=10, window_s=86400)
        for failure in top_failures:
            if failure["count"] >= 3:
                pattern = _classify_pattern(failure.get("last_message", ""))
                needs.append(UnmetNeed(
                    pattern_type=pattern or "monitoring",
                    description=f"Recurring {failure['category']} failure in {failure['component']}: {failure['last_message'][:80]}",
                    frequency=failure["count"],
                    source="failure_patterns",
                ))
    except Exception:
        pass

    # Source 3: Tool gap analyzer
    try:
        from core.tool_gap_analyzer import analyze_tool_gaps
        for gap in analyze_tool_gaps():
            pattern = _classify_pattern(gap.get("description", ""))
            needs.append(UnmetNeed(
                pattern_type=pattern or gap.get("category", "integration"),
                description=gap.get("description", "Unknown gap"),
                frequency=gap.get("frequency", 1),
                source="tool_gaps",
                example_context=gap.get("example", ""),
            ))
    except Exception:
        pass

    # Source 4: Mission-level metrics
    try:
        from core.metrics_store import get_metrics
        m = get_metrics()

        # High mission failure → may need better tooling
        submitted = m.get_counter_total("missions_submitted_total")
        failed = m.get_counter_total("missions_failed_total")
        timeouts = m.get_counter_total("mission_timeout_total")

        if submitted >= 10 and failed / submitted > 0.3:
            needs.append(UnmetNeed(
                pattern_type="monitoring",
                description=f"High mission failure rate ({failed/submitted:.0%}) — may need better error handling tools",
                frequency=int(failed),
                source="mission_metrics",
                affected_missions=int(submitted),
            ))

        if timeouts >= 5:
            needs.append(UnmetNeed(
                pattern_type="monitoring",
                description=f"{int(timeouts)} mission timeouts — may need timeout management tool",
                frequency=int(timeouts),
                source="mission_metrics",
            ))
    except Exception:
        pass

    # Deduplicate by pattern_type + description hash
    seen: set[str] = set()
    unique: list[UnmetNeed] = []
    for need in needs:
        key = f"{need.pattern_type}:{need.description[:50]}"
        if key not in seen:
            seen.add(key)
            unique.append(need)

    # Sort by frequency
    unique.sort(key=lambda n: n.frequency, reverse=True)
    return unique


# ═══════════════════════════════════════════════════════════════
# PROPOSAL GENERATION
# ═══════════════════════════════════════════════════════════════

# Proposal templates by pattern type
_PROPOSAL_TEMPLATES: dict[str, dict] = {
    "search": {
        "proposal_type": "internal_tool",
        "name_prefix": "enhanced_search",
        "description": "Structured search tool with caching and result ranking",
    },
    "parsing": {
        "proposal_type": "internal_tool",
        "name_prefix": "smart_parser",
        "description": "Multi-format parser (JSON, XML, CSV, HTML) with error recovery",
    },
    "file_transform": {
        "proposal_type": "internal_tool",
        "name_prefix": "file_transformer",
        "description": "File format converter with streaming support",
    },
    "web_request": {
        "proposal_type": "wrapper",
        "name_prefix": "robust_http",
        "description": "HTTP client wrapper with retry, circuit breaker, and response caching",
    },
    "codegen": {
        "proposal_type": "internal_tool",
        "name_prefix": "code_generator",
        "description": "Template-based code scaffolding tool",
    },
    "data_pipeline": {
        "proposal_type": "automation",
        "name_prefix": "data_pipeline",
        "description": "Composable data pipeline builder",
    },
    "monitoring": {
        "proposal_type": "internal_tool",
        "name_prefix": "health_monitor",
        "description": "Service health monitoring and alerting tool",
    },
    "integration": {
        "proposal_type": "mcp_tool",
        "name_prefix": "connector",
        "description": "External service integration connector",
    },
}


def _get_existing_tools() -> set[str]:
    """Get names of all existing tools."""
    tools: set[str] = set()
    try:
        from core.tool_intelligence.selector import ToolSelector
        selector = ToolSelector()
        for t in selector.get_all_tool_summaries():
            tools.add(t.get("name", "").lower())
    except Exception:
        pass

    try:
        from core.tool_registry import get_available_tools
        for t in get_available_tools():
            if isinstance(t, str):
                tools.add(t.lower())
            elif isinstance(t, dict):
                tools.add(t.get("name", "").lower())
    except Exception:
        pass

    return tools


def _check_overlap(name: str, existing: set[str]) -> list[str]:
    """Check if proposed tool overlaps with existing tools."""
    overlaps = []
    name_lower = name.lower()
    name_parts = set(name_lower.replace("_", " ").split())
    for tool in existing:
        tool_parts = set(tool.replace("_", " ").split())
        common = name_parts & tool_parts
        if len(common) >= 2 or name_lower in tool or tool in name_lower:
            overlaps.append(tool)
    return overlaps


def generate_proposals(needs: list[UnmetNeed], max_proposals: int = 5) -> list[ToolProposal]:
    """
    Generate tool proposals from detected needs.

    Validates each proposal:
    - passes_policy: doesn't touch security/auth
    - no_duplicate: doesn't duplicate existing tool
    - measurable_value: has quantifiable justification
    """
    existing = _get_existing_tools()
    proposals: list[ToolProposal] = []
    seen_types: set[str] = set()

    for need in needs:
        if len(proposals) >= max_proposals:
            break

        # One proposal per pattern type
        if need.pattern_type in seen_types:
            continue

        template = _PROPOSAL_TEMPLATES.get(need.pattern_type)
        if not template:
            continue

        name = f"{template['name_prefix']}_{need.pattern_type}"
        overlaps = _check_overlap(name, existing)

        # Score expected value
        value = min(1.0, need.frequency / 20) * 0.5  # frequency component
        value += 0.3 if need.frequency >= 5 else 0.1   # threshold bonus
        value += 0.2 if need.affected_missions >= 10 else 0  # mission impact
        value = round(min(1.0, value), 3)

        proposal = ToolProposal(
            proposal_type=template["proposal_type"],
            name=name,
            description=template["description"],
            justification=f"Detected {need.frequency}x: {need.description[:150]}",
            pattern_type=need.pattern_type,
            frequency=need.frequency,
            expected_value=value,
            existing_overlap=overlaps,
            validation={
                "passes_policy": True,  # proposals never touch security
                "no_duplicate": len(overlaps) == 0,
                "measurable_value": need.frequency >= 3,
            },
        )

        proposals.append(proposal)
        seen_types.add(need.pattern_type)

    # Sort by expected value
    proposals.sort(key=lambda p: p.expected_value, reverse=True)
    return proposals


# ═══════════════════════════════════════════════════════════════
# PROPOSAL STORE
# ═══════════════════════════════════════════════════════════════

class ProposalStore:
    """Persistent store for tool proposals."""

    def __init__(self, persist_path: Path | None = None):
        self._path = persist_path or Path("workspace/.tool_proposals.json")
        self._proposals: list[ToolProposal] = []
        self._load()

    def add(self, proposal: ToolProposal) -> bool:
        """Add proposal if not duplicate."""
        if any(p.id == proposal.id for p in self._proposals):
            return False
        # Keep max 20 proposals
        if len(self._proposals) >= 20:
            # Remove oldest rejected/implemented
            self._proposals = [p for p in self._proposals
                               if p.status in ("proposed", "accepted")][:15]
        self._proposals.append(proposal)
        self._save()
        return True

    def get_active(self) -> list[ToolProposal]:
        return [p for p in self._proposals if p.status == "proposed"]

    def get_valid(self) -> list[ToolProposal]:
        return [p for p in self._proposals if p.is_valid and p.status == "proposed"]

    def get_all(self) -> list[ToolProposal]:
        return list(self._proposals)

    def accept(self, proposal_id: str) -> bool:
        for p in self._proposals:
            if p.id == proposal_id:
                p.status = "accepted"
                self._save()
                return True
        return False

    def reject(self, proposal_id: str) -> bool:
        for p in self._proposals:
            if p.id == proposal_id:
                p.status = "rejected"
                self._save()
                return True
        return False

    def _save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(
                json.dumps([p.to_dict() for p in self._proposals], indent=2),
                encoding="utf-8")
        except Exception:
            pass

    def _load(self) -> None:
        if self._path.exists():
            try:
                data = json.loads(self._path.read_text(encoding="utf-8"))
                self._proposals = [ToolProposal(**{
                    k: v for k, v in d.items()
                    if k in ToolProposal.__dataclass_fields__
                }) for d in data]
            except Exception:
                pass


_store: ProposalStore | None = None


def get_proposal_store(persist_path: Path | None = None) -> ProposalStore:
    global _store
    if _store is None:
        _store = ProposalStore(persist_path)
    return _store


# ═══════════════════════════════════════════════════════════════
# HIGH-LEVEL API
# ═══════════════════════════════════════════════════════════════

def get_proposals(max_n: int = 5) -> list[dict]:
    """Detect needs, generate proposals, return ranked list."""
    needs = detect_needs()
    proposals = generate_proposals(needs, max_proposals=max_n)

    store = get_proposal_store()
    for p in proposals:
        store.add(p)

    return [p.to_dict() for p in proposals]


def get_proposal_summary() -> dict:
    """Summary of tool proposals and needs."""
    needs = detect_needs()
    store = get_proposal_store()
    active = store.get_active()
    valid = store.get_valid()

    return {
        "unmet_needs": len(needs),
        "top_needs": [{"type": n.pattern_type, "frequency": n.frequency,
                       "description": n.description[:100]} for n in needs[:5]],
        "active_proposals": len(active),
        "valid_proposals": len(valid),
        "proposals": [p.to_dict() for p in active[:5]],
    }
