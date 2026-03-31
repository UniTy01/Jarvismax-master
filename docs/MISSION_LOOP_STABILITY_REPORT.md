# Phase 6: Mission Loop Stability

## Status: STABLE ✅

### No infinite loops: _MAX_RETRIES = 2 (hard cap)
### No useless retries: only retryable error classes trigger retry
### No uncontrolled recursion: linear pipeline, no recursive calls
### No memory growth: working memory bounded, decay active
### No repeated failures: recent failures retrieved and injected into planning

### Loop phases (each with clear purpose)
1. classify — determine mission type, complexity, risk
2. assemble — gather skills, memory, failures
3. plan — adapt depth to complexity
4. approve — gate if risk ≥ medium
5. execute — delegate to JarvisOrchestrator/V2
6. validate — check output for secrets/errors
7. reflect — evaluate result quality
8. learn — extract lesson if needed
9. store — write to memory
10. refine — update skill confidence
11. trace — audit trail
