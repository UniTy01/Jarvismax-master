# MIGRATION_PLAN.md

## Renamed Modules
| Old | New | Impact |
|---|---|---|
| `.env.production` | `.env.production.example` | Don't track secrets |

## Removed Files
| File | Reason | Impact |
|---|---|---|
| `send_telegram.py` | Hardcoded bot token | None — was standalone script |
| `send_telegram_v5.py` | Hardcoded bot token | None |
| `archive/legacy_apks/*.apk` | 235MB bloat | Store in GitHub Releases instead |

## Deprecated Paths
| Component | Status | Migration |
|---|---|---|
| `start_api.py` | Prints deprecation warning | Use `python main.py` |
| `api/control_api.py` | Still works via start_api.py | Use FastAPI `api/main.py` |
| `JarvisOrchestrator` direct usage | All paths now use MetaOrchestrator | Import still works for compat |
| `OrchestratorV2` direct usage | All paths now use MetaOrchestrator | Import still works for compat |
| `MissionStatus` from mission_system.py | Re-exports from core/state.py | `from core.mission_system import MissionStatus` still works |
| `MissionStatus` from meta_orchestrator.py | Re-exports from core/state.py | `from core.meta_orchestrator import MissionStatus` still works |

## Compatibility Notes
- All existing `from core.mission_system import MissionStatus` imports continue to work (re-export)
- All existing `from core.meta_orchestrator import MissionStatus` imports continue to work (re-export)
- `from core import MissionStatus` works
- **New canonical import**: `from core.state import MissionStatus`
- MetaOrchestrator accepts all kwargs that JarvisOrchestrator/OrchestratorV2 accepted
- Flutter app now defaults to `10.0.2.2` (Android emulator) — configure real server in app Settings
