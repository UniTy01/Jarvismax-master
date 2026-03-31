"""
FilesystemTool — safe file operations scoped to workspace/.
Blocks path traversal and absolute paths outside workspace.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from tools.base import BaseTool, ToolRisk

WORKSPACE_ROOT = Path("workspace").resolve()


def _safe_path(path: str) -> Path | None:
    """Resolve path and verify it's inside workspace/. Returns None if unsafe."""
    try:
        resolved = (WORKSPACE_ROOT / path).resolve()
        if not str(resolved).startswith(str(WORKSPACE_ROOT)):
            return None
        return resolved
    except Exception:
        return None


class FilesystemTool(BaseTool):
    name = "filesystem_tool"
    risk = ToolRisk.SUPERVISED

    def read(self, path: str) -> dict:
        """Read file contents. Blocked outside workspace/."""
        safe = _safe_path(path)
        if safe is None:
            return {"success": False, "error": f"Path not allowed: {path}"}
        try:
            if not safe.exists():
                return {"success": False, "error": f"File not found: {path}"}
            content = safe.read_text(encoding="utf-8")
            return {"success": True, "result": content, "path": str(safe)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def write(self, path: str, content: str) -> dict:
        """Write content to file. Blocked outside workspace/."""
        safe = _safe_path(path)
        if safe is None:
            return {"success": False, "error": f"Path not allowed: {path}"}
        try:
            safe.parent.mkdir(parents=True, exist_ok=True)
            safe.write_text(content, encoding="utf-8")
            return {"success": True, "result": f"Written {len(content)} chars to {path}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_dir(self, path: str = "") -> dict:
        """List directory contents. Blocked outside workspace/."""
        safe = _safe_path(path) if path else WORKSPACE_ROOT
        if safe is None:
            return {"success": False, "error": f"Path not allowed: {path}"}
        try:
            if not safe.is_dir():
                return {"success": False, "error": f"Not a directory: {path}"}
            entries = [
                {"name": e.name, "type": "dir" if e.is_dir() else "file", "size": e.stat().st_size if e.is_file() else 0}
                for e in sorted(safe.iterdir())
            ]
            return {"success": True, "result": entries}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def exists(self, path: str) -> dict:
        """Check if path exists."""
        safe = _safe_path(path)
        if safe is None:
            return {"success": True, "result": False}
        return {"success": True, "result": safe.exists()}
