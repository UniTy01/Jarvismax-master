"""
Tests — Complete Observability Layer

Metrics Completeness
  O1.  Orchestrator emitters increment
  O2.  Executor emitters increment
  O3.  Memory emitters increment
  O4.  Routing emitters increment
  O5.  Self-improvement emitters increment
  O6.  Provider emitters increment
  O7.  Cost emitters increment
  O8.  Fail-open: no registry → no crash

Snapshot Persistence
  O9.  Save snapshot to disk
  O10. Load snapshot restores counters
  O11. Missing file returns False
  O12. Corrupt file returns False

Alert Triggers
  O13. Low mission success → alert
  O14. High tool failure → alert
  O15. Provider failure → alert
  O16. Retry storm → alert
  O17. Circuit breaker flapping → alert
  O18. Cost alert → triggered
  O19. Experiment rejection → alert
  O20. Healthy metrics → no alerts

Trace Summary
  O21. Build from model events
  O22. Build from tool events
  O23. Build from mixed events
  O24. Empty events → empty summary
  O25. Narrative includes all sections
  O26. Failure causal analysis populated

Diagnostics
  O27. Report has all sections
  O28. Operator summary readable
  O29. Admin summary simplified
  O30. Health score degrades with issues
  O31. No-regression: snapshot round-trip
  O32. No-regression: alerts produce dicts
"""
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.observability_complete import (
    SubsystemMetrics, MetricsSnapshot, SnapshotPersistence,
    AlertSeverity, Alert, AlertEngine,
    RichTraceSummary, TraceSummaryBuilder,
    DiagnosticsReport, OperatorDiagnostics,
)


# ── Minimal mock registry for testing ──

class MockCounter:
    def __init__(self):
        self._data: dict[str, float] = {}
    def inc(self, labels_key="", value=1.0):
        self._data[labels_key] = self._data.get(labels_key, 0) + value
    def get(self, labels_key=""):
        return self._data.get(labels_key, 0)
    def get_all(self):
        return dict(self._data)
    def total(self):
        return sum(self._data.values())

class MockHistogram:
    def __init__(self):
        self._samples: dict[str, list] = {}
    def observe(self, value, labels_key=""):
        self._samples.setdefault(labels_key, []).append(value)
    def stats(self, labels_key=""):
        s = self._samples.get(labels_key, [])
        if not s: return {"count": 0, "mean": 0, "min": 0, "max": 0, "p50": 0, "p99": 0}
        return {"count": len(s), "mean": sum(s)/len(s), "min": min(s), "max": max(s)}
    def get_all_keys(self):
        return list(self._samples.keys())

class MockGauge:
    def __init__(self):
        self._data: dict[str, float] = {}
    def set(self, value, labels_key=""):
        self._data[labels_key] = value
    def get(self, labels_key=""):
        return self._data.get(labels_key, 0)
    def get_all(self):
        return dict(self._data)

class MockCostTracker:
    def __init__(self):
        self.total_cost_usd = 0
        self.total_tokens = 0
    def snapshot(self):
        return {"total_cost_usd": self.total_cost_usd, "total_tokens": self.total_tokens}

class MockRegistry:
    def __init__(self):
        self._counters: dict[str, MockCounter] = {}
        self._histograms: dict[str, MockHistogram] = {}
        self._gauges: dict[str, MockGauge] = {}
        self._cost_tracker = MockCostTracker()

    @staticmethod
    def _labels_key(labels):
        if not labels: return ""
        return ",".join(f"{k}={v}" for k, v in sorted(labels.items()))

    def inc(self, name, value=1.0, labels=None):
        if name not in self._counters:
            self._counters[name] = MockCounter()
        self._counters[name].inc(self._labels_key(labels), value)

    def get_counter(self, name, labels=None):
        c = self._counters.get(name)
        if not c: return 0
        return c.get(self._labels_key(labels))

    def get_counter_total(self, name):
        c = self._counters.get(name)
        if not c: return 0
        return c.total()

    def observe(self, name, value, labels=None):
        if name not in self._histograms:
            self._histograms[name] = MockHistogram()
        self._histograms[name].observe(value, self._labels_key(labels))

    def get_histogram(self, name, labels=None):
        h = self._histograms.get(name)
        if not h: return {"count": 0, "mean": 0}
        return h.stats(self._labels_key(labels))

    def set_gauge(self, name, value, labels=None):
        if name not in self._gauges:
            self._gauges[name] = MockGauge()
        self._gauges[name].set(value, self._labels_key(labels))

    def get_gauge(self, name, labels=None):
        g = self._gauges.get(name)
        if not g: return 0
        return g.get(self._labels_key(labels))

    def record_failure(self, category, component, message, **kwargs):
        pass  # no-op for tests


