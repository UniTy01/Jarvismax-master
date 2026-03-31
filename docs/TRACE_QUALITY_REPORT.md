# Trace Quality Report

## Status: IMPROVED ✅

### New: human_summary() in DecisionTrace
Produces readable text explaining WHY Jarvis acted:
```
Mission abc-123:
  CLASSIFY: research — keyword: analyze
  PRE_CHECK: proceed — tools_ok=True failures=0
  EXECUTE: success — completed in 2s
  COST: $0.0030 (700 tokens)
  DURATION: 2.1s across 3 steps
```

### Trace now covers
- Value scoring reasoning
- Pre-execution assessment
- Strategy switching decisions
- Fallback attempts
- Cost per mission
