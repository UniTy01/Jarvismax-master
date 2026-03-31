# CHANGELOG — Jarvis Max

Format : `type: description (commit hash)`

---

## [Unreleased] — 2026-03-25

### Nettoyage architectural
- `cleanup`: archive APKs legacy vers `archive/legacy_apks/` (8 fichiers)
- `cleanup`: archive scripts legacy vers `archive/legacy_scripts/` (add_firewall_rule.bat, build_v5.bat)
- `cleanup`: marquage LEGACY de `self_improve/` et `self_improvement/`
- `docs`: création ARCHITECTURE.md — schéma complet des couches
- `docs`: création ROADMAP.md — état des phases et prochaines étapes
- `docs`: création CHANGELOG.md (ce fichier)
- `docs`: création AUDIT_REPO.md — inventaire ACTIVE/LEGACY/DUPLICATE/CANONICAL
- `fix`: `improvement_memory._save()` — ajout `logger.warning` sur erreur d'écriture

---

## [Phase 5] — 2026-03-24

### Self-Improvement Loop V1
- `feat`: boucle SI V1 canonique dans `core/self_improvement/` (`a8ac85b`)
  - WeaknessDetector, CandidateGenerator, ImprovementScorer, SafeExecutor, ImprovementMemory
  - Anti-loop guards : MAX=1, COOLDOWN=24h, MAX_FAILURES=3
  - Écriture atomic dans workspace/ (PROMPT_TWEAK | TOOL_PREFERENCE | RETRY_STRATEGY | SKIP_PATTERN)

### Objective Engine
- `feat`: Objective Engine persistant (`bda142f`)
  - CRUD objectifs + breakdown automatique en sous-objectifs
  - Scoring priorité dynamique (difficulté + dépendances)
  - Next best action via DAG
  - Persistance JSON + Qdrant vectoriel (fail-open)
  - API v2 : GET/POST /api/v2/objectives/*

- `fix`: clamp sub-objective difficulty to [0,1] in breakdown (`f69a425`)
- `fix`: objective_breakdown — clamp difficulty to 1.0, sanitize pattern_tools to strings (`35151b7`)
- `merge`: Objective Engine bugfix — difficulty clamp + pattern_tools sanitize (`9b1e039`)

---

## [Phase 5 — Knowledge] — 2026-03

### Knowledge Engine
- `feat`: knowledge & capability engine — `core/knowledge/` (`4e6c4f3`)
  - DifficultyEstimator, CapabilityScorer, PatternDetector
  - Intégration dans Planner + ObjectiveBreakdown

### Cognitive Engine
- `feat`: cognitive engine — memory quality, difficulty (`e6d9600`)
  - MemoryQuality evaluator
  - Intégration dans planner.py avec fail-open

---

## [Phase 3-4] — Antérieur

### Résilience
- Circuit breakers + policy engine
- Decision replay + rollback
- Mémoire vectorielle per-agent (Qdrant)

### Auto-amélioration legacy
- Self-Improve Engine original (`self_improve/`)
- Guards FORBIDDEN_SELF_MODIFY
- Pipeline classique audit → patch → review → validation

### Fondations
- MetaOrchestrator + state machine CREATED→PLANNED→RUNNING→REVIEW→DONE
- 9 agents parallèles par priorité
- Moteur risque LOW/MEDIUM/HIGH + approval gate Telegram
- Suite de tests 262 tests + validate.py 126KB
