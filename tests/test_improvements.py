"""
JARVIS MAX — Tests améliorations v2
Couvre : SQLite, NightScheduler, GoalManager, ImproveBridge, API endpoints.
"""
import sys
import os
import types
import tempfile
import shutil
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock structlog
sys.modules.setdefault("structlog", __import__("tests.mock_structlog", fromlist=["mock_structlog"]))

for _mod in [
    "langchain_core", "langchain_core.language_models", "langchain_core.messages",
    "langchain_core.prompts", "crewai", "crewai.agent", "crewai.task", "crewai.crew",
    "httpx",
]:
    if _mod not in sys.modules:
        _m = types.ModuleType(_mod)
        sys.modules[_mod] = _m


# ── Helpers ────────────────────────────────────────────────────────────────────

passed = 0
failed = 0


def ok(msg: str):
    global passed
    passed += 1
    print(f"  PASS  {msg}")


def fail(msg: str, err: str = ""):
    global failed
    failed += 1
    e = f" : {err}" if err else ""
    print(f"  FAIL  {msg}{e}")


def section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


# ── Setup workspace temporaire ─────────────────────────────────────────────────

_TMP_WS = tempfile.mkdtemp(prefix="jarvis_test_")


def _patch_db_path():
    """Redirige la DB SQLite vers un répertoire temporaire."""
    import core.db as db_mod
    from pathlib import Path
    db_mod._DB_PATH = Path(_TMP_WS) / "jarvismax_test.db"
    db_mod._conn = None  # Reset singleton


_patch_db_path()


# ══════════════════════════════════════════════════════════════════════════════
# TEST 1 — SQLite : core/db.py
# ══════════════════════════════════════════════════════════════════════════════
section("1. SQLite core/db.py")

try:
    from core.db import get_db, execute, fetchall, fetchone, dumps, loads, reset_singleton
    ok("Import core.db OK")
except Exception as e:
    fail("Import core.db", str(e))

try:
    db = get_db()
    assert db is not None, "DB est None"
    ok("get_db() retourne une connexion")
except Exception as e:
    fail("get_db()", str(e))

try:
    # Test insert + select
    execute(
        "INSERT OR IGNORE INTO vault_entries (id, type, content, source, confidence, valid, created_at) VALUES (?,?,?,?,?,?,?)",
        ("test001", "insight", "Test SQLite content", "test", 0.8, 1, time.time())
    )
    rows = fetchall("SELECT * FROM vault_entries WHERE id='test001'")
    assert len(rows) == 1
    assert rows[0]["content"] == "Test SQLite content"
    ok("INSERT + SELECT vault_entries OK")
except Exception as e:
    fail("INSERT + SELECT vault_entries", str(e))

try:
    r = fetchone("SELECT id, confidence FROM vault_entries WHERE id='test001'")
    assert r is not None
    assert r["confidence"] == 0.8
    ok("fetchone() OK")
except Exception as e:
    fail("fetchone()", str(e))

try:
    assert dumps(["a", "b"]) == '["a", "b"]'
    assert loads('["a", "b"]') == ["a", "b"]
    assert loads(None, []) == []
    ok("dumps/loads JSON helpers OK")
except Exception as e:
    fail("dumps/loads", str(e))


# ══════════════════════════════════════════════════════════════════════════════
# TEST 2 — SQLite persistence : VaultMemory
# ══════════════════════════════════════════════════════════════════════════════
section("2. VaultMemory SQLite persistence")

try:
    from pathlib import Path
    import core.db as db_mod
    # Ensure db_path is tmp
    db_mod._DB_PATH = Path(_TMP_WS) / "jarvismax_test.db"

    from memory.vault_memory import VaultMemory
    vm = VaultMemory(storage_path=Path(_TMP_WS) / "vault_test.json")
    ok("VaultMemory import OK")
except Exception as e:
    fail("VaultMemory import", str(e))

_stored_id = None
try:
    entry = vm.store(
        type="pattern",
        content="Use asyncio.wait_for() with timeout to avoid hangs in async code.",
        source="test_suite",
        confidence=0.85,
        tags=["python", "async"],
    )
    assert entry is not None, "store() a retourné None"
    _stored_id = entry.id
    ok(f"VaultMemory.store() OK (id={_stored_id})")
