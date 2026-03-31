# Real Device Ready Checklist

## Pre-flight ✅

- [x] API token set and enforced (`JARVIS_API_TOKEN`)
- [x] Bearer auth working (Flutter compatible)
- [x] Production VPS profile in api_config.dart (77.42.40.146:8000)
- [x] Health endpoint accessible without auth
- [x] Mission CRUD endpoints working with auth
- [x] WebSocket endpoint exists at `/ws/stream`
- [x] Full mission results visible in API response
- [x] No localhost dependency in production config
- [x] No debug-only endpoints exposed

## Device test steps

1. **Build APK**
   ```bash
   cd jarvismax_app
   flutter build apk --release
   ```

2. **Install on device**
   ```bash
   adb install build/app/outputs/flutter-apk/app-release.apk
   ```

3. **Configure connection**
   - Open Settings in app
   - Select "production" profile (77.42.40.146:8000)
   - Login with admin / JARVIS_SECRET_KEY

4. **Test sequence**
   - [ ] Health check shows green
   - [ ] Mission list loads
   - [ ] Submit a test mission
   - [ ] Approval notification appears
   - [ ] Approve mission
   - [ ] Mission completes
   - [ ] Full result text visible
   - [ ] WebSocket events received (realtime updates)

## Known limitations for device test
- VPS port 8000 must be accessible (check firewall: `ufw allow 8000`)
- WebSocket JWT token mismatch between storage backends (minor)
- Agent outputs are infrastructure-focused, not full business analysis
- No TLS (HTTP only) — use VPN/Tailscale for security in production

## External reachability check
```bash
# From any external machine:
curl -s http://77.42.40.146:8000/api/health
# Should return: {"ok": true, "data": {"status": "ok", ...}}
```
