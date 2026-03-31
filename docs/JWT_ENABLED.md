# JWT Enabled — DONE ✅

## Change (commit 50d8c0c)
- `JARVIS_API_TOKEN` set in `.env` (secure random 32-byte, urlsafe)
- Token injected into Docker container via `env_file: .env` in docker-compose
- Auth dependency added to all 16 route files in `api/routes/`

## Auth methods
| Method | Header | Status |
|---|---|---|
| API Token | `X-Jarvis-Token: <token>` | ✅ 200 |
| Bearer | `Authorization: Bearer <token>` | ✅ 200 |
| No token | — | ❌ 401 |
| Wrong token | any | ❌ 401 |

## Implementation
- `api/_deps.py`: `_check_auth()` accepts both header formats
- Each route file has `_auth()` dependency injected via `APIRouter(dependencies=[Depends(_auth)])`
- `api/main.py`: `get_current_user()` updated with dual header support

## Protected endpoints
All routes in `api/routes/` (16 files):
mission_control, missions, approval, cockpit, dashboard, objectives,
performance, self_improvement, skills, system, admin, memory,
monitoring, tools, rag, browser

## Unprotected (by design)
- `GET /api/health` — monitoring tools need unauthenticated access

## Security checklist
- [x] No hardcoded tokens
- [x] No debug bypass
- [x] No test tokens
- [x] Clean 401 response: `{"detail": "Unauthorized"}`
- [x] WebSocket auth via query parameter
- [x] Token rotation: change `.env` + restart container
