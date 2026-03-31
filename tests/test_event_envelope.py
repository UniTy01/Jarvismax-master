"""tests/test_event_envelope.py — Tests for observability event envelope."""
import os
import sys
import time
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

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


class TestEventEnvelope(unittest.TestCase):

    def test_envelope_creation(self):
        from core.observability.event_envelope import EventEnvelope
        e = EventEnvelope(
            trace_id="tr-abc123",
            mission_id="m-001",
            component="tool",
            event_type="tool_call",
            payload={"tool": "web_search"},
        )
        self.assertEqual(e.trace_id, "tr-abc123")
        self.assertEqual(e.component, "tool")
        self.assertEqual(e.event_type, "tool_call")

    def test_to_dict(self):
        from core.observability.event_envelope import EventEnvelope
        e = EventEnvelope(trace_id="tr-x", mission_id="m-1", component="agent", event_type="decision")
        d = e.to_dict()
        self.assertIn("trace_id", d)
        self.assertIn("timestamp", d)
        self.assertIn("component", d)
        self.assertIn("payload", d)


class TestTraceId(unittest.TestCase):

    def test_generate_unique(self):
        from core.observability.event_envelope import generate_trace_id
        ids = {generate_trace_id() for _ in range(100)}
        self.assertEqual(len(ids), 100)

    def test_format(self):
        from core.observability.event_envelope import generate_trace_id
        tid = generate_trace_id()
        self.assertTrue(tid.startswith("tr-"))
        self.assertEqual(len(tid), 15)  # "tr-" + 12 hex chars


class TestTraceContext(unittest.TestCase):

    def test_set_and_get(self):
        from core.observability.event_envelope import set_trace, get_trace_id, get_mission_id, clear_trace
        set_trace("tr-test123", "m-test")
        self.assertEqual(get_trace_id(), "tr-test123")
        self.assertEqual(get_mission_id(), "m-test")
        clear_trace()
        self.assertIsNone(get_trace_id())

    def test_clear(self):
        from core.observability.event_envelope import set_trace, clear_trace, get_trace_id
        set_trace("tr-xxx", "m-xxx")
        clear_trace()
        self.assertIsNone(get_trace_id())


class TestEventCollector(unittest.TestCase):

    def test_emit_and_retrieve(self):
        from core.observability.event_envelope import EventCollector, EventEnvelope
        c = EventCollector()
        c.emit(EventEnvelope(trace_id="tr-1", mission_id="m-1", component="tool", event_type="tool_call"))
        c.emit(EventEnvelope(trace_id="tr-1", mission_id="m-1", component="tool", event_type="tool_result"))
        events = c.get_trace("tr-1")
        self.assertEqual(len(events), 2)

    def test_get_mission_trace(self):
        from core.observability.event_envelope import EventCollector, EventEnvelope
        c = EventCollector()
        c.emit(EventEnvelope(trace_id="tr-a", mission_id="m-X", component="agent", event_type="decision"))
        c.emit(EventEnvelope(trace_id="tr-b", mission_id="m-X", component="tool", event_type="tool_call"))
        c.emit(EventEnvelope(trace_id="tr-c", mission_id="m-Y", component="tool", event_type="tool_call"))
        events = c.get_mission_trace("m-X")
        self.assertEqual(len(events), 2)

    def test_emit_quick_no_context(self):
        from core.observability.event_envelope import EventCollector, clear_trace
        clear_trace()
        c = EventCollector()
        c.emit_quick("tool", "tool_call", {"tool": "test"})
        # Should be no-op (no trace set)
        self.assertEqual(c.stats()["total_events"], 0)

    def test_emit_quick_with_context(self):
        from core.observability.event_envelope import EventCollector, set_trace, clear_trace
        set_trace("tr-ctx", "m-ctx")
        c = EventCollector()
        c.emit_quick("tool", "tool_call", {"tool": "test"})
        events = c.get_trace("tr-ctx")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["payload"]["tool"], "test")
        clear_trace()

    def test_max_events(self):
        from core.observability.event_envelope import EventCollector, EventEnvelope
        c = EventCollector(max_events=5)
        for i in range(10):
            c.emit(EventEnvelope(trace_id="tr-max", mission_id="m", component="tool", event_type="tool_call"))
        self.assertEqual(len(c.get_trace("tr-max")), 5)

    def test_cleanup(self):
        from core.observability.event_envelope import EventCollector, EventEnvelope
        c = EventCollector()
        e = EventEnvelope(trace_id="tr-old", mission_id="m", component="tool", event_type="tool_call")
        e.timestamp = time.time() - 7200  # 2 hours ago
        c.emit(e)
        removed = c.cleanup(max_age_seconds=3600)
        self.assertEqual(removed, 1)
        self.assertEqual(len(c.get_trace("tr-old")), 0)

    def test_stats(self):
        from core.observability.event_envelope import EventCollector, EventEnvelope
        c = EventCollector()
        c.emit(EventEnvelope(trace_id="tr-s1", mission_id="m", component="tool", event_type="tool_call"))
        c.emit(EventEnvelope(trace_id="tr-s2", mission_id="m", component="agent", event_type="decision"))
        stats = c.stats()
        self.assertEqual(stats["active_traces"], 2)
        self.assertEqual(stats["total_events"], 2)


class TestFinalOutputTraceId(unittest.TestCase):

    def test_trace_id_in_envelope(self):
        from core.schemas.final_output import FinalOutput
        fo = FinalOutput(mission_id="m-1", trace_id="tr-abc")
        d = fo.to_dict()
        self.assertEqual(d["trace_id"], "tr-abc")

    def test_trace_id_defaults_empty(self):
        from core.schemas.final_output import FinalOutput
        fo = FinalOutput(mission_id="m-2")
        self.assertEqual(fo.trace_id, "")


if __name__ == "__main__":
    unittest.main()
