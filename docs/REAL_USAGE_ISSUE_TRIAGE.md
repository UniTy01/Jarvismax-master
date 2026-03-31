# Real Usage Issue Triage

## P0 — Blocks real usage now
- FIXED: 'service' in SYSTEM risk keywords caused business missions to BLOCKED
  - Root cause: _RISK_KW_SYSTEM contained 'service' and 'config'
  - Impact: Any goal mentioning 'service' got +3 risk (business missions routinely score 7+)
  - Fix: Removed 'service' and 'config' from system risk keywords

## P1 — Significantly harms usefulness
- v1 API final_output is just 'X/X actions exécutées' — not the actual LLM response
  - Impact: Human cannot see the actual business analysis without digging into action logs
  - Fix needed: Aggregate agent action results into final_output field
  - NOT fixing now (requires v1 API refactor)

- No production VPS profile in Flutter api_config.dart
  - Impact: APK cannot connect to production without manual config
  - Fix: trivial (add profile entry)

## P2 — Polish / later
- JWT not enforced (backend accepts unauthenticated requests)
- MetaOrchestrator path not used by v1 API (known, deferred)
- Ollama model not used as primary (hybrid mode uses cloud first)
- No cost tracking per mission in v1 API
