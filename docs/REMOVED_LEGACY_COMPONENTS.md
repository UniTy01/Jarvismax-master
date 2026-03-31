# REMOVED_LEGACY_COMPONENTS.md

> Complete list of removed legacy systems

## Telegram System (fully removed)
- `jarvis_bot/` — bot.py, __init__.py, README.md
- `python-telegram-bot` dependency
- `TELEGRAM_BOT_TOKEN` env var
- `TELEGRAM_ALLOWED_USER_ID` env var
- `telegram_bot_token` setting
- `telegram_allowed_user_id` setting
- `telegram_chat_id` field in JarvisSession
- `jarvis_bot` Docker service
- Telegram commands section in README
- Telegram references in ARCHITECTURE.md
- `telegram_format()` method (renamed to `summary_format()`)

## Self-Improvement V0 (self_improve/)
- 15 Python files, 5979 lines
- `SelfImproveEngine` class
- `PendingPatchStore` class
- `run_improve_direct.py`
- All imports redirected to `core/self_improvement/`

## Self-Improvement V1 (self_improvement/)
- 6 Python files, 1088 lines
- Files merged into `core/self_improvement/`:
  - failure_collector.py
  - improvement_planner.py
  - validation_runner.py
  - deployment_gate.py
  - patch_builder.py

## Deprecated Entrypoints
- `start_api.py` — delegated to main.py, now deleted
- `jarvis.py` — experimental CLI, now deleted

## Legacy API
- `api/control_api.py` — 627-line raw HTTP handler (deleted earlier)

## Dead Directories
- `scheduler/` — zero imports
- `experiments/` — zero production imports
- `archive/` — stale scripts
- `jarvismax_app/android_scaffold_backup/` — transitional artifact
