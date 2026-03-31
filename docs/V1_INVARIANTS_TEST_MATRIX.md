# V1 Invariants Test Matrix — ENFORCED 🔒

## Purpose

These tests are architecture guardrails. If they fail, a regression has occurred.
All must pass before merge to master.

---

## Test Matrix

| # | Invariant | Test File | Tests | Status |
|---|-----------|-----------|-------|--------|
| 1 | CanonicalAction 7 statuses unchanged | test_v1_invariants.py | 3 | 🟢 |
| 2 | Result envelope required fields | test_v1_invariants.py | 3 | 🟢 |
| 3 | trace_id propagates end-to-end | test_v1_invariants.py | 4 | 🟢 |
| 4 | Canonical terminal statuses | test_v1_invariants.py | 2 | 🟢 |
| 5 | Production startup guard | test_v1_invariants.py | 3 | 🟢 |
| 6 | Canonical API schemas serializable | test_v1_invariants.py | 3 | 🟢 |
| 7 | Legacy aliases not canonical | test_v1_invariants.py | 3 | 🟢 |

**Total: 21 invariant tests**

---

## Additional Test Suites

| File | Tests | What It Covers |
|------|-------|----------------|
| test_event_envelope.py | 15 | EventEnvelope, trace context, collector |
| test_action_model.py | 13 | CanonicalAction lifecycle, legacy mapping |
| test_result_envelope.py | 11 | FinalOutput schema, aggregator |
| test_result_invariants.py | 14 | Envelope fields, status mapping, serialization |
| test_trace_invariants.py | 18 | trace_id format, propagation, context |
| test_capabilities.py | 14 | Capability registry, risk checks |
| test_v1_invariants.py | 21 | All 7 architecture invariants |

**Grand total: ~106 architecture tests**

---

## When Tests Must Run

- Before every merge to master
- In GitHub Actions CI job
- After any code change to:
  - `core/schemas/final_output.py`
  - `core/actions/action_model.py`
  - `core/observability/event_envelope.py`
  - `core/security/startup_guard.py`
  - `core/result_aggregator.py`
  - `api/routes/trace.py`

## Test Execution

```bash
# Run all v1 invariant tests
pytest tests/test_v1_invariants.py tests/test_trace_invariants.py \
       tests/test_result_invariants.py tests/test_event_envelope.py \
       tests/test_action_model.py tests/test_result_envelope.py \
       tests/test_capabilities.py -v

# Quick smoke test
pytest tests/test_v1_invariants.py -v
```
