"""tests/test_result_envelope.py — Tests for FinalOutput envelope and aggregator."""
import os
import sys
import time
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

# Stub structlog
import types
if 'structlog' not in sys.modules:
    _sl = types.ModuleType('structlog')
    class _ML:
        def info(self, *a, **k): pass
        def debug(self, *a, **k): pass
        def warning(self, *a, **k): pass
        def error(self, *a, **k): pass
        def bind(self, **k): return self
    _sl.get_logger = lambda *a, **k: _ML()
    sys.modules['structlog'] = _sl


class TestFinalOutputSchema(unittest.TestCase):
    """FinalOutput schema is deterministic and complete."""

    def test_basic_construction(self):
        from core.schemas.final_output import FinalOutput, AgentOutput, OutputMetrics
        fo = FinalOutput(
            mission_id="test-001",
            status="COMPLETED",
            summary="Test mission completed",
            agent_outputs=[
                AgentOutput(agent_name="scout", status="SUCCESS", output_text="Found data"),
            ],
            metrics=OutputMetrics(duration_seconds=5.2),
        )
        self.assertEqual(fo.mission_id, "test-001")
        self.assertEqual(fo.status, "COMPLETED")
        self.assertEqual(len(fo.agent_outputs), 1)
        self.assertEqual(fo.agent_outputs[0].agent_name, "scout")

    def test_to_dict_complete(self):
        from core.schemas.final_output import FinalOutput, AgentOutput
        fo = FinalOutput(
            mission_id="test-002",
            status="FAILED",
            summary="Agent failed",
            agent_outputs=[
                AgentOutput(agent_name="scout", status="ERROR", output_text="Error occurred"),
            ],
        )
        d = fo.to_dict()
        self.assertEqual(d["mission_id"], "test-002")
        self.assertEqual(d["status"], "FAILED")
        self.assertEqual(d["summary"], "Agent failed")
        self.assertIsInstance(d["agent_outputs"], list)
        self.assertEqual(len(d["agent_outputs"]), 1)
        self.assertEqual(d["agent_outputs"][0]["agent_name"], "scout")
        self.assertEqual(d["agent_outputs"][0]["status"], "ERROR")
        self.assertIsInstance(d["decision_trace"], list)
        self.assertIsInstance(d["metrics"], dict)

    def test_from_mission_legacy_status(self):
        from core.schemas.final_output import FinalOutput
        fo = FinalOutput.from_mission(
            mission_id="test-003",
            mission_status="DONE",
            summary="Legacy mission",
            agent_outputs_raw={"scout": "Found results"},
            decision_trace_raw={"mission_type": "business", "complexity": "medium"},
            start_time=time.time() - 10,
        )
        self.assertEqual(fo.status, "COMPLETED")  # DONE → COMPLETED
        self.assertEqual(len(fo.agent_outputs), 1)
        self.assertEqual(fo.agent_outputs[0].agent_name, "scout")
        self.assertTrue(len(fo.decision_trace) >= 2)

    def test_from_mission_blocked(self):
        from core.schemas.final_output import FinalOutput
        fo = FinalOutput.from_mission(
            mission_id="test-004",
            mission_status="BLOCKED",
            summary="Blocked mission",
            agent_outputs_raw={},
            decision_trace_raw={},
        )
        self.assertEqual(fo.status, "FAILED")  # BLOCKED → FAILED

    def test_from_mission_rejected(self):
        from core.schemas.final_output import FinalOutput
        fo = FinalOutput.from_mission(
            mission_id="test-005",
            mission_status="REJECTED",
            summary="Rejected mission",
            agent_outputs_raw={},
            decision_trace_raw={},
        )
        self.assertEqual(fo.status, "CANCELLED")  # REJECTED → CANCELLED

    def test_agent_error_structure(self):
        from core.schemas.final_output import AgentOutput, AgentError
        ao = AgentOutput(
            agent_name="forge",
            status="ERROR",
            error=AgentError(type="timeout", message="Agent timed out", recoverable=True),
        )
        d = ao.to_dict()
        self.assertEqual(d["error"]["type"], "timeout")
        self.assertTrue(d["error"]["recoverable"])

    def test_empty_mission(self):
        from core.schemas.final_output import FinalOutput
        fo = FinalOutput(mission_id="empty")
        d = fo.to_dict()
        self.assertEqual(d["agent_outputs"], [])
        self.assertEqual(d["decision_trace"], [])
        self.assertEqual(d["status"], "COMPLETED")

    def test_status_only_allows_canonical(self):
        from core.schemas.final_output import FinalOutput
        for status in ("COMPLETED", "FAILED", "CANCELLED"):
            fo = FinalOutput(mission_id="x", status=status)
            self.assertEqual(fo.status, status)


class TestResultAggregatorUnit(unittest.TestCase):
    """Result aggregator builds correct envelopes."""

    def test_envelope_has_required_fields(self):
        from core.schemas.final_output import FinalOutput
        fo = FinalOutput(mission_id="test")
        d = fo.to_dict()
        required = {"mission_id", "status", "summary", "agent_outputs",
                     "decision_trace", "metrics"}
        self.assertTrue(required.issubset(d.keys()),
                        f"Missing fields: {required - set(d.keys())}")

    def test_metrics_omits_none(self):
        from core.schemas.final_output import OutputMetrics
        m = OutputMetrics()
        self.assertEqual(m.to_dict(), {})

    def test_metrics_includes_values(self):
        from core.schemas.final_output import OutputMetrics
        m = OutputMetrics(duration_seconds=3.5, token_usage=1200)
        d = m.to_dict()
        self.assertEqual(d["duration_seconds"], 3.5)
        self.assertEqual(d["token_usage"], 1200)
        self.assertNotIn("cost_estimate", d)


if __name__ == "__main__":
    unittest.main()
