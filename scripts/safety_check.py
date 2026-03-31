"""
Pre-self-test safety validation.
All checks must pass before supervised self-testing can begin.
Run: python scripts/safety_check.py
"""
import sys
sys.path.insert(0, '.')

results = {}


# 1. Loop risk: OrchestrationGuard has max_retries limit
def check_loop_risk():
    try:
        from core.orchestration_guard import OrchestrationGuard
        guard = OrchestrationGuard()
        assert guard.DEFAULT_MAX_RETRIES <= 5, f"Retry limit too high: {guard.DEFAULT_MAX_RETRIES}"
        return "PASS", f"max_retries={guard.DEFAULT_MAX_RETRIES}"
    except Exception as e:
        return "FAIL", str(e)


# 2. Retry limits enforced
def check_retry_limits():
    try:
        from core.orchestration_guard import get_guard
        guard = get_guard()
        call_count = 0

        def failing_fn():
            nonlocal call_count
            call_count += 1
            raise RuntimeError("intentional failure")

        result = guard.execute("test", "test-agent", failing_fn, max_retries=2, timeout_s=5)
        assert not result.success
        assert call_count <= 3, f"Called {call_count} times, expected <= 3"
        return "PASS", f"called {call_count} times (limit=2 retries)"
    except Exception as e:
        return "FAIL", str(e)


# 3. Mission cancellation API exists
def check_cancellation():
    try:
        from api.main import app
        routes = [r.path for r in app.routes]
        cancel_routes = [r for r in routes if "cancel" in r or "abort" in r]
        assert cancel_routes, "No cancel/abort route found"
        return "PASS", f"routes: {cancel_routes}"
    except Exception as e:
        return "FAIL", str(e)


# 4. System mode switch works
def check_mode_switch():
    try:
        from api.main import app
        routes = [r.path for r in app.routes]
        mode_routes = [r for r in routes if "mode" in r or "system" in r]
        assert mode_routes, "No mode/system route found"
        return "PASS", f"mode routes: {mode_routes}"
    except Exception as e:
        return "FAIL", str(e)


# 5. SSE endpoint exists
def check_sse_endpoint():
    try:
        from api.main import app
        routes = [r.path for r in app.routes]
        sse_routes = [r for r in routes if "stream" in r]
        assert sse_routes, "No stream route found"
        return "PASS", f"SSE routes: {sse_routes}"
    except Exception as e:
        return "FAIL", str(e)


# 6. Failure reason captured (MissionStateStore)
def check_failure_capture():
    try:
        from api.mission_store import MissionStateStore
        from api.models import MissionLogEvent, LogEventType

        store = MissionStateStore.get()
        event = MissionLogEvent(
            mission_id="test-failure-check",
            event_type=LogEventType.ERROR,
            message="test failure capture",
        )
        store.append_log(event)
        logs = store.get_log("test-failure-check")
        assert len(logs) > 0, "No logs found after append"
        return "PASS", "failure events stored in MissionStateStore"
    except Exception as e:
        return "FAIL", str(e)


# 7. Memory unbounded growth protection
def check_memory_bounds():
    try:
        from api.mission_store import MissionStateStore
        store = MissionStateStore.get()
        assert hasattr(store, "clear_old_logs"), "clear_old_logs method missing"
        return "PASS", "clear_old_logs exists"
    except Exception as e:
        return "FAIL", str(e)


checks = [
    ("1. Loop risk (retry limit)", check_loop_risk),
    ("2. Retry limits enforced", check_retry_limits),
    ("3. Mission cancellation route", check_cancellation),
    ("4. System mode switch route", check_mode_switch),
    ("5. SSE endpoint exists", check_sse_endpoint),
    ("6. Failure reason captured", check_failure_capture),
    ("7. Memory bound protection", check_memory_bounds),
]

print("=== Pre Self-Test Safety Check ===\n")
passed = 0
for name, fn in checks:
    status, detail = fn()
    icon = "v" if status == "PASS" else "x"
    print(f"[{icon}] {name}: {status}")
    print(f"    {detail}")
    if status == "PASS":
        passed += 1

print(f"\n{passed}/{len(checks)} checks passed")
sys.exit(0 if passed == len(checks) else 1)
