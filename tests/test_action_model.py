"""tests/test_action_model.py — Tests for canonical Action model."""
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


class TestCanonicalAction(unittest.TestCase):

    def test_creation(self):
        from core.actions.action_model import CanonicalAction
        a = CanonicalAction(mission_id="m-1", tool_name="web_search")
        self.assertEqual(a.status, "PENDING")
        self.assertEqual(a.tool_name, "web_search")
        self.assertFalse(a.is_terminal)

    def test_lifecycle_happy_path(self):
        from core.actions.action_model import CanonicalAction
        a = CanonicalAction(mission_id="m-1")
        self.assertEqual(a.status, "PENDING")
        a.approve()
        self.assertEqual(a.status, "APPROVED")
        a.start()
        self.assertEqual(a.status, "RUNNING")
        self.assertIsNotNone(a.started_at)
        a.complete(result_text="Done")
        self.assertEqual(a.status, "COMPLETED")
        self.assertTrue(a.is_terminal)
        self.assertIsNotNone(a.duration_seconds)

    def test_lifecycle_approval_required(self):
        from core.actions.action_model import CanonicalAction
        a = CanonicalAction(mission_id="m-1", requires_approval=True)
        a.request_approval()
        self.assertEqual(a.status, "APPROVAL_REQUIRED")
        self.assertTrue(a.is_pending_approval)
        a.approve()
        self.assertEqual(a.status, "APPROVED")

    def test_lifecycle_failure(self):
        from core.actions.action_model import CanonicalAction
        a = CanonicalAction()
        a.start()
        a.fail("timeout")
        self.assertEqual(a.status, "FAILED")
        self.assertTrue(a.is_terminal)
        self.assertEqual(a.error, "timeout")

    def test_lifecycle_cancel(self):
        from core.actions.action_model import CanonicalAction
        a = CanonicalAction()
        a.cancel("user requested")
        self.assertEqual(a.status, "CANCELLED")
        self.assertTrue(a.is_terminal)

    def test_no_transition_from_terminal(self):
        from core.actions.action_model import CanonicalAction
        a = CanonicalAction()
        a.complete()
        a.fail("nope")  # should not change
        self.assertEqual(a.status, "COMPLETED")

    def test_to_dict(self):
        from core.actions.action_model import CanonicalAction
        a = CanonicalAction(mission_id="m-1", tool_name="shell_execute")
        d = a.to_dict()
        self.assertIn("action_id", d)
        self.assertIn("status", d)
        self.assertIn("is_terminal", d)
        self.assertIn("duration_seconds", d)


class TestStatusMapping(unittest.TestCase):

    def test_legacy_action_statuses(self):
        from core.actions.action_model import canonicalize_status
        self.assertEqual(canonicalize_status("PENDING"), "PENDING")
        self.assertEqual(canonicalize_status("APPROVED"), "APPROVED")
        self.assertEqual(canonicalize_status("REJECTED"), "CANCELLED")
        self.assertEqual(canonicalize_status("EXECUTED"), "COMPLETED")
        self.assertEqual(canonicalize_status("FAILED"), "FAILED")

    def test_legacy_task_statuses(self):
        from core.actions.action_model import canonicalize_status
        self.assertEqual(canonicalize_status("pending"), "PENDING")
        self.assertEqual(canonicalize_status("running"), "RUNNING")
        self.assertEqual(canonicalize_status("done"), "COMPLETED")
        self.assertEqual(canonicalize_status("failed"), "FAILED")
        self.assertEqual(canonicalize_status("cancelled"), "CANCELLED")

    def test_unknown_defaults_pending(self):
        from core.actions.action_model import canonicalize_status
        self.assertEqual(canonicalize_status("INVALID"), "PENDING")


class TestFromLegacy(unittest.TestCase):

    def test_from_legacy_action(self):
        from core.actions.action_model import CanonicalAction
        class FakeAction:
            id = "act-123"
            mission_id = "m-1"
            status = "EXECUTED"
            description = "Search web"
            target = "web_search"
            risk = "LOW"
            result = "Found results"
            created_at = time.time() - 10
            approved_at = time.time() - 5
            executed_at = time.time()
        ca = CanonicalAction.from_legacy_action(FakeAction())
        self.assertEqual(ca.action_id, "act-123")
        self.assertEqual(ca.status, "COMPLETED")
        self.assertEqual(ca.tool_name, "web_search")

    def test_from_legacy_task(self):
        from core.actions.action_model import CanonicalAction
        class FakeTask:
            id = "task-456"
            mission_id = "m-2"
            state = "running"
            name = "background job"
            payload = {"key": "val"}
            result = None
            error = ""
            created_at = time.time()
        ca = CanonicalAction.from_legacy_task(FakeTask())
        self.assertEqual(ca.action_id, "task-456")
        self.assertEqual(ca.status, "RUNNING")
        self.assertEqual(ca.description, "background job")


class TestEventEmission(unittest.TestCase):

    def test_transitions_emit_events(self):
        from core.actions.action_model import CanonicalAction
        from core.observability.event_envelope import EventCollector, set_trace, clear_trace
        set_trace("tr-test-action", "m-test")
        collector = EventCollector()

        # Monkey-patch the global collector temporarily
        import core.observability.event_envelope as obs
        old = obs._collector
        obs._collector = collector

        a = CanonicalAction(trace_id="tr-test-action", mission_id="m-test")
        a.approve()
        a.start()
        a.complete("done")

        events = collector.get_trace("tr-test-action")
        event_names = [e["payload"]["event"] for e in events]
        self.assertIn("action_approved", event_names)
        self.assertIn("action_started", event_names)
        self.assertIn("action_completed", event_names)

        obs._collector = old
        clear_trace()


if __name__ == "__main__":
    unittest.main()
