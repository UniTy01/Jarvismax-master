# App Integration Contract

## Backend contracts for Flutter

| Endpoint | Data | Status |
|---|---|---|
| GET /api/health | {status, components} | STABLE ✅ |
| GET /api/v1/missions | [{id, status, goal, created_at}] | STABLE ✅ |
| POST /api/v1/mission/run | {goal} → {mission_id, status} | STABLE ✅ |
| POST /missions/{id}/approve | → {status} | STABLE ✅ |
| GET /missions/{id}/log | [{action, data}] | STABLE ✅ |

## Data models
- MissionStatus: PLANNED→RUNNING→REVIEW→DONE/FAILED/CANCELLED
- ExecutionResult: success, result, error, error_class, retries
- DecisionTrace: summary() → list[dict], human_summary() → str

## Stable enough for Flutter binding: YES
