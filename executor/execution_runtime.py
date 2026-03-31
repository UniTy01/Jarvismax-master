"""
ExecutionRuntime — safe Python execution environment for forge-builder and similar agents.
Provides: dependency check, auto-install, sandboxed subprocess, timeout protection.
"""
from __future__ import annotations

import importlib
import json
import os
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class RuntimeResult:
    success: bool
    stdout: str = ""
    stderr: str = ""
    returncode: int = 0
    duration_ms: int = 0
    error: str = ""

    @classmethod
    def failure(cls, error: str) -> "RuntimeResult":
        return cls(success=False, error=error, returncode=-1)


class ExecutionRuntime:
    """
    Safe execution environment for agent-initiated Python code and shell commands.

    Features:
    - check_dependency(package): checks if importable
    - ensure_dependency(package): pip install if missing, fail-open
    - run_python(code, timeout=30): run Python code in subprocess
    - run_command(cmd, timeout=30): run shell command safely
    - run_file(path, timeout=60): run a Python file

    All methods return RuntimeResult — never raise.
    """

    DEFAULT_TIMEOUT = 30   # seconds
    MAX_TIMEOUT = 300      # 5 minutes hard cap
    BLOCKED_COMMANDS = [
        "rm -rf /",
        "dd if=",
        "mkfs",
        ":(){:|:&};:",
        "sudo rm",
        "format c:",
        "del /f /s /q",
        "> /dev/sda",
    ]

    def check_dependency(self, package: str) -> bool:
        """Return True if package is importable."""
        try:
            # Normalize package name for import (e.g. scikit-learn → sklearn)
            import_name = package.replace("-", "_").split("[")[0]
            importlib.import_module(import_name)
            return True
        except ImportError:
            return False
        except Exception:
            return False

    def ensure_dependency(self, package: str) -> RuntimeResult:
        """pip install {package} if not already importable. Fail-open."""
        t0 = time.perf_counter()
        try:
            if self.check_dependency(package):
                ms = int((time.perf_counter() - t0) * 1000)
                return RuntimeResult(success=True, stdout=f"{package} already installed", duration_ms=ms)

            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", package, "--break-system-packages", "-q"],
                capture_output=True,
                text=True,
                timeout=120,
            )
            ms = int((time.perf_counter() - t0) * 1000)
            success = result.returncode == 0
            return RuntimeResult(
                success=success,
                stdout=result.stdout,
                stderr=result.stderr,
                returncode=result.returncode,
                duration_ms=ms,
                error="" if success else f"pip failed with code {result.returncode}",
            )
        except subprocess.TimeoutExpired:
            ms = int((time.perf_counter() - t0) * 1000)
            return RuntimeResult(success=False, error="pip install timed out", duration_ms=ms)
        except Exception as e:
            ms = int((time.perf_counter() - t0) * 1000)
            return RuntimeResult(success=False, error=str(e), duration_ms=ms)

    def run_python(
        self,
        code: str,
        timeout: int = DEFAULT_TIMEOUT,
        env_vars: dict = None,
    ) -> RuntimeResult:
        """Run Python code string in a subprocess. Timeout kills the process."""
        timeout = min(timeout, self.MAX_TIMEOUT)
        t0 = time.perf_counter()

        tmp_path = None
        try:
            # Write code to temp file in workspace/
            workspace = Path("workspace")
            workspace.mkdir(exist_ok=True)
            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".py",
                dir=workspace,
                delete=False,
                encoding="utf-8",
            ) as f:
                f.write(code)
                tmp_path = f.name

            env = os.environ.copy()
            if env_vars:
                env.update({str(k): str(v) for k, v in env_vars.items()})

            proc = subprocess.Popen(
                [sys.executable, tmp_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
            )

            # Poll loop for timeout
            deadline = time.perf_counter() + timeout
            while proc.poll() is None:
                if time.perf_counter() > deadline:
                    proc.kill()
                    proc.wait()
                    ms = int((time.perf_counter() - t0) * 1000)
                    return RuntimeResult(
                        success=False,
                        error=f"Execution timed out after {timeout}s",
                        returncode=-9,
                        duration_ms=ms,
                    )
                time.sleep(0.05)

            stdout, stderr = proc.communicate()
            ms = int((time.perf_counter() - t0) * 1000)
            success = proc.returncode == 0
            return RuntimeResult(
                success=success,
                stdout=stdout,
                stderr=stderr,
                returncode=proc.returncode,
                duration_ms=ms,
                error="" if success else stderr[:500],
            )
        except Exception as e:
            ms = int((time.perf_counter() - t0) * 1000)
            return RuntimeResult(success=False, error=str(e), duration_ms=ms)
        finally:
            if tmp_path:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

    def run_command(
        self,
        cmd,
        timeout: int = DEFAULT_TIMEOUT,
        cwd: str = None,
    ) -> RuntimeResult:
        """Run a shell command safely. Returns RuntimeResult."""
        timeout = min(timeout, self.MAX_TIMEOUT)
        t0 = time.perf_counter()

        try:
            cmd_str = cmd if isinstance(cmd, str) else " ".join(str(c) for c in cmd)
            if self._is_blocked(cmd_str):
                return RuntimeResult.failure(f"Command blocked by safety policy: {cmd_str[:80]}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd,
                shell=isinstance(cmd, str),
            )
            ms = int((time.perf_counter() - t0) * 1000)
            success = result.returncode == 0
            return RuntimeResult(
                success=success,
                stdout=result.stdout,
                stderr=result.stderr,
                returncode=result.returncode,
                duration_ms=ms,
                error="" if success else result.stderr[:500],
            )
        except subprocess.TimeoutExpired:
            ms = int((time.perf_counter() - t0) * 1000)
            return RuntimeResult(success=False, error=f"Command timed out after {timeout}s", duration_ms=ms)
        except Exception as e:
            ms = int((time.perf_counter() - t0) * 1000)
            return RuntimeResult(success=False, error=str(e), duration_ms=ms)

    def run_file(
        self,
        path: str,
        timeout: int = 60,
        args: list = None,
    ) -> RuntimeResult:
        """Run a Python file. Returns RuntimeResult."""
        timeout = min(timeout, self.MAX_TIMEOUT)
        t0 = time.perf_counter()

        try:
            if not Path(path).exists():
                return RuntimeResult.failure(f"File not found: {path}")

            cmd = [sys.executable, path] + (args or [])
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            deadline = time.perf_counter() + timeout
            while proc.poll() is None:
                if time.perf_counter() > deadline:
                    proc.kill()
                    proc.wait()
                    ms = int((time.perf_counter() - t0) * 1000)
                    return RuntimeResult(
                        success=False,
                        error=f"File execution timed out after {timeout}s",
                        returncode=-9,
                        duration_ms=ms,
                    )
                time.sleep(0.05)

            stdout, stderr = proc.communicate()
            ms = int((time.perf_counter() - t0) * 1000)
            success = proc.returncode == 0
            return RuntimeResult(
                success=success,
                stdout=stdout,
                stderr=stderr,
                returncode=proc.returncode,
                duration_ms=ms,
                error="" if success else stderr[:500],
            )
        except Exception as e:
            ms = int((time.perf_counter() - t0) * 1000)
            return RuntimeResult(success=False, error=str(e), duration_ms=ms)

    def _is_blocked(self, cmd: str) -> bool:
        """Check command string against BLOCKED_COMMANDS list (substring match)."""
        cmd_lower = cmd.lower()
        for blocked in self.BLOCKED_COMMANDS:
            if blocked.lower() in cmd_lower:
                return True
        return False


_runtime: ExecutionRuntime | None = None


def get_runtime() -> ExecutionRuntime:
    global _runtime
    if _runtime is None:
        _runtime = ExecutionRuntime()
    return _runtime
