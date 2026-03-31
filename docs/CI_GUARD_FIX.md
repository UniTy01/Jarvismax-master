# CI Guard Fix

## Problem
Dead try/except block with `pass` instead of real import:
```python
try:
    pass  # imported at module level
    _MC_AVAILABLE = True
except ImportError:
    _MC_AVAILABLE = False
```
This always set `_MC_AVAILABLE = True` but never actually imported anything.
A second valid block followed, but was redundant.

Additionally, the FastAPI stub lacked `Depends`, so `mission_control.py` 
couldn't import even with the guard fixed.

## Fix
1. Removed dead `try: pass` block — single clean guard remains
2. Added `Depends` to FastAPI stub in test file
3. Tests now run (not skip) in both CI and Docker environments

## Verification
- Docker: 36 passed, 0 skipped ✅
- CI: guard correctly skips only when fastapi truly unavailable
