# FLUTTER REALTIME WIRING REPORT

**Phase 2 of Flutter Release Engineering**
Date: 2026-03-27 | Status: WIRED

---

## Before

- WebSocketService connected at app start (correct)
- ApiService held no reference to WebSocketService
- WS stream events arrived but were never consumed
- UI updates triggered only by 30s polling timer

## After

### ApiService <- WebSocketService (new binding)

```
main.dart
  apiService.setWebSocketService(wsService)
    -> _wsService = ws
    -> _wsSubscription = _wsService!.stream.listen(_handleWsEvent)
```

### Event dispatch table

| WS event type | Action |
|---|---|
| task_progress | _debouncedMissionRefresh() (4s) |
| mission_update | _debouncedMissionRefresh() (4s) |
| mission_done | _debouncedMissionRefresh() (4s) |
| mission_failed | _debouncedMissionRefresh() (4s) |
| action_pending | _loadActions() immediately |
| action_approved | _loadActions() immediately |
| action_rejected | _loadActions() immediately |
| agent_thinking | notifyListeners() |
| token_stream | notifyListeners() |
| (any other) | notifyListeners() |

### MissionDetailScreen live updates (new)

MissionDetailScreen now subscribes to ApiService in initState:
- Registers _onApiChanged listener on ApiService
- When missions list is refreshed by WS event, checks if this mission's
  status changed in the list
- If status changed: calls _fetchDetail() to reload full mission detail
- Unsubscribes in dispose() to prevent memory leaks

### Debounce strategy

_debouncedMissionRefresh() cancels any pending timer before restarting a 4s
countdown. This prevents flooding the backend when WS emits burst events
(e.g., multiple task_progress during agent execution).

---

## WS event types confirmed from ws_hub.py

- task_progress: mission progress percentage
- agent_thinking: LLM reasoning stream
- token_stream: raw token output
- multimodal_result: image/audio result (future use)
- mission_update / mission_done / mission_failed: lifecycle events
- action_pending / action_approved / action_rejected: approval flow
