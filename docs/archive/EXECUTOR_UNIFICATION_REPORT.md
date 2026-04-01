# Executor Unification Report

## Problem
3 `ExecutionResult` classes, 3 `is_retryable()` functions, 2 retry engines.
No canonical contract.

## Solution

### Canonical Contract: executor/contracts.py
- `ExecutionResult`: execution_id, status, error_class, duration_ms, retryable, validation_status
- `ErrorClass`: 11 categories (timeout, permission, LLM, rate_limit...)
- `classify_error()`: string → ErrorClass
- `is_retryable()`: ErrorClass → bool

### Unification Actions
| Action | Detail |
|--------|--------|
| task_model.py ExecutionResult | **Replaced** with re-export from contracts.py |
| executor/__init__.py | **Rewritten** to export from canonical locations |
| retry_engine.py | **Deprecated** (zero external callers) |
| risk_engine.py | Kept (thin re-export from risk/engine.py) |
| supervised_executor.py | Kept (used by legacy orchestrator.py) |

### Canonical Pipeline
```
task request → validation → execution → retry if allowed → structured result
```

### What Remains
- supervised_executor.py: used by core/orchestrator.py (legacy delegate)
- runner.py: used by supervised_executor + system.py
- Both will be absorbed when core/orchestrator.py is deprecated
