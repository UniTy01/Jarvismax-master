# Failure Pattern Reuse Report

## Status: ACTIVE ✅

### How it works
1. Before execution, search failure memory for goals similar to current
2. If matches found (score > 0.4): reduce confidence by 0.1 per match
3. Inject warning into execution goal
4. Strategy may change to 'cautious' or 'decompose'

### After execution
- learning_loop.py extracts lessons from failures
- Lessons stored via MemoryFacade for future pre-execution matching
