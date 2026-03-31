# Flutter Production Config Report

## Status: CONFIGURED ✅

### Connection profiles (api_config.dart)
| Profile | Host | Port | Status |
|---|---|---|---|
| emulator | 10.0.2.2 | 8000 | ✅ |
| local | 192.168.129.20 | 8000 | ✅ |
| tailscale | 100.109.1.124 | 8000 | ✅ |
| **production** | **77.42.40.146** | **8000** | ✅ NEW |

### Backend alignment
- Mission list: `GET /api/v2/missions` ✅
- Mission detail: `GET /api/v2/missions/{id}` ✅
- Mission submit: `POST /api/mission` ✅
- Mission approve: `POST /api/v1/missions/{id}/approve` ✅
- Mission reject: `POST /api/v1/missions/{id}/reject` ✅
- Health check: `GET /api/health` ✅
- Auth: `POST /auth/token` → JWT → `Authorization: Bearer` ✅

### Realtime
- WebSocket: `ws://{host}:{port}/ws/stream` ✅
- SSE: `GET /api/v1/missions/{id}/stream` ✅
- Polling fallback: 30s interval with adaptive backoff ✅

### Approval flow
- Pending actions loaded via `GET /api/v2/tasks` ✅
- Approve: `POST /api/v2/tasks/{id}/approve` ✅
- Reject: `POST /api/v2/tasks/{id}/reject` ✅

### Known issue
- WebSocket reads JWT from SharedPreferences (`jwt_token` key)
- ApiService stores JWT in FlutterSecureStorage (`jarvis_jwt_token` key)
- Minor mismatch — WebSocket may not authenticate if token stored only in secure storage
