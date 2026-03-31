"""tests/test_capabilities.py — Tests for capability registry."""
import os
import sys
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

# Stubs
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


class TestCapabilitySchema(unittest.TestCase):

    def test_capability_creation(self):
        from core.capabilities.schema import Capability
        cap = Capability(name="web_search", risk_level="LOW", timeout_seconds=15)
        self.assertEqual(cap.name, "web_search")
        self.assertEqual(cap.risk_level, "LOW")
        self.assertFalse(cap.requires_approval)

    def test_capability_frozen(self):
        from core.capabilities.schema import Capability
        cap = Capability(name="test")
        with self.assertRaises(AttributeError):
            cap.name = "changed"

    def test_allows_agent_unrestricted(self):
        from core.capabilities.schema import Capability
        cap = Capability(name="test", allowed_agents=())
        self.assertTrue(cap.allows_agent("any-agent"))

    def test_allows_agent_restricted(self):
        from core.capabilities.schema import Capability
        cap = Capability(name="test", allowed_agents=("scout", "forge"))
        self.assertTrue(cap.allows_agent("scout"))
        self.assertFalse(cap.allows_agent("hacker"))

    def test_to_dict(self):
        from core.capabilities.schema import Capability
        cap = Capability(name="shell_execute", risk_level="HIGH", requires_approval=True)
        d = cap.to_dict()
        self.assertEqual(d["name"], "shell_execute")
        self.assertEqual(d["risk_level"], "HIGH")
        self.assertTrue(d["requires_approval"])
        self.assertIsInstance(d["allowed_agents"], list)


class TestCapabilityRegistry(unittest.TestCase):

    def test_core_tools_registered(self):
        from core.capabilities.registry import CapabilityRegistry
        reg = CapabilityRegistry()
        self.assertTrue(reg.is_registered("web_search"))
        self.assertTrue(reg.is_registered("shell_execute"))
        self.assertTrue(reg.is_registered("file_write"))
        self.assertTrue(reg.is_registered("memory_write"))
        self.assertTrue(reg.is_registered("api_call"))

    def test_unregistered_tool_rejected(self):
        from core.capabilities.registry import CapabilityRegistry
        reg = CapabilityRegistry()
        perm = reg.check_permission("evil_hack")
        self.assertFalse(perm["allowed"])
        self.assertIn("unregistered", perm["reason"])

    def test_low_risk_allowed(self):
        from core.capabilities.registry import CapabilityRegistry
        reg = CapabilityRegistry()
        perm = reg.check_permission("web_search")
        self.assertTrue(perm["allowed"])
        self.assertFalse(perm["requires_approval"])

    def test_high_risk_requires_approval(self):
        from core.capabilities.registry import CapabilityRegistry
        reg = CapabilityRegistry()
        perm = reg.check_permission("shell_execute")
        self.assertTrue(perm["allowed"])
        self.assertTrue(perm["requires_approval"])

    def test_stats(self):
        from core.capabilities.registry import CapabilityRegistry
        reg = CapabilityRegistry()
        stats = reg.stats()
        self.assertGreater(stats["total"], 0)
        self.assertIn("LOW", stats["by_risk"])
        self.assertIn("MEDIUM", stats["by_risk"])
        self.assertIn("HIGH", stats["by_risk"])
        self.assertGreater(stats["requiring_approval"], 0)

    def test_list_by_risk(self):
        from core.capabilities.registry import CapabilityRegistry
        reg = CapabilityRegistry()
        high = reg.list_by_risk("HIGH")
        self.assertTrue(all(c["risk_level"] == "HIGH" for c in high))
        names = [c["name"] for c in high]
        self.assertIn("shell_execute", names)

    def test_register_custom(self):
        from core.capabilities.schema import Capability
        from core.capabilities.registry import CapabilityRegistry
        reg = CapabilityRegistry()
        reg.register(Capability(name="custom_tool", risk_level="LOW"))
        self.assertTrue(reg.is_registered("custom_tool"))

    def test_singleton(self):
        from core.capabilities.registry import get_capability_registry
        r1 = get_capability_registry()
        r2 = get_capability_registry()
        self.assertIs(r1, r2)

    def test_agent_restriction(self):
        from core.capabilities.schema import Capability
        from core.capabilities.registry import CapabilityRegistry
        reg = CapabilityRegistry()
        reg.register(Capability(name="restricted", allowed_agents=("scout",)))
        perm_ok = reg.check_permission("restricted", agent_name="scout")
        perm_bad = reg.check_permission("restricted", agent_name="hacker")
        self.assertTrue(perm_ok["allowed"])
        self.assertFalse(perm_bad["allowed"])


if __name__ == "__main__":
    unittest.main()
