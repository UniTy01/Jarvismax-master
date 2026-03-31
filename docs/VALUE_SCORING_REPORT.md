# Value Scoring Report

## Status: IMPROVED ✅

### Before
value_score = urgency*0.6 + complexity*0.4 (two factors)

### After
value_score = urgency*0.4 + impact*0.3 + feasibility*0.3 (three factors)

### New factors
- **Impact**: task type matters (debugging=0.9 > query=0.3)
- **Feasibility**: simpler tasks score higher (trivial=0.95, complex=0.4)
- Prevents wasting compute on infeasible tasks

### Test: critical debug (0.76) > research (0.59) > trivial query (0.58)