# ═══════════════════════════════════════════════════════════════
# METRICS COMPLETENESS
# ═══════════════════════════════════════════════════════════════

class TestMetricsCompleteness:

    def test_orchestrator_emitters(self):
        """O1: Orchestrator emitters increment."""
        r = MockRegistry()
        m = SubsystemMetrics(registry=r)
        m.emit_plan_created("m1", step_count=5)
        m.emit_plan_validation(valid=True)
        m.emit_capability_dispatch("code_generation", latency_ms=100)
        assert r.get_counter_total("plans_created_total") == 1
        assert r.get_counter_total("capability_dispatches_total") == 1

    def test_executor_emitters(self):
        """O2: Executor emitters increment."""
        r = MockRegistry()
        m = SubsystemMetrics(registry=r)
        m.emit_step_executed("step1", success=True, duration_ms=50)
        m.emit_step_executed("step2", success=False, duration_ms=100)
        m.emit_partial_result("partial_success")
        m.emit_completion_guard(complete=False, blocking=2)
        m.emit_stress_shield(rejected=True)
        assert r.get_counter_total("steps_executed_total") == 2
        assert r.get_counter_total("step_failures_total") == 1
        assert r.get_counter_total("stress_shield_rejections_total") == 1

    def test_memory_emitters(self):
        """O3: Memory emitters increment."""
        r = MockRegistry()
        m = SubsystemMetrics(registry=r)
        m.emit_memory_store("knowledge", accepted=True)
        m.emit_memory_store("short_term", accepted=False)
        m.emit_memory_retrieve(hit_count=3, latency_ms=5)
        m.emit_memory_prune(removed=10)
        m.emit_memory_dedup(duplicates_found=2)
        assert r.get_counter_total("memory_store_total") == 2
        assert r.get_counter_total("memory_store_rejected_total") == 1
        assert r.get_counter_total("memory_prune_total") == 1

    def test_routing_emitters(self):
        """O4: Routing emitters increment."""
        r = MockRegistry()
        m = SubsystemMetrics(registry=r)
        m.emit_routing_decision("gpt-4o", reason="best score", cost_tier="premium")
        m.emit_routing_fallback("gpt-4o", "gpt-3.5", reason="timeout")
        m.emit_routing_health_update("gpt-4o", health_score=0.85)
        assert r.get_counter_total("routing_decisions_total") == 1
        assert r.get_counter_total("routing_fallbacks_total") == 1

    def test_improvement_emitters(self):
        """O5: Self-improvement emitters increment."""
        r = MockRegistry()
        m = SubsystemMetrics(registry=r)
        m.emit_experiment_started("timeout_tuning", priority=0.85)
        m.emit_experiment_result("timeout_tuning", "promoted", score_delta=0.5)
        m.emit_lesson_stored("timeout_tuning", "success")
        m.emit_lesson_reused(similarity=0.8)
        assert r.get_counter_total("improvement_experiments_total") == 1
        assert r.get_counter_total("experiment_promoted_total") == 1
        assert r.get_counter_total("lessons_stored_total") == 1

    def test_provider_emitters(self):
        """O6: Provider emitters increment."""
        r = MockRegistry()
        m = SubsystemMetrics(registry=r)
        m.emit_provider_error("openai", "rate_limit")
        m.emit_provider_error("anthropic", "timeout")
        m.emit_provider_latency("openai", latency_ms=500)
        assert r.get_counter_total("provider_errors_total") == 2

    def test_cost_emitters(self):
        """O7: Cost emitters increment."""
        r = MockRegistry()
        m = SubsystemMetrics(registry=r)
        m.emit_cost_event("gpt-4o", tokens=1500, cost_usd=0.045)
        assert r.get_counter_total("cost_events_total") == 1

    def test_no_registry_no_crash(self):
        """O8: Fail-open with no registry."""
        m = SubsystemMetrics(registry=None)
        # None of these should raise
        m.emit_plan_created("m1")
        m.emit_step_executed("s1", success=True)
        m.emit_memory_store("knowledge", accepted=True)
        m.emit_routing_decision("gpt-4o")
        m.emit_experiment_started("timeout_tuning")
        m.emit_provider_error("openai", "timeout")
        m.emit_cost_event("gpt-4o")


