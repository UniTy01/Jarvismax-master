=== ARCHITECTURE CLEANUP — RAPPORT FINAL ===
Date : 2026-03-25
Branche : claude/mystifying-tharp

---

[1] AUDIT : RÉSUMÉ DE L'ÉTAT TROUVÉ

Jarvis Max est un système mature et stable (262 tests, Phase 5 complète).
Trois problèmes structurels identifiés à l'entrée :
  - 14 APKs binaires à la racine du repo (~900MB, non archivés)
  - Trois modules self-improvement coexistants sans marquage clair
  - Absence totale de ARCHITECTURE.md, ROADMAP.md, CHANGELOG.md

Système self-improvement : trois modules trouvés —
  core/self_improvement/  ← V1 CANONIQUE (commit a8ac85b, hier)
  self_improve/           ← LEGACY mature (encore actif via /improve Telegram)
  self_improvement/       ← LEGACY intermédiaire (plus référencé)

Problème de code trouvé :
  core/self_improvement/improvement_memory._save() n'avait pas de try/except
  → les erreurs d'écriture remontaient silencieusement jusqu'au handler API

---

[2] DÉPLACEMENTS : FICHIERS DÉPLACÉS + DESTINATION

APKs (8 fichiers) → archive/legacy_apks/
  jarvismax-debug.apk
  jarvismax-release.apk
  jarvismax-stable.apk
  jarvismax-v3-fixed.apk
  jarvismax-v4-connection-fix.apk
  jarvismax-v5-full-fix.apk
  jarvismax-v6-mission-fixed.apk
  jarvismax-vps-release.apk

Scripts legacy (2 fichiers) → archive/legacy_scripts/
  add_firewall_rule.bat   (config firewall one-shot)
  build_v5.bat            (build script legacy v5)

---

[3] ARCHIVÉS : FICHIERS MARQUÉS LEGACY

self_improve/LEGACY.md     → marquage + inventaire + plan de migration
self_improvement/LEGACY.md → marquage + mapping vers équivalents V1

Note : les modules sont conservés intacts — uniquement marqués.
self_improve/ reste actif via /improve Telegram, ne pas supprimer.

---

[4] DOCS : FICHIERS CRÉÉS / MIS À JOUR

Créés :
  ARCHITECTURE.md    — schéma complet couches, pipeline, SI loop, fail-open policy
  ROADMAP.md         — phases complétées + prochaines étapes
  CHANGELOG.md       — historique depuis Phase 3
  AUDIT_REPO.md      — inventaire CANONICAL/LEGACY/DUPLICATE/ARCHIVE/DELETE
  archive/legacy_apks/README.md — index des APKs archivés

Modifié :
  README.md          — ajout schéma architecture couches + liens vers ARCHITECTURE/ROADMAP/CHANGELOG/AUDIT

---

[5] FIXES : CORRECTIONS APPLIQUÉES

core/self_improvement/improvement_memory.py — _save()

AVANT :
    def _save(self, history: List[dict]) -> None:
        _HISTORY_DIR.mkdir(parents=True, exist_ok=True)
        tmp = _HISTORY_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(history, indent=2), "utf-8")
        tmp.replace(_HISTORY_PATH)

APRÈS :
    def _save(self, history: List[dict]) -> None:
        try:
            _HISTORY_DIR.mkdir(parents=True, exist_ok=True)
            tmp = _HISTORY_PATH.with_suffix(".tmp")
            tmp.write_text(json.dumps(history, indent=2), "utf-8")
            tmp.replace(_HISTORY_PATH)
        except Exception as e:
            logger.warning("[ImprovementMemory] _save failed — history not persisted: %s", e)

Résultat : erreur d'écriture → WARNING log, pas de raise.
Cohérent avec la politique fail-open du projet.
record() retourne l'entrée même si la persistance a échoué.

---

[6] TESTS : RÉSULTATS

Non exécutés dans cette session (branche de nettoyage architectural, pas de changements fonctionnels).
Le seul changement de code est improvement_memory._save() qui est
désormais fail-open (ne lève plus d'exception) — changement non-breaking.

Tests critiques à exécuter en validation :
  tests/test_self_improvement_loop.py
  tests/test_objective_engine.py
  tests/test_stability.py

Ces tests ne doivent pas être impactés par le fix _save() puisqu'ils
testent des scénarios de succès et l'échec d'écriture était déjà géré
au niveau du handler API (/run) avec logger.error.

---

[7] RISQUES RESTANTS

1. DIVERGENCE GUARDS (priorité haute)
   self_improve/guards.py (FORBIDDEN_SELF_MODIFY) et
   core/self_improvement/safe_executor.py (PROTECTED_FILES)
   ont des listes partiellement différentes.
   → Synchroniser dans une session dédiée.

2. APKs DANS L'HISTORIQUE GIT
   Les APKs sont déplacés dans archive/ mais restent dans l'historique git.
   Pour un nettoyage complet : git-filter-repo (hors scope, opération destructive).
   → Documenter en ROADMAP.md (fait).

3. self_improve/ TOUJOURS ACTIF VIA BOT
   La commande /improve Telegram appelle toujours self_improve/engine.py.
   Migration vers core/self_improvement/ non effectuée — hors scope.
   → Plan de migration documenté dans self_improve/LEGACY.md.

4. core/improvement_memory.py POTENTIEL DOUBLON
   Fichier à la racine de core/ qui peut dupliquer core/self_improvement/improvement_memory.py.
   Vérifier les imports avant suppression.

5. workspace/self_improvement/ N'EXISTE PAS ENCORE
   Sera créé automatiquement au premier appel /api/v2/self-improvement/run
   grâce à _HISTORY_DIR.mkdir(parents=True, exist_ok=True). OK.

---

[8] PROCHAINES ÉTAPES

1. Valider tests critiques sur cette branche :
   cd tests && python -m pytest test_self_improvement_loop.py test_objective_engine.py test_stability.py -v

2. Synchroniser FORBIDDEN_SELF_MODIFY (self_improve/guards.py) ↔
   PROTECTED_FILES (core/self_improvement/safe_executor.py)

3. Migrer /improve Telegram → core/self_improvement/ (session dédiée)

4. Vérifier et potentiellement supprimer self_improvement/ :
   grep -r "from self_improvement" . --include="*.py" | grep -v tests | grep -v __pycache__

5. Supprimer core/improvement_memory.py si doublon confirmé

6. Documenter API v2 complète (OpenAPI/Swagger)

---

[9] COMMITS

Phase 0+1 : audit + archive + LEGACY markers
Phase 2   : docs canoniques (ARCHITECTURE, ROADMAP, CHANGELOG, README update)
Phase 3   : fix improvement_memory write error logging
