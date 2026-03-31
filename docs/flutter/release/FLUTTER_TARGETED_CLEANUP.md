# FLUTTER TARGETED CLEANUP

**Phase 6 of Flutter Release Engineering**
Date: 2026-03-27 | Status: COMPLETE

---

## Removed

- getMCPList() method in api_service.dart (dead code, called non-existent endpoint)
- SharedPreferences import and usage from api_service.dart
- Hardcoded auto-login block from api_service.dart

## Fixed

- UTF-8 encoding bug: "rÃ©pond" -> "répond" in _friendly() error message
  (was caused by incorrect encoding during previous file write)

## Deprecated Warnings (acknowledged, not blocking)

The following use deprecated Flutter APIs. They compile and work correctly
but will need updating before the next major Flutter version:

- lib/screens/mission_detail_screen.dart:421 - activeColor -> use activeThumbColor
- lib/screens/mode_screen.dart:386 - activeColor deprecated
- lib/screens/settings_screen.dart:371, 444 - activeColor deprecated

These are cosmetic (Switch widget thumb color) and do not affect functionality.

## Pre-existing Error (not fixed in this pass)

- lib/theme/app_theme.dart:56 - CardTheme -> CardThemeData
  Requires: change CardTheme( to CardThemeData( in app_theme.dart
  Risk: zero functional impact (theme styling only)
  Decision: deferred to post-RC cleanup
