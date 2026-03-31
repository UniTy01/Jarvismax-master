# ROADMAP — Jarvis Max

> Mis à jour le 2026-03-25

---

## Fait ✅

### Phase 1-2 — Fondations
- [x] Orchestrateur central (MetaOrchestrator + state machine)
- [x] 9 agents parallèles (Atlas, Scout, Map, Forge, Lens, Vault, Shadow, Pulse, Night)
- [x] Moteur de risque LOW/MEDIUM/HIGH
- [x] Exécution d'actions supervisée avec backup + rollback
- [x] Boucle nuit autonome (NightWorker, max 5 cycles)
- [x] Interface Telegram (commandes, approval gate MEDIUM/HIGH)

### Phase 3 — Résilience
- [x] Circuit breakers + policy engine
- [x] Goal manager
- [x] Decision replay
- [x] Mémoire vectorielle per-agent (Qdrant fail-open)
- [x] Suite de tests : 262 tests + validate.py

### Phase 4 — Auto-amélioration legacy
- [x] Self-Improve Engine original (`self_improve/`)
- [x] Guards anti-self-modify (FORBIDDEN_SELF_MODIFY)
- [x] Pipeline classique : audit → patch → review → validation

### Phase 5 — Cognition & Objectifs
- [x] **Knowledge Engine** — difficulté, patterns, capacités (`core/knowledge/`)
- [x] **Objective Engine** — objectifs persistants, breakdown, scoring, next action (`core/objectives/`)
- [x] **Planner v2** — injection objective context + difficulty
- [x] **API v2** — endpoints objectifs, self-improvement, monitoring
- [x] **Self-Improvement Loop V1** — weakness→candidates→scorer→safe_executor (`core/self_improvement/`)

### Phase 6 — Nettoyage architectural (2026-03-25)
- [x] Audit AUDIT_REPO.md
- [x] Archive APKs legacy (`archive/legacy_apks/`)
- [x] Marquage LEGACY (`self_improve/LEGACY.md`, `self_improvement/LEGACY.md`)
- [x] Docs canoniques (ARCHITECTURE.md, ROADMAP.md, CHANGELOG.md)
- [x] Fix write error logging dans `improvement_memory._save()`

---

## En cours 🔄

- [ ] Première exécution de la boucle SI V1 en production (workspace/self_improvement/ à créer)
- [ ] Monitoring des cycles d'objectifs en conditions réelles

---

## Prochaines étapes

### Court terme
- [ ] Migration commande `/improve` Telegram vers `core/self_improvement/`
- [ ] Synchronisation guards : `self_improve/guards.py` ↔ `core/self_improvement/safe_executor.py`
- [ ] Supprimer `self_improvement/` (version intermédiaire) après vérification des imports
- [ ] Documenter API v2 complète (OpenAPI/Swagger)

### Moyen terme
- [ ] Dashboard de monitoring des objectifs (interface web)
- [ ] Métriques de succès de la boucle SI (taux d'amélioration mesurable)
- [ ] Load testing : combien d'objectifs actifs simultanément en production ?
- [ ] Réduire APKs de l'historique git (`git-filter-repo`)

### Long terme
- [ ] Multi-user support
- [ ] Agent builder autonome (API v2 agent-builder déjà présent)
- [ ] Intégration OpenHands complète (`adapters/`)
- [ ] Business modules activés en production (`business/`)