# ═══════════════════════════════════════════════════════════════
# SNAPSHOT PERSISTENCE
# ═══════════════════════════════════════════════════════════════

class TestSnapshotPersistence:

    def test_save(self, tmp_path):
        """O9: Save snapshot to disk."""
        r = MockRegistry()
        r.inc("missions_submitted_total", value=5)
        r.inc("tool_invocations_total", value=20)
        sp = SnapshotPersistence(tmp_path / "snap.json")
        assert sp.save(r)
        assert sp.exists()

    def test_load_restores(self, tmp_path):
        """O10: Load restores counters."""
        r1 = MockRegistry()
        r1.inc("missions_submitted_total", value=10)
        r1.set_gauge("health", 0.95)
        sp = SnapshotPersistence(tmp_path / "snap.json")
        sp.save(r1)

        r2 = MockRegistry()
        assert sp.load(r2)
        assert r2.get_counter_total("missions_submitted_total") == 10

    def test_missing_file(self, tmp_path):
        """O11: Missing file returns False."""
        sp = SnapshotPersistence(tmp_path / "nonexistent.json")
        r = MockRegistry()
        assert not sp.load(r)

    def test_corrupt_file(self, tmp_path):
        """O12: Corrupt file returns False."""
        path = tmp_path / "bad.json"
        path.write_text("{invalid json!!!}", encoding="utf-8")
        sp = SnapshotPersistence(path)
        r = MockRegistry()
        assert not sp.load(r)


# ═══════════════════════════════════════════════════════════════
# ALERT TRIGGERS
# ═══════════════════════════════════════════════════════════════