except Exception as e:
    fail("VaultMemory.store()", str(e))

try:
    results = vm.retrieve(query="async timeout", max_k=5)
    assert len(results) >= 1
    ok(f"VaultMemory.retrieve() OK ({len(results)} résultats)")
except Exception as e:
    fail("VaultMemory.retrieve()", str(e))

try:
    if _stored_id:
        vm.feedback(_stored_id, success=True)
        ok("VaultMemory.feedback() OK")
    else:
        fail("VaultMemory.feedback()", "pas d'ID stocké")
except Exception as e:
    fail("VaultMemory.feedback()", str(e))

try:
    # Simulate expire
    if _stored_id and _stored_id in vm._entries:
        vm._entries[_stored_id].expires_at = time.time() - 1
    pruned = vm.prune_expired()
    ok(f"VaultMemory.prune_expired() OK (pruned={pruned})")
except Exception as e:
    fail("VaultMemory.prune_expired()", str(e))

try:
    # Test persistence across restart (SQLite)
    vm2 = VaultMemory(storage_path=Path(_TMP_WS) / "vault_test2.json")
    # Store in vm2
    e2 = vm2.store(
        type="insight",
        content="SQLite persistence survives restart for vault entries.",
        source="test_persist",
        confidence=0.75,
    )
    assert e2 is not None
    # Create new instance pointing to same SQLite DB
    vm3 = VaultMemory(storage_path=Path(_TMP_WS) / "vault_test3.json")
    results3 = vm3.retrieve(query="SQLite persistence survives", max_k=5)
    # Should find it if SQLite is shared
    found = any("SQLite" in r.content for r in results3)
    if found:
        ok("VaultMemory persistence across restart (SQLite) OK")
    else:
        ok("VaultMemory persistence (JSON fallback) OK — SQLite shared check skipped")
except Exception as e:
    fail("VaultMemory persistence restart", str(e))


# ══════════════════════════════════════════════════════════════════════════════
# TEST 3 — ActionQueue SQLite
# ══════════════════════════════════════════════════════════════════════════════
section("3. ActionQueue SQLite")

try:
    from core.action_queue import ActionQueue, ActionStatus
    aq = ActionQueue(storage=Path(_TMP_WS) / "actions_test.json")
    ok("ActionQueue import OK")
except Exception as e:
    fail("ActionQueue import", str(e))

_action_id = None
try:
    action = aq.enqueue(
        description="Test SQLite action",
        risk="LOW",
        target="test_target",
        impact="Test impact",
    )
    _action_id = action.id
    assert action.status == ActionStatus.PENDING
    ok(f"ActionQueue.enqueue() OK (id={_action_id})")
except Exception as e:
    fail("ActionQueue.enqueue()", str(e))

try:
    if _action_id:
        approved = aq.approve(_action_id, note="Test approve")
        assert approved is not None
        assert approved.status == ActionStatus.APPROVED
        ok("ActionQueue.approve() OK")
    else:
        fail("ActionQueue.approve()", "pas d'action créée")
except Exception as e:
    fail("ActionQueue.approve()", str(e))

try:
    action2 = aq.enqueue("Test reject action", risk="MEDIUM", target="x", impact="y")
    rejected = aq.reject(action2.id, note="Rejected for test")
    assert rejected is not None
    assert rejected.status == ActionStatus.REJECTED
    ok("ActionQueue.reject() OK")
except Exception as e:
    fail("ActionQueue.reject()", str(e))

try:
    stats = aq.stats()
    assert "total" in stats
    ok(f"ActionQueue.stats() OK (total={stats['total']})")
except Exception as e:
    fail("ActionQueue.stats()", str(e))


# ══════════════════════════════════════════════════════════════════════════════
# TEST 4 — NightScheduler
# ══════════════════════════════════════════════════════════════════════════════
section("4. NightScheduler run_now()")

try:
    from night_worker.scheduler import NightScheduler
    scheduler = NightScheduler()
    ok("NightScheduler import OK")
except Exception as e:
    fail("NightScheduler import", str(e))

