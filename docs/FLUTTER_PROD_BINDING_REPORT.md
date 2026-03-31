# Flutter Production Binding Report

## Backend alignment: COMPATIBLE ✅

### Endpoint mapping
| Flutter calls | Backend route | Status |
|---|---|---|
| POST /api/mission | /api/mission (legacy alias) | ✅ Working |
| GET /api/v1/missions | /api/v1/missions | ✅ Working |
| POST /api/v1/missions/{id}/approve | /api/v1/missions/{id}/approve | ✅ Working |
| POST /api/v1/missions/{id}/reject | /api/v1/missions/{id}/reject | ✅ Working |
| GET /api/health | /api/health | ✅ Working |

### Connection profiles (api_config.dart)
- emulator: 10.0.2.2:8000
- local: 192.168.129.20:8000
- tailscale: 100.109.1.124:8000
- NEEDS: add production VPS profile (77.42.40.146:8000 or via Tailscale)

### Realtime: WebSocket
- websocket_service.dart connects to ws://{baseUrl}/ws
- Events: mission_update, mission_done, mission_failed, action_approved
- Polling fallback: yes (debounced, 4s)
- Status: WebSocket endpoint exists on backend ✅

### Token handling
- JWT stored in SharedPreferences
- Sent as query param on WebSocket connection
- Backend accepts unauthenticated for now (no JWT enforcement yet)

### Mission status mapping
- Backend: CREATED → PENDING_VALIDATION → APPROVED → DONE/FAILED
- Flutter: maps via Mission model, shows in list view

### Blocking issues
1. No production VPS profile in api_config.dart (easy fix)
2. JWT not enforced on backend (security concern for production)
3. Final result text not displayed (v1 API returns summary, not full LLM output)

### Release APK
- Android signing: needs keystore configuration
- Build: `flutter build apk --release` (standard Flutter flow)
- Not yet tested against production — needs VPS profile added first
