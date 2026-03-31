# API Contract v1 — FROZEN 🔒

> This contract is frozen. Changes require version bump.
> Flutter mobile app MUST use only canonical endpoints.
> All other endpoints are DEPRECATED or INTERNAL.

---

## Authentication

All endpoints (except health) require one of:
- `X-Jarvis-Token: <token>` header
- `Authorization: Bearer <token>` header

In production (ENV=production), startup FAILS if token is missing.

---

## CANONICAL ENDPOINTS (v1)

These are the ONLY endpoints the Flutter app and external integrations should use.

### POST /api/v1/mission/run
Submit a new mission.

**Request:**
```json
{"goal": "Identify 3 business opportunities for AI consultant"}
```

**Response:**
```json
{
  "status": "submitted",
  "data": {
    "mission_id": "abc123",
    "status": "CREATED",
    "plan_summary": "..."
  }
}
```

### GET /api/v2/missions/{mission_id}
Retrieve full mission result with envelope.

**Response:**
```json
{
  "ok": true,
  "data": {
    "mission_id": "abc123",
    "status": "DONE",
    "final_output": "# Résultats ...",
    "result_envelope": {
      "mission_id": "abc123",
      "trace_id": "tr-a1b2c3d4e5f6",
      "status": "COMPLETED",
      "summary": "...",
      "agent_outputs": [...],
      "decision_trace": [...],
      "metrics": {"duration_seconds": 45.14}
    },
    "decision_trace": {...}
  }
}
```

### GET /api/v1/trace/{trace_id}
Retrieve lifecycle events for a trace.

**Response:**
```json
{
  "ok": true,
  "data": {
    "trace_id": "tr-a1b2c3d4e5f6",
    "event_count": 5,
    "events": [...]
  }
}
```

### GET /api/v1/trace/mission/{mission_id}
Retrieve all events for a mission across traces.

### POST /api/v1/missions/{mission_id}/approve
Approve a pending mission.

### POST /api/v1/missions/{mission_id}/reject
Reject a mission.

### POST /api/v1/missions/{mission_id}/cancel
Cancel a running mission.

### GET /api/v1/missions
List all missions.

### GET /api/health
Health check (no auth required).

### GET /api/v2/missions
List all missions (alias, returns same data).

---

## DEPRECATED ENDPOINTS

These exist for backward compatibility. DO NOT use in new code.

| Deprecated | Canonical Replacement | Notes |
|---|---|---|
| POST /api/mission | POST /api/v1/mission/run | Legacy alias |
| GET /api/missions | GET /api/v1/missions | Legacy alias |
| GET /api/stats | GET /api/v2/system/health | Legacy |
| POST /api/v2/missions/submit | POST /api/v1/mission/run | v2 alias |
| POST /api/v2/task | — | Task queue (deprecated model) |
| GET /api/v2/task/{id} | — | Task queue (deprecated model) |
| GET /api/v2/tasks | — | Task queue (deprecated model) |
| POST /api/v2/tasks/{id}/approve | POST /api/v1/missions/{id}/approve | v2 alias |
| POST /api/v2/tasks/{id}/reject | POST /api/v1/missions/{id}/reject | v2 alias |

---

## INTERNAL ENDPOINTS

These serve admin/debug purposes. NOT part of the public contract.

| Category | Endpoints | Auth |
|---|---|---|
| Monitoring | /api/v2/metrics, /api/v2/logs, /api/v2/diagnostics | Required |
| Admin | /api/v2/debug/*, /api/v3/* | Required |
| Learning | /api/v2/learning/* | Required |
| Skills | /api/v2/skills/* | Required |
| Self-improvement | /api/v2/self-improvement/* | Required |
| Browser | /api/v2/browser/* | Required |
| RAG | /api/v2/rag/* | Required |
| Voice | /api/v2/voice/* | Required |
| Objectives | /api/v2/objectives/* | Required |
| Dashboard/Cockpit | /cockpit, /dashboard/* | Required |

---

## WebSocket

### ws://{host}:{port}/ws/stream
Real-time mission events. Auth via `?token=<jwt>` query param.

---

## Result Envelope Invariants

Every completed mission's `result_envelope` MUST contain:
- `trace_id` (non-empty)
- `status` (COMPLETED | FAILED | CANCELLED)
- `summary` (string)
- `agent_outputs` (list)
- `decision_trace` (list)
- `metrics` (dict with `duration_seconds`)

---

## Status Flow

```
CREATED → ANALYZING → PENDING_VALIDATION → APPROVED → EXECUTING → DONE
                                         → REJECTED
                                         → BLOCKED
```

## Versioning Policy

- Bug fixes: allowed in-place
- New optional response fields: allowed
- Breaking changes: NOT ALLOWED, requires v2 proposal
- Endpoint removal: NOT ALLOWED in v1 lifetime
