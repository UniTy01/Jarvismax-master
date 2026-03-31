# FLUTTER MISSION & APPROVAL FLOW VALIDATION

**Phase 3 of Flutter Release Engineering**
Date: 2026-03-27 | Status: VALIDATED

---

## Mission Flow

| Flutter call | Backend route | Status |
|---|---|---|
| POST /api/mission | POST /api/mission -> alias /api/v2/task | OK |
| GET /api/v2/missions | GET /api/v2/missions | OK |
| GET /api/v2/missions/{id} | GET /api/v2/missions/{mission_id} | OK |
| POST /api/v2/missions/{id}/abort | POST /api/v2/missions/{mission_id}/abort | OK |

## Approval Flow

| Flutter call | Backend route | Status |
|---|---|---|
| POST /api/v2/tasks/{id}/approve | POST /api/v2/tasks/{task_id}/approve | OK |
| POST /api/v2/tasks/{id}/reject | POST /api/v2/tasks/{task_id}/reject | OK |
| GET /api/v2/tasks | GET /api/v2/tasks | OK |

## System/Mode Endpoints

| Flutter call | Backend route | Status |
|---|---|---|
| GET /api/v2/status | GET /api/v2/status | OK |
| POST /api/system/mode | POST /api/system/mode | OK |
| GET /api/system/mode/uncensored | GET /api/system/mode/uncensored | OK |
| POST /api/system/mode/uncensored | POST /api/system/mode/uncensored | OK |
| GET /api/v2/system/policy-mode | GET /api/v2/system/policy-mode | OK |
| POST /api/v2/system/policy-mode | POST /api/v2/system/policy-mode | OK |
| GET /api/v2/system/capabilities | GET /api/v2/system/capabilities | OK |
| GET /api/v2/metrics/recent | GET /api/v2/metrics/recent | OK |

## Self-Improvement Endpoints

| Flutter call | Backend route | Status |
|---|---|---|
| GET /api/v2/self-improvement/suggestions | GET /api/v2/self-improvement/suggestions | ADDED |

**Fix**: /suggestions endpoint was missing from backend. Added to
api/routes/self_improvement.py: calls WeaknessDetector.detect() and returns
{suggestions: [{domain, severity, suggested_focus, evidence}]}.

## Dead Code Removed

- getMCPList() -> GET /api/mcp/list: route does not exist, method removed.
  Never called from any screen.

## SSE Stream

Flutter calls GET /api/v1/missions/{id}/stream — this route exists in
missions.py (line 877-882). Uses _sse_generator from mission_control.py.
Connection is established but the stream consumer (in MissionDetailScreen)
is not yet connected to the SSE endpoint. The WS stream (Phase 2) covers
the real-time update need for now.

---

## Verdict

All mission and approval endpoints are aligned. The self-improvement
suggestions endpoint was the only mismatch — fixed.
