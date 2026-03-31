# HexStrike AI MCP Integration

## Overview
HexStrike AI v6.0 — Advanced cybersecurity MCP server with 150+ security tools.
Source: https://github.com/0x4m4/hexstrike-ai

## Architecture
- `hexstrike_server.py` — Flask server (port 8888) with 150+ security tools
- `hexstrike_mcp.py` — FastMCP client that connects AI agents to the server

## Setup
```bash
# Install deps (inside Docker or venv)
pip install -r requirements.txt

# Start the server
python3 hexstrike_server.py --port 8888

# MCP client connects via:
python3 hexstrike_mcp.py --server http://localhost:8888
```

## JarvisMax Integration
Registered as MCP connector in modules_v3 with:
- Transport: stdio (FastMCP)
- Server: http://localhost:8888
- Trust: community (external, requires review)
- Risk: high (offensive security tooling)
- Requires approval: yes (all tool executions)
