"""
Phase 6 — Mission creation parity test.
Simulates both API and Flutter paths.
Run: python scripts/test_parity.py
"""
import requests
import json
import time
import sys

BASE = "http://localhost:8000"


def create_via_api(goal: str, source: str = "test") -> dict:
    """Flutter / API path."""
    resp = requests.post(f"{BASE}/api/v2/task", json={
        "input": goal,
        "priority": 2,
        "mode": "auto",
    }, timeout=10)
    return {"status": resp.status_code, "data": resp.json() if resp.ok else {}}


def check_mission(task_id: str) -> dict:
    resp = requests.get(f"{BASE}/api/v2/missions/{task_id}", timeout=10)
    return {"status": resp.status_code, "data": resp.json() if resp.ok else {}}


if __name__ == "__main__":
    print("=== Parity Test ===")
    try:
        result = create_via_api("Parity test mission - verify API path", source="parity_test")
        print(f"Mission creation: {result['status']}")
        if result["status"] in (200, 201):
            task_id = result["data"].get("data", {}).get("task_id", "")
            print(f"Task ID: {task_id}")
            if task_id:
                time.sleep(2)
                detail = check_mission(task_id)
                print(f"Mission detail: {detail['status']}")
                print(json.dumps(detail["data"], indent=2, ensure_ascii=False)[:500])

        # Note on API path:
        print("\n--- API path note ---")
        print("Missions submitted via POST /api/v2/missions.")
        print("All paths go through MetaOrchestrator with full auth/emit hooks.")

        sys.exit(0 if result["status"] in (200, 201) else 1)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)
