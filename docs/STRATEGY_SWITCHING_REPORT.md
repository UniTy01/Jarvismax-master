# Strategy Switching Report

## Status: IMPROVED ✅

### Before
- Transient errors → retry (max 2)
- All other errors → abort
- FALLBACK/REPLAN → treated as abort

### After
| Error Type | Attempt 0 | Attempt 1 | Attempt 2+ |
|---|---|---|---|
| Transient (timeout, connection) | RETRY | RETRY | FALLBACK |
| Permanent (permission, invalid) | ABORT | — | — |
| Execution error | RETRY | FALLBACK | — |
| LLM error | RETRY | FALLBACK | — |
| High risk (any) | ESCALATE | — | — |

### FALLBACK behavior
- Retries with simplified goal prefix
- If simplified also fails → abort with structured trace
