# FLUTTER RELEASE TEST PLAN

**Testing Requirements for Flutter Release Engineering**
Date: 2026-03-27

---

## Critical Path Tests

### 1. Authentication
- [ ] First launch: app starts with empty JWT, shows login/settings screen
- [ ] Login: enter VPS URL + credentials -> JWT saved to secure storage
- [ ] Restart: app restores JWT from secure storage, auto-connects
- [ ] Logout: JWT cleared from secure storage, not recoverable without re-login

### 2. Mission Flow
- [ ] Submit mission: POST /api/mission -> mission appears in list within 5s
- [ ] WS update: mission status changes in real-time (no manual refresh needed)
- [ ] Mission detail: tap mission -> detail loads with full agent outputs
- [ ] Live detail update: open detail screen while mission runs -> status updates live
- [ ] Mission abort: POST /api/v2/missions/{id}/abort -> status reflects ABORTED

### 3. Approval Flow
- [ ] Pending actions badge: count updates within 5s via WS event
- [ ] Approve action: tap approve -> action disappears from pending list
- [ ] Reject action: tap reject + reason -> action marked rejected
- [ ] Bulk: multiple actions -> approve/reject each independently

### 4. Real-time Updates (WS)
- [ ] Disconnect VPS network -> app shows offline state
- [ ] Reconnect -> app recovers, resumes polling
- [ ] WS reconnect: verify WebSocketService.connect() retries on disconnect
- [ ] Submit mission -> agent_thinking events update UI without 30s wait

### 5. Network Resilience
- [ ] VPS unreachable for 2 minutes -> adaptive guard kicks in (health-check-only)
- [ ] VPS comes back -> full refresh resumes automatically
- [ ] Slow network (simulate 5s latency) -> timeouts handled gracefully, no crash

### 6. Security
- [ ] APK binary: strings jarvismax.apk | grep -i password -> no credentials found
- [ ] Android Keystore: JWT not visible in adb backup or plain SharedPreferences dump
- [ ] Release APK: signed with release key (not debug)

---

## Regression Tests

- [ ] All 9 screens navigate without crash
- [ ] Dashboard loads agent status
- [ ] CapabilitiesScreen loads /api/v2/system/capabilities
- [ ] SelfImprovementScreen loads /api/v2/self-improvement/suggestions
- [ ] InsightsScreen loads metrics
- [ ] SettingsScreen saves server URL and credentials

---

## Not Tested (out of scope for RC)

- Push notifications
- File upload/download
- Offline mode with local cache
- Multiple concurrent users
