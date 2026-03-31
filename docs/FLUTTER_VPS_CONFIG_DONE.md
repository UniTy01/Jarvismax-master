# Flutter VPS Config — DONE ✅

## Change (commit 50d8c0c)
Added production profile to `jarvismax_app/lib/config/api_config.dart`:

```dart
static const profiles = {
  'emulator':   ('10.0.2.2',        8000),
  'local':      ('192.168.129.20',  8000),
  'tailscale':  ('100.109.1.124',   8000),
  'production': ('77.42.40.146',    8000),  // ← NEW
};
```

## Verification
- Base URL: `http://77.42.40.146:8000` ✅
- No localhost references in production path ✅
- HTTP timeout: 8s GET, 15s POST (reasonable for mobile) ✅
- WebSocket endpoint: `ws://77.42.40.146:8000/ws/stream` ✅

## Endpoint confirmations
| Endpoint | Method | Result |
|---|---|---|
| `/api/v1/missions` | GET | ✅ Loads mission list |
| `/api/v2/missions/{id}` | GET | ✅ Loads full mission detail with final_output |
| `/api/v1/missions/{id}/approve` | POST | ✅ Approves mission |
| `/api/v1/missions/{id}/reject` | POST | ✅ Rejects mission |
| `/api/health` | GET | ✅ Returns health status |

## External reachability
```
$ curl -s http://77.42.40.146:8000/api/health → 200 OK
$ curl -s http://77.42.40.146:8000/api/v1/missions → 401 (auth required)
```
