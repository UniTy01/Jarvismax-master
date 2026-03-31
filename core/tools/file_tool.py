"""
core/tools/file_tool.py — Structured file read/write tool.

LOW risk for read, MEDIUM for write.
Sandboxed to workspace directory.
"""
from __future__ import annotations

import json
import os
import logging
from pathlib import Path

from core.tools.tool_template import BaseTool, ToolResult

log = logging.getLogger("jarvis.tools.file")

_WORKSPACE = Path(os.getenv("WORKSPACE_DIR", "/app/workspace"))
_MAX_READ_CHARS = 100_000
_MAX_WRITE_CHARS = 50_000
_ALLOWED_EXTENSIONS = {".txt", ".md", ".json", ".yaml", ".yml", ".csv", ".log", ".py", ".html"}


def _safe_path(path_str: str) -> Path | None:
    """Resolve path within workspace sandbox. Returns None if escape attempt."""
    try:
        target = (_WORKSPACE / path_str).resolve()
        if not str(target).startswith(str(_WORKSPACE.resolve())):
            return None
        return target
    except Exception:
        return None


class FileReadTool(BaseTool):
    name = "file_read"
    risk_level = "LOW"
    description = "Read file contents from workspace"
    timeout_seconds = 5.0

    def execute(self, path: str = "", **kw) -> ToolResult:
        if not path:
            return ToolResult(ok=False, error="missing_path")

        safe = _safe_path(path)
        if safe is None:
            return ToolResult(ok=False, error="path_escape: must stay within workspace")

        if not safe.exists():
            return ToolResult(ok=False, error=f"file_not_found: {path}")
        if not safe.is_file():
            return ToolResult(ok=False, error=f"not_a_file: {path}")
        if safe.suffix not in _ALLOWED_EXTENSIONS and safe.suffix:
            return ToolResult(ok=False, error=f"extension_not_allowed: {safe.suffix}")

        try:
            content = safe.read_text(encoding="utf-8")
            if len(content) > _MAX_READ_CHARS:
                content = content[:_MAX_READ_CHARS] + f"\n\n[truncated at {_MAX_READ_CHARS} chars]"
            return ToolResult(ok=True, result=content)
        except UnicodeDecodeError:
            return ToolResult(ok=False, error="binary_file: cannot read as text")
        except Exception as e:
            return ToolResult(ok=False, error=f"read_error: {str(e)[:200]}")


class FileWriteTool(BaseTool):
    name = "file_write"
    risk_level = "MEDIUM"
    description = "Write content to file in workspace"
    timeout_seconds = 5.0

    def execute(self, path: str = "", content: str = "", append: bool = False, **kw) -> ToolResult:
        if not path:
            return ToolResult(ok=False, error="missing_path")
        if not content:
            return ToolResult(ok=False, error="missing_content")
        if len(content) > _MAX_WRITE_CHARS:
            return ToolResult(ok=False, error=f"content_too_large: {len(content)} > {_MAX_WRITE_CHARS}")

        safe = _safe_path(path)
        if safe is None:
            return ToolResult(ok=False, error="path_escape: must stay within workspace")

        if safe.suffix not in _ALLOWED_EXTENSIONS and safe.suffix:
            return ToolResult(ok=False, error=f"extension_not_allowed: {safe.suffix}")

        try:
            safe.parent.mkdir(parents=True, exist_ok=True)
            mode = "a" if append else "w"
            with open(safe, mode, encoding="utf-8") as f:
                f.write(content)
            action = "appended to" if append else "wrote"
            return ToolResult(ok=True, result=f"{action} {path} ({len(content)} chars)")
        except Exception as e:
            return ToolResult(ok=False, error=f"write_error: {str(e)[:200]}")