class TestAlertTriggers:

    def test_low_mission_success(self):
        """O13: Low mission success → alert."""
        r = MockRegistry()
        r.inc("missions_submitted_total", value=10)
        r.inc("missions_completed_total", value=4)
        alerts = AlertEngine().evaluate(r)
        names = [a.name for a in alerts]
        assert "low_mission_success_rate" in names

    def test_high_tool_failure(self):
        """O14: High tool failure → alert."""
        r = MockRegistry()
        r.inc("tool_invocations_total", value=20)
        r.inc("tool_failures_total", value=10)
        alerts = AlertEngine().evaluate(r)
        names = [a.name for a in alerts]
        assert "high_tool_failure_rate" in names

    def test_provider_failure(self):
        """O15: Provider failure → alert."""
        r = MockRegistry()
        r.inc("model_selected_total", value=10)
        r.inc("provider_errors_total", value=5)
        alerts = AlertEngine().evaluate(r)
        names = [a.name for a in alerts]
        assert "high_provider_failure_rate" in names

    def test_retry_storm(self):
        """O16: Retry storm → alert."""
        r = MockRegistry()
        r.inc("retry_attempts_total", value=15)
        alerts = AlertEngine().evaluate(r)
        names = [a.name for a in alerts]
        assert "retry_storm" in names

    def test_circuit_breaker_flapping(self):
        """O17: Circuit breaker flapping → alert."""
        r = MockRegistry()
        r.inc("circuit_breaker_open_total", value=5)
        alerts = AlertEngine().evaluate(r)
        names = [a.name for a in alerts]
        assert "circuit_breaker_flapping" in names

    def test_cost_alert(self):
        """O18: Cost alert triggered."""
        r = MockRegistry()
        r._cost_tracker.total_cost_usd = 10.0
        alerts = AlertEngine().evaluate(r)
        names = [a.name for a in alerts]
        assert "high_cost" in names

    def test_experiment_rejection(self):
        """O19: Experiment rejection → alert."""
        r = MockRegistry()
        r.inc("improvement_experiments_total", value=10)
        r.inc("experiment_rejected_total", value=9)
        alerts = AlertEngine().evaluate(r)
        names = [a.name for a in alerts]
        assert "high_experiment_rejection_rate" in names

    def test_healthy_no_alerts(self):
        """O20: Healthy metrics → no alerts."""
        r = MockRegistry()
        r.inc("missions_submitted_total", value=10)
        r.inc("missions_completed_total", value=9)
        r.inc("tool_invocations_total", value=50)
        r.inc("tool_failures_total", value=2)
        alerts = AlertEngine().evaluate(r)
        assert len(alerts) == 0


# ═══════════════════════════════════════════════════════════════
# TRACE SUMMARY
# ═══════════════════════════════════════════════════════════════

class TestTraceSummary:

    def test_model_events(self):
        """O21: Build from model events."""
        events = [
            {"event": "model_selected", "model_id": "gpt-4o", "timestamp": 1000,
             "latency_ms": 200, "tokens": 500},
            {"event": "llm_response", "model_id": "gpt-4o", "timestamp": 1001,
             "latency_ms": 150, "tokens": 300, "status": "success"},
        ]
        summary = TraceSummaryBuilder().build("m1", events)
        assert summary.primary_model == "gpt-4o"
        assert summary.total_model_calls == 2
        assert summary.total_tokens == 800

    def test_tool_events(self):
        """O22: Build from tool events."""
        events = [
            {"event": "tool_execute", "tool_name": "web_search", "timestamp": 1000,
             "success": True, "duration_ms": 300},
            {"event": "tool_execute", "tool_name": "web_search", "timestamp": 1001,
             "success": False, "duration_ms": 100},
            {"event": "tool_execute", "tool_name": "shell", "timestamp": 1002,
             "success": True, "duration_ms": 50, "status": "success"},
        ]
        summary = TraceSummaryBuilder().build("m2", events)
        assert summary.total_tool_calls == 3
        assert summary.primary_tool == "web_search"
        assert summary.tool_success_rate < 1.0

    def test_mixed_events(self):
        """O23: Build from mixed events."""
        events = [
            {"event": "model_selected", "model_id": "claude-3", "timestamp": 100,
             "latency_ms": 500, "tokens": 1000},
            {"event": "tool_execute", "tool_name": "shell", "timestamp": 101,
             "success": True, "duration_ms": 200, "phase": "execution"},
            {"event": "completion", "timestamp": 102, "status": "success",
             "phase": "finalize", "duration_ms": 50},
        ]
        summary = TraceSummaryBuilder().build("m3", events)
        assert summary.primary_model == "claude-3"
        assert summary.total_tool_calls == 1
        assert "execution" in summary.time_breakdown

    def test_empty_events(self):
        """O24: Empty events → empty summary."""
        summary = TraceSummaryBuilder().build("empty", [])
        assert summary.status == "unknown"
        assert summary.total_model_calls == 0
        assert summary.total_tool_calls == 0

    def test_narrative(self):
        """O25: Narrative includes all sections."""
        events = [
            {"event": "model_selected", "model_id": "gpt-4o", "timestamp": 100,
             "latency_ms": 200, "tokens": 1000},
            {"event": "tool_execute", "tool_name": "shell", "timestamp": 101,
             "success": True, "duration_ms": 100, "phase": "execution"},
            {"event": "done", "timestamp": 102, "status": "success"},
        ]
        summary = TraceSummaryBuilder().build("m4", events)
        text = summary.narrative()
        assert "Mission m4" in text
        assert "Models" in text
        assert "Tools" in text

    def test_failure_analysis(self):
        """O26: Failure causal analysis populated."""
        events = [
            {"event": "tool_execute", "tool_name": "web_search", "timestamp": 100,
             "success": False, "error": "Connection timeout after 30s",
             "component": "tool_executor"},
            {"event": "done", "timestamp": 101, "status": "failed"},
        ]
        summary = TraceSummaryBuilder().build("m5", events)
        assert summary.failure_reason
        assert "timeout" in summary.failure_reason.lower()
        assert summary.recommendation


