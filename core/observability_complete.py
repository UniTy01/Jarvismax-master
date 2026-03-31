"""
JARVIS MAX — Complete Observability Layer
==========================================
Makes all critical runtime behaviors visible, persisted, and actionable.

Components:
1. MetricsCompleteness  — emitters for every subsystem (orchestrator, executor, tools,
                          memory, routing, self-improvement, multimodal)
2. SnapshotPersistence  — safe restart-resilient metric snapshots with load-on-start
3. AlertEngine          — 8 alert conditions with severity, context, and recommendations
4. TraceSummaryBuilder  — rich mission trace: model, tools, time, cost, why success/failure
5. OperatorDiagnostics  — unified diagnostics for both technical operators and product admins

Design: composable layer on top of metrics_store.py and trace_intelligence.py.
All methods fail-open (try/except, never crash caller).
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


# ═══════════════════════════════════════════════════════════════
# 1. METRICS COMPLETENESS — Subsystem emitters
# ═══════════════════════════════════════════════════════════════

class SubsystemMetrics:
    """
    Centralized emitter registry for all JarvisMax subsystems.
    Each emit_*() is fail-open: silently handles import or runtime errors.
    """

    def __init__(self, registry=None):
        self._registry = registry

    def _reg(self):
        """Lazy-get registry."""
        if self._registry is not None:
            return self._registry
        try:
            from core.metrics_store import get_metrics
            return get_metrics()
        except Exception:
            return None

    # ── Orchestrator ──
    def emit_plan_created(self, mission_id: str = "", step_count: int = 0) -> None:
        r = self._reg()
        if r:
            r.inc("plans_created_total")
            if step_count > 0:
                r.observe("plan_step_count", step_count, labels={"mission": mission_id[:32]})

    def emit_plan_validation(self, valid: bool, errors: int = 0) -> None:
        r = self._reg()
        if r:
            r.inc("plan_validations_total")
            if not valid:
                r.inc("plan_validation_failures_total")
                r.observe("plan_validation_errors", errors)

    def emit_capability_dispatch(self, capability: str, latency_ms: float = 0) -> None:
        r = self._reg()
        if r:
            r.inc("capability_dispatches_total", labels={"capability": capability})
            if latency_ms > 0:
                r.observe("capability_dispatch_latency_ms", latency_ms)

    # ── Executor ──
    def emit_step_executed(self, step: str, success: bool, duration_ms: float = 0) -> None:
        r = self._reg()
        if r:
            r.inc("steps_executed_total", labels={"step": step[:32]})
            if not success:
                r.inc("step_failures_total", labels={"step": step[:32]})
            if duration_ms > 0:
                r.observe("step_duration_ms", duration_ms, labels={"step": step[:32]})

    def emit_partial_result(self, outcome: str) -> None:
        r = self._reg()
        if r:
            r.inc("partial_results_total", labels={"outcome": outcome})

    def emit_completion_guard(self, complete: bool, blocking: int = 0) -> None:
        r = self._reg()
        if r:
            r.inc("completion_checks_total")
            if not complete:
                r.inc("completion_blocked_total")
                r.observe("blocking_steps_count", blocking)

    def emit_stress_shield(self, rejected: bool = False) -> None:
        r = self._reg()
        if r:
            if rejected:
                r.inc("stress_shield_rejections_total")
            r.inc("stress_shield_checks_total")

    # ── Memory ──
    def emit_memory_store(self, memory_type: str, accepted: bool) -> None:
        r = self._reg()
        if r:
            r.inc("memory_store_total", labels={"type": memory_type})
            if not accepted:
                r.inc("memory_store_rejected_total", labels={"type": memory_type})

    def emit_memory_retrieve(self, hit_count: int = 0, latency_ms: float = 0) -> None:
        r = self._reg()
        if r:
            r.inc("memory_retrieve_total")
            r.observe("memory_retrieve_hits", hit_count)
            if latency_ms > 0:
                r.observe("memory_retrieve_latency_ms", latency_ms)

    def emit_memory_prune(self, removed: int = 0) -> None:
        r = self._reg()
        if r:
            r.inc("memory_prune_total")
            r.observe("memory_pruned_items", removed)

    def emit_memory_dedup(self, duplicates_found: int = 0) -> None:
        r = self._reg()
        if r:
            r.inc("memory_dedup_total")
            if duplicates_found > 0:
                r.observe("memory_duplicates_found", duplicates_found)

    # ── Model Routing ──
    def emit_routing_decision(self, model: str, reason: str = "",
                              cost_tier: str = "standard") -> None:
        r = self._reg()
        if r:
            r.inc("routing_decisions_total", labels={"model": model, "cost_tier": cost_tier})

    def emit_routing_fallback(self, from_model: str, to_model: str, reason: str = "") -> None:
        r = self._reg()
        if r:
            r.inc("routing_fallbacks_total", labels={"from": from_model, "to": to_model})
            if reason:
                r.record_failure("routing_fallback", "model_routing", reason)

    def emit_routing_health_update(self, model: str, health_score: float) -> None:
        r = self._reg()
        if r:
            r.set_gauge("model_health_score", health_score, labels={"model": model})

    # ── Self-Improvement ──
    def emit_experiment_started(self, strategy: str, priority: float = 0) -> None:
        r = self._reg()
        if r:
            r.inc("improvement_experiments_total", labels={"strategy": strategy})
            if priority > 0:
                r.observe("experiment_priority", priority)

    def emit_experiment_result(self, strategy: str, outcome: str,
                               score_delta: float = 0) -> None:
        r = self._reg()
        if r:
            r.inc(f"experiment_{outcome}_total", labels={"strategy": strategy})
            if score_delta != 0:
                r.observe("experiment_score_delta", score_delta)

    def emit_lesson_stored(self, strategy: str, result: str) -> None:
        r = self._reg()
        if r:
            r.inc("lessons_stored_total", labels={"strategy": strategy, "result": result})

    def emit_lesson_reused(self, similarity: float = 0) -> None:
        r = self._reg()
        if r:
            r.inc("lessons_reused_total")
            if similarity > 0:
                r.observe("lesson_similarity", similarity)

    # ── Provider ──
    def emit_provider_error(self, provider: str, error_type: str = "unknown") -> None:
        r = self._reg()
        if r:
            r.inc("provider_errors_total", labels={"provider": provider, "type": error_type})

    def emit_provider_latency(self, provider: str, latency_ms: float = 0) -> None:
        r = self._reg()
        if r:
            if latency_ms > 0:
                r.observe("provider_latency_ms", latency_ms, labels={"provider": provider})

    # ── Cost ──
    def emit_cost_event(self, model: str, tokens: int = 0,
                        cost_usd: float = 0, mission_id: str = "") -> None:
        r = self._reg()
        if r:
            r.inc("cost_events_total", labels={"model": model})
            if cost_usd > 0:
                r.observe("cost_usd", cost_usd, labels={"model": model})
            if tokens > 0:
                r.observe("tokens_used", tokens, labels={"model": model})


# ═══════════════════════════════════════════════════════════════
# 2. SNAPSHOT PERSISTENCE — Restart-resilient metrics
# ═══════════════════════════════════════════════════════════════

@dataclass
class MetricsSnapshot:
    """Point-in-time metrics snapshot for persistence."""
    timestamp: float = field(default_factory=time.time)
    counters: dict[str, dict[str, float]] = field(default_factory=dict)
    gauges: dict[str, dict[str, float]] = field(default_factory=dict)
    cost_data: dict = field(default_factory=dict)
    version: int = 1


class SnapshotPersistence:
    """
    Saves and restores metrics across restarts.
    Atomic writes (tmp + rename).
    """

    def __init__(self, path: str | Path = "workspace/metrics_snapshot.json"):
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def save(self, registry) -> bool:
        """Save current metrics to disk. Returns True on success."""
        try:
            snap = MetricsSnapshot()

            # Extract counters
            for name, counter in getattr(registry, "_counters", {}).items():
                snap.counters[name] = counter.get_all()

            # Extract gauges
            for name, gauge in getattr(registry, "_gauges", {}).items():
                snap.gauges[name] = gauge.get_all()

            # Extract cost
            if hasattr(registry, "_cost_tracker"):
                snap.cost_data = registry._cost_tracker.snapshot()

            data = {
                "timestamp": snap.timestamp,
                "version": snap.version,
                "counters": snap.counters,
                "gauges": snap.gauges,
                "cost": snap.cost_data,
            }

            tmp = self._path.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
            os.replace(str(tmp), str(self._path))
            return True
        except Exception:
            return False

    def load(self, registry) -> bool:
        """Restore metrics from disk into registry. Returns True on success."""
        try:
            if not self._path.exists():
                return False

            data = json.loads(self._path.read_text(encoding="utf-8"))
            if data.get("version", 0) != 1:
                return False

            # Restore counters
            for name, labels_map in data.get("counters", {}).items():
                for labels_key, value in labels_map.items():
                    registry.inc(name, value=value, labels={"_raw": labels_key} if labels_key else None)

            # Restore gauges
            for name, labels_map in data.get("gauges", {}).items():
                for labels_key, value in labels_map.items():
                    registry.set_gauge(name, value, labels={"_raw": labels_key} if labels_key else None)

            return True
        except Exception:
            return False

    def exists(self) -> bool:
        return self._path.exists()

    @property
    def path(self) -> Path:
        return self._path


# ═══════════════════════════════════════════════════════════════
# 3. ALERT ENGINE — 8 alert conditions
# ═══════════════════════════════════════════════════════════════

class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class Alert:
    """Structured alert."""
    name: str
    severity: str
    current_value: float
    threshold: float
    context: dict = field(default_factory=dict)
    recommendation: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "alert": self.name,
            "severity": self.severity,
            "current": round(self.current_value, 3),
            "threshold": round(self.threshold, 3),
            "context": self.context,
            "recommendation": self.recommendation[:200],
            "timestamp": self.timestamp,
        }


class AlertEngine:
    """
    Evaluates 8 alert conditions against metrics registry.
    All checks fail-open.
    """

    DEFAULT_THRESHOLDS = {
        "mission_success_rate_min": 0.7,
        "tool_failure_rate_max": 0.3,
        "provider_failure_rate_max": 0.2,
        "retry_storm_max": 10,
        "circuit_breaker_opens_max": 3,
        "memory_miss_rate_max": 0.5,
        "cost_per_hour_max_usd": 5.0,
        "experiment_rejection_rate_max": 0.8,
    }

    def __init__(self, thresholds: dict | None = None):
        self._thresholds = {**self.DEFAULT_THRESHOLDS, **(thresholds or {})}

    def evaluate(self, registry) -> list[Alert]:
        """Evaluate all alert conditions. Returns triggered alerts."""
        alerts = []

        try:
            alerts.extend(self._check_mission_success(registry))
        except Exception:
            pass
        try:
            alerts.extend(self._check_tool_failures(registry))
        except Exception:
            pass
        try:
            alerts.extend(self._check_provider_failures(registry))
        except Exception:
            pass
        try:
            alerts.extend(self._check_retry_storm(registry))
        except Exception:
            pass
        try:
            alerts.extend(self._check_circuit_breaker(registry))
        except Exception:
            pass
        try:
            alerts.extend(self._check_memory_misses(registry))
        except Exception:
            pass
        try:
            alerts.extend(self._check_cost(registry))
        except Exception:
            pass
        try:
            alerts.extend(self._check_experiment_rejections(registry))
        except Exception:
            pass

        return alerts

    def _check_mission_success(self, r) -> list[Alert]:
        submitted = r.get_counter_total("missions_submitted_total")
        completed = r.get_counter_total("missions_completed_total")
        if submitted < 5:
            return []
        rate = completed / submitted
        thresh = self._thresholds["mission_success_rate_min"]
        if rate >= thresh:
            return []
        return [Alert(
            name="low_mission_success_rate",
            severity="critical" if rate < 0.5 else "warning",
            current_value=rate, threshold=thresh,
            context={"submitted": int(submitted), "completed": int(completed)},
            recommendation="Check failure patterns in trace summaries; consider retry/fallback changes",
        )]

    def _check_tool_failures(self, r) -> list[Alert]:
        total = r.get_counter_total("tool_invocations_total")
        failures = r.get_counter_total("tool_failures_total")
        if total < 10:
            return []
        rate = failures / total
        thresh = self._thresholds["tool_failure_rate_max"]
        if rate <= thresh:
            return []
        # Find worst tool
        worst = self._find_worst_label(r, "tool_failures_total")
        return [Alert(
            name="high_tool_failure_rate",
            severity="critical" if rate > 0.5 else "warning",
            current_value=rate, threshold=thresh,
            context={"total_invocations": int(total), "failures": int(failures),
                      "worst_tool": worst},
            recommendation=f"Deprioritize or fix tool '{worst}'; check tool health dashboard",
        )]

    def _check_provider_failures(self, r) -> list[Alert]:
        total = r.get_counter_total("model_selected_total")
        failures = r.get_counter_total("provider_errors_total")
        if total < 5:
            return []
        rate = failures / max(total, 1)
        thresh = self._thresholds["provider_failure_rate_max"]
        if rate <= thresh:
            return []
        worst = self._find_worst_label(r, "provider_errors_total")
        return [Alert(
            name="high_provider_failure_rate",
            severity="critical" if rate > 0.4 else "warning",
            current_value=rate, threshold=thresh,
            context={"worst_provider": worst},
            recommendation=f"Provider '{worst}' unstable; route to alternate model",
        )]

    def _check_retry_storm(self, r) -> list[Alert]:
        retries = r.get_counter_total("retry_attempts_total")
        thresh = self._thresholds["retry_storm_max"]
        if retries <= thresh:
            return []
        return [Alert(
            name="retry_storm",
            severity="critical" if retries > 20 else "warning",
            current_value=retries, threshold=thresh,
            recommendation="Reduce concurrent load; check if provider is rate-limiting",
        )]

    def _check_circuit_breaker(self, r) -> list[Alert]:
        opens = r.get_counter_total("circuit_breaker_open_total")
        thresh = self._thresholds["circuit_breaker_opens_max"]
        if opens <= thresh:
            return []
        return [Alert(
            name="circuit_breaker_flapping",
            severity="critical",
            current_value=opens, threshold=thresh,
            recommendation="Provider instability; consider manual failover",
        )]

    def _check_memory_misses(self, r) -> list[Alert]:
        total = r.get_counter_total("memory_retrieve_total")
        if total < 10:
            return []
        hits_hist = r.get_histogram("memory_retrieve_hits")
        avg_hits = hits_hist.get("mean", 1) if isinstance(hits_hist, dict) else 1
        if avg_hits >= 1:
            return []
        return [Alert(
            name="high_memory_miss_rate",
            severity="warning",
            current_value=avg_hits, threshold=1.0,
            context={"total_queries": int(total)},
            recommendation="Memory may be empty or queries too narrow; check IntelligentMemory stats",
        )]

    def _check_cost(self, r) -> list[Alert]:
        # Check cost tracker if available
        cost_data = {}
        if hasattr(r, "_cost_tracker"):
            cost_data = r._cost_tracker.snapshot()
        total_cost = cost_data.get("total_cost_usd", 0)
        thresh = self._thresholds["cost_per_hour_max_usd"]
        if total_cost <= thresh:
            return []
        return [Alert(
            name="high_cost",
            severity="critical" if total_cost > thresh * 3 else "warning",
            current_value=total_cost, threshold=thresh,
            context={"total_tokens": cost_data.get("total_tokens", 0)},
            recommendation="Switch to cheaper models or reduce token usage",
        )]

    def _check_experiment_rejections(self, r) -> list[Alert]:
        started = r.get_counter_total("improvement_experiments_total")
        rejected = r.get_counter_total("experiment_rejected_total")
        if started < 5:
            return []
        rate = rejected / started
        thresh = self._thresholds["experiment_rejection_rate_max"]
        if rate <= thresh:
            return []
        return [Alert(
            name="high_experiment_rejection_rate",
            severity="warning",
            current_value=rate, threshold=thresh,
            context={"started": int(started), "rejected": int(rejected)},
            recommendation="Improvement loop may be targeting wrong areas; review prioritization",
        )]

    @staticmethod
    def _find_worst_label(r, metric_name: str) -> str:
        """Find the label key with highest counter value."""
        try:
            counter = r._counters.get(metric_name)
            if not counter:
                return "unknown"
            worst, worst_val = "unknown", 0
            for lk, v in counter.get_all().items():
                if v > worst_val:
                    worst_val = v
                    worst = lk
            return worst
        except Exception:
            return "unknown"


# ═══════════════════════════════════════════════════════════════
# 4. TRACE SUMMARY BUILDER — Rich mission traces
# ═══════════════════════════════════════════════════════════════

@dataclass
class RichTraceSummary:
    """Enhanced trace summary with model, tools, cost, time, and causal analysis."""
    mission_id: str
    status: str = "unknown"
    duration_ms: float = 0

    # Models
    models_used: list[dict] = field(default_factory=list)
    primary_model: str = ""
    total_model_calls: int = 0

    # Tools
    tools_used: list[dict] = field(default_factory=list)
    primary_tool: str = ""
    total_tool_calls: int = 0
    tool_success_rate: float = 1.0

    # Time
    time_breakdown: dict[str, float] = field(default_factory=dict)  # phase → ms
    slowest_phase: str = ""

    # Cost
    total_tokens: int = 0
    estimated_cost_usd: float = 0

    # Causal analysis
    success_reason: str = ""
    failure_reason: str = ""
    failure_component: str = ""
    recommendation: str = ""

    def to_dict(self) -> dict:
        return {
            "mission_id": self.mission_id,
            "status": self.status,
            "duration_ms": round(self.duration_ms, 1),
            "models": {"used": self.models_used, "primary": self.primary_model,
                        "total_calls": self.total_model_calls},
            "tools": {"used": self.tools_used, "primary": self.primary_tool,
                       "total_calls": self.total_tool_calls,
                       "success_rate": round(self.tool_success_rate, 3)},
            "time": {"breakdown": self.time_breakdown, "slowest_phase": self.slowest_phase},
            "cost": {"total_tokens": self.total_tokens,
                      "estimated_usd": round(self.estimated_cost_usd, 4)},
            "analysis": {"success_reason": self.success_reason,
                          "failure_reason": self.failure_reason,
                          "failure_component": self.failure_component,
                          "recommendation": self.recommendation},
        }

    def narrative(self) -> str:
        """Human-readable trace narrative."""
        lines = [f"═══ Mission {self.mission_id}: {self.status.upper()} ═══"]

        # Duration
        if self.duration_ms > 0:
            secs = self.duration_ms / 1000
            lines.append(f"⏱  Duration: {secs:.1f}s")

        # Models
        if self.models_used:
            lines.append(f"\n🤖 Models ({self.total_model_calls} calls):")
            for m in self.models_used[:5]:
                lines.append(f"   {m.get('model', '?')}: {m.get('calls', 0)} calls, "
                             f"{m.get('avg_latency_ms', 0):.0f}ms avg")

        # Tools
        if self.tools_used:
            lines.append(f"\n🔧 Tools ({self.total_tool_calls} calls, "
                         f"{self.tool_success_rate:.0%} success):")
            for t in self.tools_used[:5]:
                status = "✅" if t.get("success_rate", 1) > 0.9 else "⚠️"
                lines.append(f"   {status} {t.get('tool', '?')}: "
                             f"{t.get('calls', 0)} calls, {t.get('avg_ms', 0):.0f}ms")

        # Time breakdown
        if self.time_breakdown:
            lines.append(f"\n⏰ Time breakdown:")
            total = sum(self.time_breakdown.values()) or 1
            for phase, ms in sorted(self.time_breakdown.items(), key=lambda x: -x[1]):
                pct = (ms / total) * 100
                bar = "█" * int(pct // 5)
                lines.append(f"   {phase:20s} {bar} {pct:.0f}% ({ms:.0f}ms)")

        # Cost
        if self.total_tokens > 0 or self.estimated_cost_usd > 0:
            lines.append(f"\n💰 Cost: {self.total_tokens:,} tokens, "
                         f"~${self.estimated_cost_usd:.4f}")

        # Causal analysis
        if self.status == "success" and self.success_reason:
            lines.append(f"\n✅ Why success: {self.success_reason}")
        elif self.failure_reason:
            lines.append(f"\n❌ Why failed: {self.failure_reason}")
            if self.failure_component:
                lines.append(f"   Component: {self.failure_component}")
            if self.recommendation:
                lines.append(f"   💡 Recommendation: {self.recommendation}")

        return "\n".join(lines)


class TraceSummaryBuilder:
    """Builds rich trace summaries from raw events."""

    # Cost per 1M tokens by tier (rough estimates)
    COST_PER_1M = {"local": 0, "nano": 0.10, "cheap": 0.50,
                    "standard": 3.00, "premium": 15.00}

    def build(self, mission_id: str, events: list[dict]) -> RichTraceSummary:
        """Build RichTraceSummary from trace events."""
        summary = RichTraceSummary(mission_id=mission_id)
        if not events:
            return summary

        model_stats: dict[str, dict] = {}
        tool_stats: dict[str, dict] = {}
        phase_times: dict[str, float] = {}
        total_tokens = 0
        start_time = None
        end_time = None
        failure_info = {}

        for event in events:
            ts = event.get("timestamp", 0)
            if start_time is None or ts < start_time:
                start_time = ts
            if end_time is None or ts > end_time:
                end_time = ts

            etype = event.get("event", event.get("type", ""))
            component = event.get("component", "")

            # Model events
            if "model" in etype or etype in ("llm_invoke", "model_selected", "llm_response"):
                model_id = event.get("model_id", event.get("model", "unknown"))
                if model_id not in model_stats:
                    model_stats[model_id] = {"calls": 0, "total_ms": 0, "tokens": 0}
                model_stats[model_id]["calls"] += 1
                model_stats[model_id]["total_ms"] += event.get("latency_ms", event.get("duration_ms", 0))
                model_stats[model_id]["tokens"] += event.get("tokens", 0)
                total_tokens += event.get("tokens", 0)

            # Tool events
            if "tool" in etype or etype in ("tool_execute", "tool_result"):
                tool_name = event.get("tool_name", event.get("tool", "unknown"))
                if tool_name not in tool_stats:
                    tool_stats[tool_name] = {"calls": 0, "success": 0, "total_ms": 0}
                tool_stats[tool_name]["calls"] += 1
                if event.get("success", True):
                    tool_stats[tool_name]["success"] += 1
                tool_stats[tool_name]["total_ms"] += event.get("duration_ms", 0)

            # Phase timing
            if event.get("phase") and event.get("duration_ms", 0) > 0:
                phase = event["phase"]
                phase_times[phase] = phase_times.get(phase, 0) + event["duration_ms"]

            # Failure
            if event.get("error") or event.get("failure"):
                failure_info = {
                    "reason": event.get("error", event.get("failure", ""))[:200],
                    "component": component,
                }

            # Status
            if event.get("status") in ("success", "failed", "timeout"):
                summary.status = event["status"]

        # Duration
        if start_time and end_time:
            summary.duration_ms = (end_time - start_time) * 1000

        # Models
        for model_id, stats in model_stats.items():
            avg_ms = stats["total_ms"] / max(stats["calls"], 1)
            summary.models_used.append({
                "model": model_id, "calls": stats["calls"],
                "avg_latency_ms": round(avg_ms, 1), "tokens": stats["tokens"],
            })
        summary.total_model_calls = sum(s["calls"] for s in model_stats.values())
        if model_stats:
            summary.primary_model = max(model_stats, key=lambda m: model_stats[m]["calls"])

        # Tools
        total_tool_ok = 0
        total_tool_calls = 0
        for tool_name, stats in tool_stats.items():
            sr = stats["success"] / max(stats["calls"], 1)
            avg_ms = stats["total_ms"] / max(stats["calls"], 1)
            summary.tools_used.append({
                "tool": tool_name, "calls": stats["calls"],
                "success_rate": round(sr, 3), "avg_ms": round(avg_ms, 1),
            })
            total_tool_ok += stats["success"]
            total_tool_calls += stats["calls"]
        summary.total_tool_calls = total_tool_calls
        summary.tool_success_rate = total_tool_ok / max(total_tool_calls, 1)
        if tool_stats:
            summary.primary_tool = max(tool_stats, key=lambda t: tool_stats[t]["calls"])

        # Time
        summary.time_breakdown = phase_times
        if phase_times:
            summary.slowest_phase = max(phase_times, key=lambda p: phase_times[p])

        # Cost
        summary.total_tokens = total_tokens
        # Rough estimate at standard tier
        summary.estimated_cost_usd = (total_tokens / 1_000_000) * self.COST_PER_1M.get("standard", 3.0)

        # Causal analysis
        if summary.status == "success":
            if summary.tool_success_rate > 0.9:
                summary.success_reason = "All tools succeeded; model produced valid output"
            else:
                summary.success_reason = "Completed despite some tool failures"
        elif failure_info:
            summary.failure_reason = failure_info.get("reason", "Unknown")
            summary.failure_component = failure_info.get("component", "")
            if "timeout" in summary.failure_reason.lower():
                summary.recommendation = "Increase timeout or use faster model"
            elif "tool" in summary.failure_component.lower():
                summary.recommendation = "Check tool availability; consider fallback tool"
            else:
                summary.recommendation = "Inspect failure logs; check model/provider health"

        return summary


# ═══════════════════════════════════════════════════════════════
# 5. OPERATOR DIAGNOSTICS — Unified view
# ═══════════════════════════════════════════════════════════════

@dataclass
class DiagnosticsReport:
    """Unified diagnostics for operators and admins."""
    timestamp: float = field(default_factory=time.time)
    uptime_s: float = 0

    # Health
    overall_health: str = "healthy"  # healthy, degraded, critical
    health_score: float = 1.0       # 0.0-1.0

    # Metrics summary
    missions: dict = field(default_factory=dict)
    tools: dict = field(default_factory=dict)
    models: dict = field(default_factory=dict)
    memory: dict = field(default_factory=dict)
    improvement: dict = field(default_factory=dict)

    # Active alerts
    alerts: list[dict] = field(default_factory=list)

    # Cost
    cost: dict = field(default_factory=dict)

    # Recommendations
    top_issues: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "uptime_s": round(self.uptime_s, 1),
            "health": {"status": self.overall_health, "score": round(self.health_score, 3)},
            "missions": self.missions,
            "tools": self.tools,
            "models": self.models,
            "memory": self.memory,
            "improvement": self.improvement,
            "alerts": self.alerts,
            "cost": self.cost,
            "top_issues": self.top_issues,
        }

    def operator_summary(self) -> str:
        """Technical operator view."""
        health_icon = {"healthy": "🟢", "degraded": "🟡", "critical": "🔴"}.get(
            self.overall_health, "⚪")
        lines = [
            f"═══ JarvisMax Diagnostics ═══",
            f"{health_icon} Health: {self.overall_health.upper()} ({self.health_score:.0%})",
            f"⏱  Uptime: {self.uptime_s / 3600:.1f}h",
        ]

        m = self.missions
        if m:
            lines.append(f"\n📋 Missions: {m.get('submitted', 0)} submitted, "
                         f"{m.get('completed', 0)} completed, "
                         f"{m.get('failed', 0)} failed "
                         f"({m.get('success_rate', 0):.0%} success)")

        t = self.tools
        if t:
            lines.append(f"🔧 Tools: {t.get('invocations', 0)} calls, "
                         f"{t.get('success_rate', 0):.0%} success"
                         + (f", worst: {t.get('worst_tool', '?')}" if t.get("worst_tool") else ""))

        mo = self.models
        if mo:
            lines.append(f"🤖 Models: {mo.get('selections', 0)} selections, "
                         f"{mo.get('failures', 0)} failures"
                         + (f", primary: {mo.get('primary', '?')}" if mo.get("primary") else ""))

        mem = self.memory
        if mem:
            lines.append(f"🧠 Memory: {mem.get('searches', 0)} searches, "
                         f"{mem.get('stores', 0)} stores")

        imp = self.improvement
        if imp:
            lines.append(f"🔄 Improvement: {imp.get('experiments', 0)} experiments, "
                         f"{imp.get('promoted', 0)} promoted, "
                         f"{imp.get('rejected', 0)} rejected")

        c = self.cost
        if c:
            lines.append(f"\n💰 Cost: {c.get('total_tokens', 0):,} tokens, "
                         f"~${c.get('total_usd', 0):.4f}")

        if self.alerts:
            lines.append(f"\n⚠️  Active alerts ({len(self.alerts)}):")
            for a in self.alerts[:5]:
                sev = {"critical": "🔴", "warning": "🟡"}.get(a.get("severity"), "⚪")
                lines.append(f"   {sev} {a.get('alert', '?')}: {a.get('recommendation', '')[:60]}")

        if self.top_issues:
            lines.append(f"\n🎯 Top issues:")
            for issue in self.top_issues[:3]:
                lines.append(f"   • {issue}")

        return "\n".join(lines)

    def admin_summary(self) -> str:
        """Non-technical admin view."""
        health_icon = {"healthy": "🟢", "degraded": "🟡", "critical": "🔴"}.get(
            self.overall_health, "⚪")
        lines = [
            f"{health_icon} System is {self.overall_health}",
        ]

        m = self.missions
        if m:
            lines.append(f"📊 {m.get('completed', 0)} tasks completed successfully "
                         f"({m.get('success_rate', 0):.0%} success rate)")

        c = self.cost
        if c and c.get("total_usd", 0) > 0:
            lines.append(f"💰 Cost so far: ${c.get('total_usd', 0):.2f}")

        if self.alerts:
            critical = [a for a in self.alerts if a.get("severity") == "critical"]
            if critical:
                lines.append(f"⚠️ {len(critical)} critical issue(s) need attention")

        return "\n".join(lines)


class OperatorDiagnostics:
    """Builds diagnostics reports from metrics registry + alerts."""

    def __init__(self, start_time: float | None = None):
        self._start_time = start_time or time.time()

    def build(self, registry, alerts: list[Alert] | None = None) -> DiagnosticsReport:
        """Build a full diagnostics report."""
        report = DiagnosticsReport()
        report.uptime_s = time.time() - self._start_time

        try:
            r = registry

            # Missions
            submitted = r.get_counter_total("missions_submitted_total")
            completed = r.get_counter_total("missions_completed_total")
            failed = r.get_counter_total("missions_failed_total")
            report.missions = {
                "submitted": int(submitted),
                "completed": int(completed),
                "failed": int(failed),
                "success_rate": completed / max(submitted, 1),
            }

            # Tools
            tool_total = r.get_counter_total("tool_invocations_total")
            tool_fail = r.get_counter_total("tool_failures_total")
            worst = AlertEngine._find_worst_label(r, "tool_failures_total")
            report.tools = {
                "invocations": int(tool_total),
                "failures": int(tool_fail),
                "success_rate": 1 - (tool_fail / max(tool_total, 1)),
                "worst_tool": worst if worst != "unknown" else None,
            }

            # Models
            selections = r.get_counter_total("model_selected_total")
            model_failures = r.get_counter_total("model_failure_total")
            primary = AlertEngine._find_worst_label(r, "model_selected_total")
            report.models = {
                "selections": int(selections),
                "failures": int(model_failures),
                "primary": primary if primary != "unknown" else None,
            }

            # Memory
            searches = r.get_counter_total("memory_search_total")
            stores = r.get_counter_total("memory_store_total")
            report.memory = {
                "searches": int(searches),
                "stores": int(stores),
            }

            # Improvement
            experiments = r.get_counter_total("improvement_experiments_total")
            promoted = r.get_counter_total("experiment_promoted_total")
            rejected = r.get_counter_total("experiment_rejected_total")
            report.improvement = {
                "experiments": int(experiments),
                "promoted": int(promoted),
                "rejected": int(rejected),
            }

            # Cost
            if hasattr(r, "_cost_tracker"):
                cost_data = r._cost_tracker.snapshot()
                report.cost = {
                    "total_tokens": cost_data.get("total_tokens", 0),
                    "total_usd": cost_data.get("total_cost_usd", 0),
                }

            # Alerts
            if alerts:
                report.alerts = [a.to_dict() if hasattr(a, "to_dict") else a for a in alerts]

            # Health score
            issues = []
            sr = report.missions.get("success_rate", 1)
            if sr < 0.7:
                issues.append(f"Mission success rate low ({sr:.0%})")
            tr = report.tools.get("success_rate", 1)
            if tr < 0.7:
                issues.append(f"Tool reliability low ({tr:.0%})")
            if report.alerts:
                critical_count = len([a for a in report.alerts if a.get("severity") == "critical"])
                if critical_count > 0:
                    issues.append(f"{critical_count} critical alert(s) active")

            report.top_issues = issues
            report.health_score = max(0, 1.0 - len(issues) * 0.25)
            if report.health_score < 0.5:
                report.overall_health = "critical"
            elif report.health_score < 0.8:
                report.overall_health = "degraded"
            else:
                report.overall_health = "healthy"

        except Exception:
            report.overall_health = "unknown"

        return report