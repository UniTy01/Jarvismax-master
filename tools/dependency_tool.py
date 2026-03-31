"""
DependencyTool — check and install Python packages.
Delegates to ExecutionRuntime.
"""
from __future__ import annotations

import json

from tools.base import BaseTool, ToolRisk


class DependencyTool(BaseTool):
    name = "dependency_tool"
    risk = ToolRisk.SUPERVISED

    def check(self, package: str) -> dict:
        """Check if package is importable."""
        try:
            from executor.execution_runtime import get_runtime
            available = get_runtime().check_dependency(package)
            return {"success": True, "available": available, "package": package}
        except Exception as e:
            return {"success": False, "error": str(e), "available": False}

    def install(self, package: str) -> dict:
        """Install package via pip."""
        try:
            from executor.execution_runtime import get_runtime
            result = get_runtime().ensure_dependency(package)
            return {
                "success": result.success,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "error": result.error,
                "duration_ms": result.duration_ms,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_installed(self) -> dict:
        """List all installed packages via pip list --format=json."""
        try:
            import subprocess
            import sys
            result = subprocess.run(
                [sys.executable, "-m", "pip", "list", "--format=json"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                packages = json.loads(result.stdout)
                return {"success": True, "packages": packages}
            return {"success": False, "error": result.stderr[:500]}
        except Exception as e:
            return {"success": False, "error": str(e)}
