# Architecture Lock v1 — FROZEN

## Status: LOCKED 🔒

No structural changes without explicit version bump.

---

## Locked Components

### Runtime
| Component | Location | Status |
|-----------|----------|--------|
| MetaOrchestrator | core/meta_orchestrator.py | LOCKED |
| ToolExecutor | core/tool_executor.py | LOCKED |
| MissionSystem | core/mission_system.py | LOCKED |
| ActionExecutor | core/action_executor.py | LOCKED |
| MemoryFacade | core/memory_facade.py | LOCKED |

### Schemas
| Component | Location | Status |
|-----------|----------|--------|
| FinalOutput | core/schemas/final_output.py | LOCKED |
| CanonicalAction | core/actions/action_model.py | LOCKED |
| EventEnvelope | core/observability/event_envelope.py | LOCKED |
| Capability | core/capabilities/schema.py | LOCKED |

### API Surface
| Endpoint | Status |
|----------|--------|
| POST /api/v1/mission/run | LOCKED |
| GET /api/v2/missions/{id} | LOCKED |
| GET /api/v1/trace/{trace_id} | LOCKED |
| POST /api/v1/missions/{id}/approve | LOCKED |
| GET /api/health | LOCKED |
| ws://host/ws/stream | LOCKED |

---

## What LOCKED means

- **DO NOT** rename, remove, or change the public interface
- **DO NOT** add required parameters to existing endpoints
- **DO NOT** change response schema shapes
- **CAN** add optional fields to responses
- **CAN** add new endpoints (with new paths)
- **CAN** fix bugs in behavior (same contract, better implementation)
- **CAN** improve internal implementation without changing contract

---

## Regression Prevention

### Test suites (must pass before merge)
- test_beta_architecture.py
- test_stabilization_final.py
- test_hardening_safety.py
- test_status_memory_consolidation.py
- test_result_envelope.py
- test_capabilities.py
- test_event_envelope.py
- test_action_model.py

### CI enforcement
- GitHub Actions `test` job runs on every push to master
- Deploy blocked if tests fail
- Concurrency group prevents run pile-up

---

## Iteration Rules

1. **Bug fixes**: direct to master, test, deploy
2. **Small features**: branch → test → merge
3. **Schema changes**: requires version bump proposal
4. **Breaking changes**: NOT ALLOWED in v1

---

## Module counts (baseline)
- core/: 30+ modules
- api/routes/: 16 route files
- tests/: 17 test suites
- Total tests: ~300
- Lines added this session: ~3,500+

## Production baseline
- Master: frozen after this commit
- VPS: 77.42.40.146:8000
- Health: 6/6 components OK
- Real missions: 10/10 completed