# ═══════════════════════════════════════════════════════════════
# DIAGNOSTICS
# ═══════════════════════════════════════════════════════════════

class TestDiagnostics:

    def test_report_sections(self):
        """O27: Report has all sections."""
        r = MockRegistry()
        r.inc("missions_submitted_total", value=10)
        r.inc("missions_completed_total", value=8)
        r.inc("tool_invocations_total", value=30)
        r.inc("model_selected_total", value=15)
        diag = OperatorDiagnostics(start_time=time.time() - 3600)
        report = diag.build(r)
        d = report.to_dict()
        assert "health" in d
        assert "missions" in d
        assert "tools" in d
        assert "models" in d

    def test_operator_summary(self):
        """O28: Operator summary readable."""
        r = MockRegistry()
        r.inc("missions_submitted_total", value=5)
        r.inc("missions_completed_total", value=4)
        diag = OperatorDiagnostics()
        report = diag.build(r)
        text = report.operator_summary()
        assert "Diagnostics" in text
        assert "Missions" in text

    def test_admin_summary(self):
        """O29: Admin summary simplified."""
        r = MockRegistry()
        r.inc("missions_submitted_total", value=10)
        r.inc("missions_completed_total", value=9)
        diag = OperatorDiagnostics()
        report = diag.build(r)
        text = report.admin_summary()
        assert "healthy" in text.lower() or "System" in text

    def test_health_degrades(self):
        """O30: Health score degrades with issues."""
        r = MockRegistry()
        r.inc("missions_submitted_total", value=10)
        r.inc("missions_completed_total", value=3)  # Low success
        r.inc("tool_invocations_total", value=20)
        r.inc("tool_failures_total", value=15)  # Low tool reliability
        alerts = [Alert(name="test", severity="critical", current_value=0, threshold=0)]
        diag = OperatorDiagnostics()
        report = diag.build(r, alerts=alerts)
        assert report.health_score < 0.8
        assert report.overall_health in ("degraded", "critical")

    def test_snapshot_roundtrip(self, tmp_path):
        """O31: Snapshot round-trip no regression."""
        r1 = MockRegistry()
        r1.inc("missions_submitted_total", value=42)
        r1.inc("tool_invocations_total", value=100)
        sp = SnapshotPersistence(tmp_path / "rt.json")
        sp.save(r1)

        r2 = MockRegistry()
        sp.load(r2)
        assert r2.get_counter_total("missions_submitted_total") == 42

    def test_alerts_produce_dicts(self):
        """O32: Alerts produce serializable dicts."""
        r = MockRegistry()
        r.inc("missions_submitted_total", value=10)
        r.inc("missions_completed_total", value=2)
        r.inc("retry_attempts_total", value=25)
        alerts = AlertEngine().evaluate(r)
        for alert in alerts:
            d = alert.to_dict()
            assert isinstance(d, dict)
            assert "alert" in d
            assert "severity" in d
            # Should be JSON-serializable
            json.dumps(d)
