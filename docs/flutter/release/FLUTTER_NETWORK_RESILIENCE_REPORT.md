# FLUTTER NETWORK RESILIENCE REPORT

**Phase 4 of Flutter Release Engineering**
Date: 2026-03-27 | Status: HARDENED

---

## Existing Resilience (pre-existing, confirmed)

- GET requests: 8s timeout
- POST requests: 15s timeout (adequate for LLM pipeline calls)
- Health check: tries /health then / fallback
- All data-loading methods: try/catch with _lastError state
- WS event debounce: 4s (prevents backend flood on burst events)
- refresh() wraps all parallel loads in try/catch finally

## New: Adaptive Offline Guard

**Problem**: Auto-refresh timer fired every 30s regardless of server state.
When the VPS is unreachable (restart, network hiccup), the app would fire
4 parallel HTTP requests every 30s — all timing out after 8-15s each.

**Fix** added to startAutoRefresh():
- Tracks _offlineStreak counter
- After 3 consecutive offline cycles (90s offline), switches to lightweight
  health-check-only mode instead of full refresh
- When server comes back online (health check succeeds), resumes normal refresh
- _offlineStreak resets to 0 on successful refresh

```
Behavior when offline:
  tick 1 (30s): full refresh -> fails -> _offlineStreak = 1
  tick 2 (60s): full refresh -> fails -> _offlineStreak = 2
  tick 3 (90s): full refresh -> fails -> _offlineStreak = 3
  tick 4 (120s): health check only -> if still down, return early
  tick 5+: health check only until server is back
```

## Timeout Assessment

| Operation | Timeout | Adequate? |
|---|---|---|
| GET requests | 8s | Yes (status, missions list) |
| POST /api/mission | 15s | Yes (LLM pipeline can take 10-15s) |
| POST approve/reject | 15s | Yes (quick DB write) |
| Health check | 8s | Yes |
| WS connection | (managed by WebSocketService) | OK |

## Remaining Gap (acceptable for RC)

- No exponential backoff on the 30s timer (adaptive guard covers the flood case)
- No retry on single 502/503 responses (Docker restart transients)
  -> Acceptable: next 30s tick will retry