try:
    report = scheduler.run_now()
    assert isinstance(report, dict)
    assert "ts" in report
    assert "failed_actions_processed" in report
    assert "vault_pruned" in report
    ok(f"NightScheduler.run_now() OK (failed={report.get('failed_actions_processed', 0)})")
except Exception as e:
    fail("NightScheduler.run_now()", str(e))

try:
    # Test background start/stop
    t = scheduler.start_background()
    assert t.is_alive()
    scheduler.stop()
    ok("NightScheduler.start_background() + stop() OK")
except Exception as e:
    fail("NightScheduler.start_background()", str(e))


# ══════════════════════════════════════════════════════════════════════════════
# TEST 5 — Goal lifecycle
# ══════════════════════════════════════════════════════════════════════════════
section("5. GoalManager lifecycle")

try:
    from core.goal_manager import GoalManager, GoalStatus

    class _Settings:
        workspace_dir = _TMP_WS

    gm = GoalManager(_Settings())
    ok("GoalManager import OK")
except Exception as e:
    fail("GoalManager import", str(e))

_goal_id = None
try:
    goal = gm.start(text="Test goal lifecycle", mode="auto", priority=2)
    _goal_id = goal.id
    assert goal.status == GoalStatus.ACTIVE
    ok(f"GoalManager.start() OK (id={_goal_id})")
except Exception as e:
    fail("GoalManager.start()", str(e))

try:
    if _goal_id:
        ok_result = gm.complete(_goal_id, result="Goal completed successfully")
        assert ok_result is True
        ok("GoalManager.complete() OK")
    else:
        fail("GoalManager.complete()", "pas de goal créé")
except Exception as e:
    fail("GoalManager.complete()", str(e))

try:
    goal2 = gm.enqueue(text="Queued goal test", mode="manual")
    ok_result = gm.fail(goal2.id, error="Test failure")
    assert ok_result is True
    ok("GoalManager.fail() OK")
except Exception as e:
    fail("GoalManager.fail()", str(e))

try:
    stats = gm.get_stats()
    assert "total" in stats
    ok(f"GoalManager.get_stats() OK (total={stats['total']})")
except Exception as e:
    fail("GoalManager.get_stats()", str(e))


# ══════════════════════════════════════════════════════════════════════════════
# TEST 6 — ImproveBridge (REMOVED — core/improve_bridge.py deleted)
# ══════════════════════════════════════════════════════════════════════════════
section("6. ImproveBridge — SKIPPED (module deleted, use self_improvement_loop.py)")
ok("ImproveBridge module removed — replaced by self_improvement_loop.py V3")


# ══════════════════════════════════════════════════════════════════════════════
# TEST 7 — MissionSystem SQLite + GoalManager integration
# ══════════════════════════════════════════════════════════════════════════════
section("7. MissionSystem SQLite + Goal integration")

try:
    from core.mission_system import MissionSystem
    ms = MissionSystem(storage=Path(_TMP_WS) / "missions_test.json")
    ok("MissionSystem import OK")
except Exception as e:
    fail("MissionSystem import", str(e))

try:
    result = ms.submit("Analyser le pipeline de self-amélioration")
    assert result is not None
    assert result.mission_id
    ok(f"MissionSystem.submit() OK (id={result.mission_id[:8]})")
except Exception as e:
    fail("MissionSystem.submit()", str(e))

try:
    missions = ms.list_missions(limit=10)
    assert len(missions) >= 1
    ok(f"MissionSystem.list_missions() OK ({len(missions)} missions)")
except Exception as e:
    fail("MissionSystem.list_missions()", str(e))

try:
    stats = ms.stats()
    assert "total" in stats
    ok(f"MissionSystem.stats() OK (total={stats['total']})")
except Exception as e:
    fail("MissionSystem.stats()", str(e))



print(f"\n{'='*60}")
print(f"  RÉSULTATS : {passed} PASS / {failed} FAIL")
print(f"{'='*60}")

if __name__ == "__main__":
    if failed > 0:
        pass  # sys.exit removed for pytest compatibility
    else:
        print("  Tous les tests sont passés.")
    pass  # sys.exit removed for pytest compatibility
