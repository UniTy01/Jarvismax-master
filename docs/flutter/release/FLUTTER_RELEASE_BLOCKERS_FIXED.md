# FLUTTER RELEASE BLOCKERS — FIXED

**Phase 1 of Flutter Release Engineering**
Date: 2026-03-27 | Status: ALL BLOCKERS RESOLVED

---

## Blocker 1 — JWT stored in SharedPreferences (SECURITY)

**Problem**: JWT was stored in SharedPreferences (plain-text key-value, unencrypted on Android). Exploitable via any app with READ_EXTERNAL_STORAGE on non-FDE devices.

**Fix**: Migrated to flutter_secure_storage with AndroidOptions(encryptedSharedPreferences: true) — Android Keystore-backed AES-256 encryption.
New methods: saveJwt(), clearJwt(), _loadJwt() — all use FlutterSecureStorage.

---

## Blocker 2 — Hardcoded credentials in production code (SECURITY)

**Problem**: api_service.dart contained an auto-login block with hardcoded
credentials ('admin' / 'JarvisSecretKey2026!'). Password extractable from APK binary.

**Fix**: Auto-login block removed. Comment: "SECURITY: hardcoded credentials removed. Configure via Settings."

---

## Blocker 3 — WebSocket stream never consumed

**Problem**: WebSocketService.connect() was called but ApiService never subscribed
to ws.stream. The app polled every 30s; WS events were silently dropped.

**Fix**: setWebSocketService(WebSocketService ws) added to ApiService. Subscribes
to the WS stream and dispatches by event type:
- task_progress / mission_update / mission_done / mission_failed -> 4s debounced refresh
- action_pending / action_approved / action_rejected -> immediate action reload
- agent_thinking / token_stream -> notifyListeners()

Wired in main.dart: apiService.setWebSocketService(wsService)

---

## Blocker 4 — getMCPList() calls non-existent endpoint

**Problem**: getMCPList() called GET /api/mcp/list — this route does not exist on
the backend. Dead code, never called from any screen. Would 404 if triggered.

**Fix**: getMCPList() removed from api_service.dart.

---

## Blocker 5 — Release signing uses debug keys (manual step)

**Problem**: android/app/build.gradle uses debug keystore.
APK cannot be submitted to Google Play with debug signing.

**Action Required**:
1. keytool -genkey -v -keystore jarvismax-release.jks -alias jarvismax -keyalg RSA -keysize 2048 -validity 10000
2. Add signingConfig release block to android/app/build.gradle using env vars (KEYSTORE_PASS, KEY_PASS)
3. Store keystore off-VPS, never commit to git

---

## Summary

| Blocker | Severity | Status |
|---------|----------|--------|
| JWT in SharedPreferences | Critical | FIXED |
| Hardcoded credentials | Critical | FIXED |
| WS stream not consumed | High | FIXED |
| getMCPList dead code | Medium | FIXED |
| Release signing | High | Documented (manual step) |

Files modified: lib/services/api_service.dart, lib/main.dart
