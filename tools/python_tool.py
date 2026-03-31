"""
PythonTool — execute Python code via ExecutionRuntime.
"""
from __future__ import annotations

from tools.base import BaseTool, ToolRisk


class PythonTool(BaseTool):
    name = "python_tool"
    risk = ToolRisk.SUPERVISED

    def execute(self, code: str, timeout: int = 30) -> dict:
        """Run Python code. Delegates to ExecutionRuntime."""
        try:
            from executor.execution_runtime import get_runtime
            result = get_runtime().run_python(code, timeout=timeout)
            return {
                "success": result.success,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
                "duration_ms": result.duration_ms,
                "error": result.error,
            }
        except Exception as e:
            return {"success": False, "stdout": "", "stderr": "", "error": str(e)}
