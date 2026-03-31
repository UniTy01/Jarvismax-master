"""
core/tools/http_tool.py — HTTP request tool for external API calls.

MEDIUM risk — allows GET/POST to external URLs.
"""
from __future__ import annotations

import json
import os
import logging

from core.tools.tool_template import BaseTool, ToolResult

log = logging.getLogger("jarvis.tools.http")

_MAX_RESPONSE_CHARS = 50_000
_BLOCKED_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "169.254.169.254"}


class HttpTool(BaseTool):
    name = "http_request"
    risk_level = "MEDIUM"
    description = "Make HTTP GET/POST requests to external APIs"
    timeout_seconds = 15.0

    def execute(self, url: str = "", method: str = "GET",
                headers: dict = None, body: dict = None, **kw) -> ToolResult:
        if not url:
            return ToolResult(ok=False, error="missing_url")
        if not url.startswith(("http://", "https://")):
            return ToolResult(ok=False, error="invalid_url: must start with http(s)://")

        # Block internal network access
        try:
            from urllib.parse import urlparse
            host = urlparse(url).hostname or ""
            if host in _BLOCKED_HOSTS or host.startswith("10.") or host.startswith("172."):
                return ToolResult(ok=False, error=f"blocked_host: {host}")
        except Exception:
            pass

        method = method.upper()
        if method not in ("GET", "POST", "PUT", "PATCH", "DELETE"):
            return ToolResult(ok=False, error=f"unsupported_method: {method}")

        try:
            import requests
            req_headers = {"User-Agent": "JarvisMax/1.0"}
            if headers:
                req_headers.update(headers)

            if method == "GET":
                resp = requests.get(url, headers=req_headers, timeout=self.timeout_seconds)
            else:
                resp = requests.request(
                    method, url,
                    headers=req_headers,
                    json=body if body else None,
                    timeout=self.timeout_seconds,
                )

            result_text = resp.text[:_MAX_RESPONSE_CHARS]

            if resp.ok:
                return ToolResult(ok=True, result=result_text)
            else:
                return ToolResult(
                    ok=False,
                    error=f"http_{resp.status_code}: {result_text[:200]}",
                    retryable=resp.status_code in (429, 500, 502, 503, 504),
                )

        except requests.Timeout:
            return ToolResult(ok=False, error="http_timeout", retryable=True)
        except requests.ConnectionError as e:
            return ToolResult(ok=False, error=f"connection_error: {str(e)[:200]}", retryable=True)
        except Exception as e:
            return ToolResult(ok=False, error=f"http_error: {str(e)[:200]}")
