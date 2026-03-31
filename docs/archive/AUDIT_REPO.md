# AUDIT_REPO.md — Jarvis Max
**Date :** 2026-03-25
**Branche :** claude/mystifying-tharp (→ sera mergée via claude/architecture-cleanup)
**Auteur :** Claude Code — Phase 0 audit strict lecture seule

---

## RÉSUMÉ EXÉCUTIF

Le dépôt est **fonctionnel et stable** (262 tests, Phase 5 active). Trois problèmes structurels principaux :
1. **14 APKs à la racine** (~900 MB de binaires non archivés)
2. **Trois modules self-improvement coexistants** sans marquage clair de la source canonique
3. **Absence de docs canoniques** (ARCHITECTURE.md, ROADMAP.md, CHANGELOG.md inexistants)

---

## INVENTAIRE PAR STATUT

### KEEP_AS_CANONICAL — Sources de vérité actives

| Fichier / Module | Rôle |
|---|---|
| `core/meta_orchestrator.py` | Façade unique d'entrée des missions — NE PAS MODIFIER |
| `core/orchestrator.py` | Logique métier historique (rétrocompat) — NE PAS MODIFIER |
| `core/orchestrator_v2.py` | Budget/DAG missions complexes — NE PAS MODIFIER |
| `core/self_improvement/` | **Boucle SI V1 canonique** (ajouté commit a8ac85b) |
| `core/self_improvement/__init__.py` | Anti-loop guards : MAX=1, COOLDOWN=24h, MAX_FAILURES=3 |
| `core/self_improvement/safe_executor.py` | Exécution atomic + rollback + PROTECTED_FILES |
| `core/self_improvement/improvement_memory.py` | Historique JSON dans workspace/self_improvement/ |
| `core/planner.py` | Planificateur avec injection self_improvement_context (fail-open) |
| `core/objectives/` | Objective Engine complet (ajouté commit bda142f) |
| `core/knowledge/` | Knowledge/Difficulty/Pattern layer |
| `executor/mission_result.py` | Résultat mission — NE PAS MODIFIER |
| `api/schemas.py` | Helpers ok()/error() — NE PAS MODIFIER |
| `api/routes/self_improvement.py` | Endpoints GET/POST /api/v2/self-improvement/* |
| `self_improve/guards.py` | **Source unique des règles FORBIDDEN_SELF_MODIFY** |
| `tests/` | 262 tests — suite complète |
| `README.md` | Documentation principale (à enrichir) |
| `docker-compose.yml` | Stack Docker officielle — NE PAS MODIFIER |
| `.env.example` | Template config |
| `jarvis.py` | CLI entry point |
| `main.py` | Entrée FastAPI |
| `start_api.py` | Démarrage API |
| `start_all.bat` | Démarrage principal Windows |
| `start_jarvis.bat` | Démarrage Jarvis Windows |
| `status_jarvis.bat` | Statut services Windows |
| `stop_jarvis.bat` | Arrêt services Windows |
| `PROMPT_DIRECTEUR_AGENT.md` | Prompt système orchestrateur (actif, utilisé en prod) |
| `scripts/` | install.sh, start.sh, deploy_check.sh |

---

### ACTIVE — Utilisé en production

| Module | Statut |
|---|---|
| `core/meta_orchestrator.py` | Façade canonique, point d'entrée unique |
| `core/orchestrator_v2.py` | Utilisé pour missions complexes avec budget/DAG |
| `core/objectives/` | Objective Engine — CRUD + breakdown + scoring |
| `core/knowledge/` | Difficulty estimator, pattern detector, capability scorer |
| `agents/crew.py` | 9 agents parallèles (Atlas, Scout, Map, Forge, Lens, Vault, Shadow, Pulse, Night) |
| `api/routes/` | 10+ endpoints FastAPI actifs |
| `executor/` | Exécution sécurisée avec retry + supervision |
| `jarvis_bot/` | Interface Telegram |
| `risk/` | Moteur risque LOW/MEDIUM/HIGH |
| `night_worker/` | Boucle nuit autonome |

---

### LEGACY — Plus canonique mais encore référencé

| Module | Raison legacy | Action |
|---|---|---|
| `self_improve/` | Système SI original, mature, encore référencé dans README et `/improve` Telegram | Marquer LEGACY, conserver guards.py comme référence |
| `self_improve/engine.py` | Toujours appelé par `/improve` Telegram bot | **Ne pas supprimer** — bridge vers V1 |
| `self_improve/guards.py` | **Source canonique** des FORBIDDEN_SELF_MODIFY — référencé par safe_executor.py | **GARDER comme source de vérité** |
| `self_improvement/` | Version intermédiaire (failure_collector, deployment_gate, patch_builder) — plus utilisée activement | Marquer LEGACY |
| `core/improvement_memory.py` | Duplique partiellement core/self_improvement/improvement_memory.py | Vérifier si encore importé |

---

### DUPLICATE — Doublon fonctionnel

| Fichier | Doublon de | Décision |
|---|---|---|
| `core/improvement_memory.py` | `core/self_improvement/improvement_memory.py` | Vérifier imports avant action |
| `self_improvement/patch_builder.py` | `self_improve/patch_builder.py` | self_improvement/ = LEGACY |
| `send_telegram.py` | `send_telegram_v5.py` (deux versions) | send_telegram_v5.py → archive |

---

### EXPERIMENTAL — En cours de dev

| Module | Note |
|---|---|
| `core/self_improvement/` | V1 opérationnel, testé, mais premier cycle réel non encore exécuté en prod |
| `adapters/` | Bridge OpenHands — intégration partielle |

---

### DELETE_CANDIDATE — Supprimable sans risque

| Fichier | Justification |
|---|---|
| `send_telegram_v5.py` | Remplacé par send_telegram.py, suffix _v5 = legacy |
| `test_openhands_bridge.py` | Test one-shot à la racine, devrait être dans tests/ |

---

### MOVE_TO_ARCHIVE — Conserver mais hors chemin principal

#### APKs à la racine (binaires, non versionner)

| Fichier | Action |
|---|---|
| `jarvismax-debug.apk` | → `archive/legacy_apks/` |
| `jarvismax-release.apk` | → `archive/legacy_apks/` |
| `jarvismax-stable.apk` | → `archive/legacy_apks/` |
| `jarvismax-v3-fixed.apk` | → `archive/legacy_apks/` |
| `jarvismax-v4-connection-fix.apk` | → `archive/legacy_apks/` |
| `jarvismax-v5-full-fix.apk` | → `archive/legacy_apks/` |
| `jarvismax-v6-mission-fixed.apk` | → `archive/legacy_apks/` (plus récent, garder accessible) |
| `jarvismax-vps-release.apk` | → `archive/legacy_apks/` (prod release) |

#### Scripts legacy

| Fichier | Action |
|---|---|
| `add_firewall_rule.bat` | → `archive/legacy_scripts/` (config firewall one-shot) |
| `build_v5.bat` | → `archive/legacy_scripts/` (build script v5 obsolète) |

---

## TROIS MODULES SELF-IMPROVEMENT : ANALYSE

```
self_improve/          ← LEGACY (système le plus mature, 16 fichiers)
│  guards.py           ← SOURCE CANONIQUE des règles FORBIDDEN (conserver)
│  engine.py           ← Encore appelé par /improve Telegram
│  pipeline.py         ← Pipeline complet (audit→patch→review→validate)
│  ...
│
self_improvement/      ← INTERMÉDIAIRE LEGACY (6 fichiers)
│  failure_collector.py
│  improvement_planner.py
│  patch_builder.py
│  validation_runner.py
│  deployment_gate.py
│
core/self_improvement/ ← CANONIQUE V1 (6 fichiers, commit a8ac85b)
   __init__.py         ← Anti-loop guards
   weakness_detector.py
   candidate_generator.py
   improvement_scorer.py
   safe_executor.py    ← PROTECTED_FILES hardcodées ici aussi
   improvement_memory.py
```

**Décision :**
- `core/self_improvement/` = canonique going forward
- `self_improve/guards.py` = source de vérité FORBIDDEN_SELF_MODIFY (à synchroniser avec safe_executor.py)
- `self_improve/` = LEGACY mais **ne pas supprimer** (encore utilisé par /improve bot)
- `self_improvement/` = LEGACY, plus référencé activement

---

## ORCHESTRATEUR CANONIQUE

- **MetaOrchestrator** (`core/meta_orchestrator.py`) = point d'entrée unique
- `core/orchestrator.py` = rétrocompatibilité (déprecié mais utilisable)
- `core/orchestrator_v2.py` = utilisé pour missions complexes via MetaOrchestrator

---

## CONTRATS CANONIQUES

- `api/schemas.py` = helpers ok()/error() — **CANONICAL**
- `core/contracts.py` = contrats internes agents
- `agents/contracts.py` = contrats agents

---

## FAIL-OPEN ANALYSIS — POINTS CRITIQUES

### ✅ Correct : fail-open sur lectures
- `_load_history()` dans `core/self_improvement/__init__.py` → retourne `[]` sur erreur (correct)
- Imports dans `api/routes/self_improvement.py` → `_SI_AVAILABLE = False` si import échoue (correct)

### ⚠️ PROBLÈME TROUVÉ : write silencieux dans improvement_memory._save()
```python
def _save(self, history: List[dict]) -> None:
    _HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    tmp = _HISTORY_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(history, indent=2), "utf-8")  # ← pas de try/except
    tmp.replace(_HISTORY_PATH)                               # ← pas de try/except local
```
Si `write_text` ou `replace` échoue, l'exception remonte à `record()` qui ne catch pas non plus,
puis remonte au appelant. **À corriger** : ajouter `try/except` + `logger.warning` dans `_save()`.

---

## DOCS MANQUANTES

| Fichier | Statut |
|---|---|
| `README.md` | Existe — à enrichir (architecture schema, liens) |
| `ARCHITECTURE.md` | **MANQUANT** — à créer |
| `ROADMAP.md` | **MANQUANT** — à créer |
| `CHANGELOG.md` | **MANQUANT** — à créer |
| `PROMPT_DIRECTEUR_AGENT.md` | Existe — garder en place (actif en prod) |

---

## RISQUES RESTANTS

1. **Divergence guards** : `self_improve/guards.py` (FORBIDDEN_SELF_MODIFY) et `core/self_improvement/safe_executor.py` (PROTECTED_FILES) ont des listes partiellement différentes. À synchroniser dans une session dédiée.

2. **core/improvement_memory.py** : fichier à la racine de core/ qui duplique partiellement `core/self_improvement/improvement_memory.py`. Vérifier les imports avant toute suppression.

3. **APKs en git** : les APKs sont trackés dans git — les déplacer dans archive/ réduit leur présence à la racine mais ils restent dans l'historique git. Pour un nettoyage complet, un `git filter-branch` ou `git-filter-repo` serait nécessaire (hors scope cette session).

4. **self_improve/** encore actif via bot Telegram `/improve` : ne pas supprimer ce module sans refactorer le bot.

5. **workspace/self_improvement/** n'existe pas encore : le premier appel à `/run` le créera automatiquement (mkdir parents=True). OK.
