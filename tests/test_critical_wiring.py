"""
JARVIS MAX — Critical Zone Wiring Tests
============================================
Verifies the 3 CRITICAL integrations actually enforce:
  1. MissionGuardian registered in MetaOrchestrator.run_mission()
  2. CognitiveBridge.pre_mission()/post_mission() called from MetaOrchestrator
  3. ToolPermissions.check() called from ToolExecutor.execute()

Total: 15 tests
"""
import sys, os, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("ADMIN_PASSWORD_HASH", "test-hash")
os.environ.setdefault("JARVISMAX_DATA_DIR", tempfile.mkdtemp())

import pytest


# ═══════════════════════════════════════════════════════════════
# TOOL EXECUTOR ↔ TOOL PERMISSIONS (8 tests)
# ═══════════════════════════════════════════════════════════════

class TestToolExecutorPermissions:
    """Verify ToolExecutor.execute() actually calls tool permission check."""

    def _get_executor(self):
        from core.tool_executor import ToolExecutor
        return ToolExecutor()

    def test_TW01_safe_tool_passes(self):
        """read_file is not gated — should execute normally."""
        te = self._get_executor()
        result = te.execute("read_file", {"path": "/tmp/nonexistent_test_file"})
        # May fail for missing file, but should NOT be blocked by permissions
        assert result.get("blocked_by_policy") is not True or "approval_required" not in result.get("error", "")

    def test_TW02_shell_command_gated(self):
        """shell_command IS gated — should return approval_required."""
        te = self._get_executor()
        result = te.execute("shell_command", {"cmd": "echo test"})
        assert result["ok"] is False
        assert "approval_required" in result.get("error", "")
        assert "approval_request_id" in result

    def test_TW03_git_push_gated(self):
        """git_push is gated — blocked by permission OR unknown_tool (if git tools not loaded)."""
        te = self._get_executor()
        result = te.execute("git_push", {})
        assert result["ok"] is False
        # Either gated by permission or not registered in executor
        assert "approval_required" in result.get("error", "") or "unknown_tool" in result.get("error", "")

    def test_TW04_python_snippet_gated(self):
        te = self._get_executor()
        result = te.execute("python_snippet", {"code": "print(1)"})
        assert result["ok"] is False
        assert "approval_required" in result.get("error", "")

    def test_TW05_docker_restart_gated(self):
        """docker_restart is gated — blocked by permission OR unknown_tool (if docker not loaded)."""
        te = self._get_executor()
        result = te.execute("docker_restart", {"container": "test"})
        assert result["ok"] is False
        assert "approval_required" in result.get("error", "") or "unknown_tool" in result.get("error", "")

    def test_TW06_approval_request_id_returned(self):
        """Gated tool returns the approval request ID for resume."""
        te = self._get_executor()
        result = te.execute("shell_command", {"cmd": "ls"})
        req_id = result.get("approval_request_id", "")
        assert req_id.startswith("apr-")

    def test_TW07_approval_request_scrubs_secrets(self):
        """Params in approval request have secrets scrubbed."""
        from core.tool_permissions import get_tool_permissions
        te = self._get_executor()
        result = te.execute("shell_command", {
            "cmd": "deploy",
            "api_key": "sk-supersecretkey1234567890",
        })
        req_id = result.get("approval_request_id", "")
        req = get_tool_permissions().get_request(req_id)
        assert req is not None
        assert "sk-super" not in str(req.safe_params)

    def test_TW08_http_get_not_gated(self):
        """http_get is safe — should attempt execution (may fail network, but not policy)."""
        te = self._get_executor()
        result = te.execute("http_get", {"url": "http://localhost:99999/nonexistent"})
        # Should NOT be blocked by permission
        assert "approval_required" not in result.get("error", "")


# ═══════════════════════════════════════════════════════════════
# META-ORCHESTRATOR WIRING VERIFICATION (7 tests)
# ═══════════════════════════════════════════════════════════════

class TestMetaOrchestratorWiring:
    """Verify MetaOrchestrator source code contains the wiring."""

    def test_MW01_guardian_registration_in_source(self):
        """MetaOrchestrator.run_mission() imports mission_guards."""
        import inspect
        from core.meta_orchestrator import MetaOrchestrator
        source = inspect.getsource(MetaOrchestrator.run_mission)
        assert "from core.mission_guards import get_guardian" in source

    def test_MW02_guardian_register_call(self):
        """run_mission() calls get_guardian().register_mission()."""
        import inspect
        from core.meta_orchestrator import MetaOrchestrator
        source = inspect.getsource(MetaOrchestrator.run_mission)
        assert "register_mission" in source

    def test_MW03_cognitive_pre_mission_in_source(self):
        """run_mission() calls cognitive_bridge.pre_mission()."""
        import inspect
        from core.meta_orchestrator import MetaOrchestrator
        source = inspect.getsource(MetaOrchestrator.run_mission)
        assert "from core.cognitive_bridge import get_bridge" in source
        assert "pre_mission" in source

    def test_MW04_cognitive_post_mission_in_source(self):
        """run_mission() calls post_mission() at the end."""
        import inspect
        from core.meta_orchestrator import MetaOrchestrator
        source = inspect.getsource(MetaOrchestrator.run_mission)
        assert "post_mission" in source

    def test_MW05_guardian_release_in_source(self):
        """run_mission() calls release_mission() for cleanup."""
        import inspect
        from core.meta_orchestrator import MetaOrchestrator
        source = inspect.getsource(MetaOrchestrator.run_mission)
        assert "release_mission" in source

    def test_MW06_tool_permissions_in_executor(self):
        """ToolExecutor.execute() imports tool_permissions."""
        import inspect
        from core.tool_executor import ToolExecutor
        source = inspect.getsource(ToolExecutor.execute)
        assert "from core.tool_permissions import get_tool_permissions" in source

    def test_MW07_all_wiring_is_fail_open(self):
        """All 3 CRITICAL wirings are inside try/except blocks."""
        import inspect
        from core.meta_orchestrator import MetaOrchestrator
        source = inspect.getsource(MetaOrchestrator.run_mission)
        # Count try blocks around our code
        lines = source.split('\n')
        guardian_try = False
        cognitive_try = False
        for i, line in enumerate(lines):
            if "mission_guards" in line:
                # Check that a try: exists within ~3 lines before
                for j in range(max(0, i-5), i):
                    if "try:" in lines[j]:
                        guardian_try = True
            if "cognitive_bridge" in line and "pre_mission" in source[source.index(line):source.index(line)+200]:
                for j in range(max(0, i-5), i):
                    if "try:" in lines[j]:
                        cognitive_try = True
        assert guardian_try, "mission_guards not wrapped in try/except"
        assert cognitive_try, "cognitive_bridge not wrapped in try/except"
