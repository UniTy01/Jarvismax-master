"""tests/test_aios_dashboard.py — AI OS dashboard API tests."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import pytest
import httpx

BASE = "http://localhost:8000"
TOKEN = os.environ.get("JARVIS_API_TOKEN", "")
H = {"Authorization": f"Bearer {TOKEN}"}


class TestAIOSStatusEndpoint:
    def test_status_returns_200(self):
        r = httpx.get(f"{BASE}/aios/status", headers=H, timeout=10)
        assert r.status_code == 200

    def test_status_has_required_sections(self):
        r = httpx.get(f"{BASE}/aios/status", headers=H, timeout=10)
        data = r.json()["data"]
        required = ["capabilities", "tools", "memory", "policy",
                     "missions", "semantic_router", "recovery", "agents"]
        for section in required:
            assert section in data, f"Missing section: {section}"

    def test_status_capabilities_not_error(self):
        r = httpx.get(f"{BASE}/aios/status", headers=H, timeout=10)
        data = r.json()["data"]
        assert "error" not in data.get("capabilities", {})

    def test_status_tools_count(self):
        r = httpx.get(f"{BASE}/aios/status", headers=H, timeout=10)
        tools = r.json()["data"]["tools"]
        assert tools.get("total", 0) >= 10

    def test_status_policy_profile(self):
        r = httpx.get(f"{BASE}/aios/status", headers=H, timeout=10)
        policy = r.json()["data"]["policy"]
        assert policy.get("active") in ("safe", "balanced", "autonomous")

    def test_status_unauthorized(self):
        r = httpx.get(f"{BASE}/aios/status", timeout=5)
        assert r.status_code in (401, 403)


class TestAIOSIndividualEndpoints:
    def test_manifest(self):
        r = httpx.get(f"{BASE}/aios/manifest", headers=H, timeout=10)
        assert r.status_code == 200
        modules = r.json()["data"]["modules"]
        assert len(modules) >= 11

    def test_capabilities(self):
        r = httpx.get(f"{BASE}/aios/capabilities", headers=H, timeout=5)
        assert r.status_code == 200
        assert r.json()["data"]["total"] >= 9

    def test_tools(self):
        r = httpx.get(f"{BASE}/aios/tools", headers=H, timeout=5)
        assert r.status_code == 200

    def test_memory(self):
        r = httpx.get(f"{BASE}/aios/memory", headers=H, timeout=5)
        assert r.status_code == 200

    def test_agents(self):
        r = httpx.get(f"{BASE}/aios/agents", headers=H, timeout=5)
        assert r.status_code == 200

    def test_policy(self):
        r = httpx.get(f"{BASE}/aios/policy", headers=H, timeout=5)
        assert r.status_code == 200

    def test_semantic_router(self):
        r = httpx.get(f"{BASE}/aios/semantic-router", headers=H, timeout=5)
        assert r.status_code == 200

    def test_vector_memory(self):
        r = httpx.get(f"{BASE}/aios/vector-memory", headers=H, timeout=5)
        assert r.status_code == 200

    def test_recovery(self):
        r = httpx.get(f"{BASE}/aios/recovery", headers=H, timeout=5)
        assert r.status_code == 200

    def test_trace_analysis(self):
        r = httpx.get(f"{BASE}/aios/trace-analysis", headers=H, timeout=5)
        assert r.status_code == 200

    def test_skills(self):
        r = httpx.get(f"{BASE}/aios/skills", headers=H, timeout=5)
        assert r.status_code == 200

    def test_consistency(self):
        r = httpx.get(f"{BASE}/aios/consistency", headers=H, timeout=5)
        assert r.status_code == 200
        issues = r.json()["data"]["issues"]
        assert len(issues) == 0
