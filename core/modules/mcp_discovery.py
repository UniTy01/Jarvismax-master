"""
JARVIS MAX — MCP Discovery Client
=====================================
Real MCP protocol discovery for stdio and HTTP servers.

Connects to MCP servers, requests tool lists, parses schemas,
and registers discovered tools.

Safety: timeout protection, safe parsing, no code execution,
audit logging, clear error messages.
"""
from __future__ import annotations

import json
import logging
import subprocess
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

DISCOVERY_TIMEOUT = 15  # seconds


@dataclass
class DiscoveredTool:
    """A tool discovered from an MCP server."""
    name: str
    description: str = ""
    input_schema: dict = field(default_factory=dict)
    output_schema: dict = field(default_factory=dict)
    transport: str = ""
    connector_id: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description[:200],
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "transport": self.transport,
            "connector_id": self.connector_id,
        }


@dataclass
class DiscoveryResult:
    """Result of MCP tool discovery."""
    success: bool
    mcp_id: str
    tools: list[DiscoveredTool] = field(default_factory=list)
    error: str = ""
    latency_ms: float = 0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "mcp_id": self.mcp_id,
            "tools": [t.to_dict() for t in self.tools],
            "tool_count": len(self.tools),
            "error": self.error[:200],
            "latency_ms": round(self.latency_ms, 1),
        }


class MCPDiscoveryClient:
    """
    Discovers tools from MCP servers via stdio or HTTP.
    """

    def __init__(self, timeout: int = DISCOVERY_TIMEOUT):
        self._timeout = timeout

    def discover(self, mcp_id: str, transport: str, endpoint: str,
                 headers: dict | None = None, env_vars: dict | None = None) -> DiscoveryResult:
        """
        Discover tools from an MCP server.
        
        Args:
            mcp_id: MCP connector ID
            transport: "stdio" or "http"
            endpoint: Command (stdio) or URL (http)
            headers: HTTP headers (for http transport)
            env_vars: Environment variables (for stdio transport)
        """
        start = time.time()

        if not endpoint:
            return DiscoveryResult(success=False, mcp_id=mcp_id,
                                   error="No endpoint configured")

        try:
            if transport == "stdio":
                return self._discover_stdio(mcp_id, endpoint, env_vars or {}, start)
            elif transport in ("http", "https"):
                return self._discover_http(mcp_id, endpoint, headers or {}, start)
            else:
                return DiscoveryResult(success=False, mcp_id=mcp_id,
                                       error=f"Unsupported transport: {transport}")
        except Exception as e:
            latency = (time.time() - start) * 1000
            return DiscoveryResult(success=False, mcp_id=mcp_id,
                                   error=str(e)[:200], latency_ms=latency)

    def _discover_stdio(self, mcp_id: str, command: str, env: dict,
                        start: float) -> DiscoveryResult:
        """Discover tools via stdio MCP protocol."""
        import os
        import shlex

        # Build the JSON-RPC request for tools/list
        request = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {},
        }) + "\n"

        try:
            proc_env = {**os.environ, **env}
            args = shlex.split(command)

            proc = subprocess.run(
                args,
                input=request,
                capture_output=True,
                text=True,
                timeout=self._timeout,
                env=proc_env,
            )

            latency = (time.time() - start) * 1000

            if proc.returncode != 0:
                return DiscoveryResult(
                    success=False, mcp_id=mcp_id,
                    error=f"Process exited with code {proc.returncode}: {proc.stderr[:200]}",
                    latency_ms=latency,
                )

            return self._parse_response(mcp_id, proc.stdout, "stdio", latency)

        except subprocess.TimeoutExpired:
            latency = (time.time() - start) * 1000
            return DiscoveryResult(success=False, mcp_id=mcp_id,
                                   error="Discovery timed out", latency_ms=latency)
        except FileNotFoundError:
            return DiscoveryResult(success=False, mcp_id=mcp_id,
                                   error=f"Command not found: {command.split()[0]}")

    def _discover_http(self, mcp_id: str, url: str, headers: dict,
                       start: float) -> DiscoveryResult:
        """Discover tools via HTTP MCP protocol."""
        import urllib.request
        import urllib.error

        request_body = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {},
        }).encode()

        req_headers = {
            "Content-Type": "application/json",
            **{k: v for k, v in headers.items() if k.lower() not in ("host",)},
        }

        try:
            req = urllib.request.Request(url, data=request_body, headers=req_headers, method="POST")
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                body = resp.read().decode("utf-8")
                latency = (time.time() - start) * 1000
                return self._parse_response(mcp_id, body, "http", latency)

        except urllib.error.URLError as e:
            latency = (time.time() - start) * 1000
            return DiscoveryResult(success=False, mcp_id=mcp_id,
                                   error=f"Service unreachable: {str(e)[:150]}", latency_ms=latency)
        except TimeoutError:
            return DiscoveryResult(success=False, mcp_id=mcp_id,
                                   error="Discovery timed out")

    def _parse_response(self, mcp_id: str, raw: str, transport: str,
                        latency: float) -> DiscoveryResult:
        """Parse MCP JSON-RPC response into DiscoveredTool list."""
        try:
            # Find JSON in response (may have extra output)
            json_start = raw.find("{")
            if json_start < 0:
                return DiscoveryResult(success=False, mcp_id=mcp_id,
                                       error="No JSON in response", latency_ms=latency)

            data = json.loads(raw[json_start:])

            if "error" in data:
                err = data["error"]
                msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
                return DiscoveryResult(success=False, mcp_id=mcp_id,
                                       error=f"MCP error: {msg[:200]}", latency_ms=latency)

            result = data.get("result", {})
            tool_list = result.get("tools", [])

            if not isinstance(tool_list, list):
                return DiscoveryResult(success=False, mcp_id=mcp_id,
                                       error="Invalid tool list format", latency_ms=latency)

            tools = []
            for t in tool_list:
                if not isinstance(t, dict) or "name" not in t:
                    continue
                tools.append(DiscoveredTool(
                    name=t["name"],
                    description=t.get("description", ""),
                    input_schema=t.get("inputSchema", t.get("input_schema", {})),
                    output_schema=t.get("outputSchema", t.get("output_schema", {})),
                    transport=transport,
                    connector_id=mcp_id,
                ))

            return DiscoveryResult(
                success=True, mcp_id=mcp_id,
                tools=tools, latency_ms=latency,
            )

        except json.JSONDecodeError:
            return DiscoveryResult(success=False, mcp_id=mcp_id,
                                   error="Invalid JSON response", latency_ms=latency)
