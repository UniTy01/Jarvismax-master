"""
Tests pour core/contracts.py — Schémas Pydantic v2 inter-agents.
"""
import asyncio
import time
import pytest
from pydantic import ValidationError

from core.contracts import (
    TaskContract, AgentResult, AgentMessage, ErrorReport,
    HealthReport, ComponentHealth, HealthStatus, ErrorSeverity,
    RootCauseType, TaskState, AdvisoryReport,
    AdvisoryDecision, ExecutionResultSchema, MissionLifecycle,
)
# contracts.py has a Pydantic RetryConfig for serialization only.


class TestTaskContract:
    def test_defaults(self):
        tc = TaskContract(agent="scout-research", task="Analyser le code")
        assert tc.agent == "scout-research"
        assert tc.priority == 2
        assert tc.timeout_s == 120
        assert tc.task_id  # auto-generated
        assert tc.correlation_id  # auto-generated

    def test_custom_fields(self):
        from core.contracts import RetryConfig as PydanticRetryConfig
        rc = PydanticRetryConfig(max_attempts=5, base_delay_s=1.0)
        tc = TaskContract(
            agent="forge-builder",
            task="Générer le code",
            priority=1,
            timeout_s=180,
            retry_config=rc,
            mission_id="mission-abc",
        )
        assert tc.priority == 1
        assert tc.retry_config.max_attempts == 5

    def test_priority_range(self):
        with pytest.raises(ValidationError):
            TaskContract(agent="a", task="b", priority=10)  # max=4



class TestAgentResult:
    def test_success(self):
        r = AgentResult(agent="scout-research", success=True, content="## Synthèse\n...")
        assert r.success
        assert not r.is_empty
        assert "scout-research" in r.short_summary()

    def test_failure(self):
        r = AgentResult(agent="scout-research", success=False, error="Timeout")
        assert not r.success
        assert r.is_empty

    def test_duration(self):
        r = AgentResult(agent="a", success=True, content="ok", duration_ms=1500)
        assert "1500ms" in r.short_summary()


class TestErrorReport:
    def test_from_exception(self):
        try:
            raise asyncio.TimeoutError("async timeout")
        except Exception as e:
            report = ErrorReport.from_exception(
                e, agent="lens-reviewer", task_id="t1", retry_count=2
            )
        assert report.agent == "lens-reviewer"
        assert report.retry_count == 2
        assert report.is_retryable

    def test_from_value_error(self):
        import asyncio
        try:
            raise ValueError("bad input")
        except Exception as e:
            report = ErrorReport.from_exception(e, agent="forge-builder")
        # ValueError non-retryable
        assert not report.is_retryable

    def test_severity_enum(self):
        r = ErrorReport(
            agent="a", error_type="TimeoutError", message="timeout",
            severity=ErrorSeverity.HIGH,
        )
        assert r.severity == "high"


class TestHealthReport:
    def test_healthy(self):
        comp = ComponentHealth(name="llm", status=HealthStatus.OK, latency_ms=800)
        report = HealthReport(
            status=HealthStatus.OK,
            components={"llm": comp},
        )
        assert report.is_healthy()
        assert "ok" in report.summary()

    def test_degraded(self):
        comp = ComponentHealth(name="llm", status=HealthStatus.DEGRADED, error="Slow")
        report = HealthReport(
            status=HealthStatus.DEGRADED,
            components={"llm": comp},
        )
        assert not report.is_healthy()

    def test_summary_counts(self):
        r = HealthReport(
            status=HealthStatus.OK,
            components={
                "llm":    ComponentHealth(name="llm",    status=HealthStatus.OK),
                "memory": ComponentHealth(name="memory", status=HealthStatus.OK),
                "exec":   ComponentHealth(name="exec",   status=HealthStatus.DEGRADED),
            }
        )
        assert "2/3" in r.summary()


class TestMissionLifecycle:
    def test_transitions(self):
        lc = MissionLifecycle(mission_id="m1")
        assert lc.current_state == "intake"
        lc.transition("planning", reason="started", agent="atlas-director")
        lc.transition("dispatch")
        assert lc.current_state == "dispatch"
        assert len(lc.transitions) == 2
        assert "planning" in lc.history_summary()

    def test_duration(self):
        lc = MissionLifecycle(mission_id="m2")
        time.sleep(0.01)
        assert lc.duration_s() > 0


class TestAdvisoryReport:
    def test_go(self):
        r = AdvisoryReport(decision=AdvisoryDecision.GO, final_score=8.5)
        assert r.is_go()
        assert r.blocking_count() == 0

    def test_no_go(self):
        from core.contracts import BlockingIssue
        r = AdvisoryReport(
            decision=AdvisoryDecision.NO_GO,
            final_score=2.0,
            blocking_issues=[
                BlockingIssue(type="security", description="Risque critique", severity="high")
            ]
        )
        assert not r.is_go()
        assert r.blocking_count() == 1


class TestExecutionResultSchema:
    def test_summary_format_success(self):
        r = ExecutionResultSchema(
            success=True, action_type="write_file", target="workspace/test.py",
            output="Fichier créé avec succès",
        )
        fmt = r.summary_format()
        assert "OK" in fmt
        assert "write_file" in fmt

    def test_summary_format_error(self):
        r = ExecutionResultSchema(
            success=False, action_type="run_command", target="ls -la",
            error="Commande hors whitelist"
        )
        fmt = r.summary_format()
        assert "ERREUR" in fmt
        assert "whitelist" in fmt

    def test_whitelist_detection(self):
        r = ExecutionResultSchema(
            success=False, action_type="run_command", target="rm -rf /",
            error="Refusé par whitelist"
        )
        assert r.is_rejected_by_whitelist()
