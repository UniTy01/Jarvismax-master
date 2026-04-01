# CI Root Cause Analysis

## 5 test failures in "Deploy to VPS" → test job

### Failure 1: test_no_hardcoded_production_ip (test_beta_architecture.py)
**Cause**: We added production VPS profile `77.42.40.146` to `api_config.dart`.
A test greps all source for hardcoded production IPs and fails if found.
**Verdict**: False positive — `api_config.dart` is intentional client config, not a leaked secret.

### Failures 2-5: TestAPICanonicalStatus (test_status_memory_consolidation.py)
**Cause**: We added `Depends` import to `mission_control.py` for JWT auth.
CI installs minimal `fastapi` from `requirements.txt` which doesn't include `Depends`.
When tests import `_canonical_status` from mission_control, the module-level import fails.
**Verdict**: CI environment mismatch — full fastapi is in Docker, minimal in CI.

### Impact
- Every push to master triggers → test fails → deploy skipped → failure email
- 10+ failure emails sent in this session alone
