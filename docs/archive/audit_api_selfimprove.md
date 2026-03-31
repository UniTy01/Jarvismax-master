# Audit API / Self-Improve / Night-Worker / Business
Date : 2026-03-19
Auditeur : Claude Sonnet 4.6 (senior Python engineer)

---

## Synthèse exécutive

| Couche | Statut global | Corrections appliquées |
|--------|--------------|------------------------|
| api/control_api.py | OK | — (déjà conforme) |
| api/main.py | ⚠️ Legacy en parallèle | Note clarifiée ici |
| api/ws.py | OK | — |
| api/__init__.py | OK | — |
| start_api.py | OK | — |
| self_improve/* | OK | — |
| night_worker/scheduler.py | OK | — |
| night_worker/worker.py | ⚠️ | datetime.utcnow() corrigé |
| scheduler/night_scheduler.py | ⚠️ doublon distinct | Rôle clarifié |
| business/layer.py | OK | — |
| business/business_knowledge.py | OK | — |

---

## api/__init__.py
- STATUT: OK
- Rôle: Marqueur de package Python, aucune logique.
- Problèmes: Aucun.
- Corrections appliquées: Aucune.

---

## api/control_api.py
- STATUT: OK
- Rôle: API HTTP principale (stdlib pure, HTTPServer) — API v1 utilisée par start_api.py.
- Analyse des routes :
  - `GET /api/stats` : PRESENT. Retourne `{"ok": true, "data": {...}}` avec les champs
    `missions.total/done/approved/pending_validation/rejected`, `actions.total/executed/pending/approved/failed`,
    `executor.running/executed_total/cycles`, plus `vault`, `goals`, `night_worker`. Structure conforme au cahier
    des charges et même plus riche que le minimum demandé.
  - `GET /api/missions` : PRESENT. Retourne liste + stats via `ms.stats()`.
  - `POST /api/missions/repair` : PRESENT (handler `post_missions_repair`, route ligne 111).
  - Gestion des erreurs : try/except systématique, status codes corrects (404 sur ressource manquante, 500 sur
    erreur interne, 400 sur erreur métier), helper `_err(msg, status)` cohérent.
  - CORS : `Access-Control-Allow-Origin: *` sur chaque réponse.
- Problèmes résiduels :
  - Pas de handler OPTIONS (preflight CORS pour les navigateurs modernes). Non-bloquant car l'app cible est
    Flutter/Android, pas un navigateur.
  - `_read_body()` pour GET /api/actions lit le body — comportement non standard (GET avec body). Fonctionnel
    mais peut poser problème avec des reverse-proxies stricts.
- Corrections appliquées: Aucune (fichier déjà propre).
- Compilation: OK (`python -m py_compile api/control_api.py` → exit 0).

---

## api/main.py
- STATUT: ⚠️ — Version alternative FastAPI (non utilisée par start_api.py)
- Rôle: API v2 FastAPI async avec routes `/api/v2/*` + alias de rétrocompatibilité `/api/*`.
- Relation avec control_api.py : `start_api.py` importe **uniquement** `api.control_api.ControlAPI` — `api/main.py`
  n'est PAS chargé au démarrage normal. C'est une évolution future, pas un doublon actif.
- `GET /api/stats` dans main.py (ligne 410–413) : c'est un alias vers `get_metrics()`, qui retourne les stats
  missions uniquement. Structure différente de control_api.py — incohérence si les deux API tournent en parallèle.
- Problèmes :
  - `_get_orchestrator()` instancie un nouveau `JarvisOrchestrator` à chaque requête POST — pas de singleton.
  - `_get_monitoring_agent()` a un double fallback sans settings (ligne 122–123) qui peut instancier sans paramètres
    requis.
  - Dépendances externes : nécessite `fastapi`, `pydantic`, `uvicorn` (absents de stdlib).
- Corrections appliquées: Aucune — fichier non utilisé en production. Marquer comme "work-in-progress v2".
- Recommandation : ajouter en tête de fichier un commentaire `# STATUS: WIP — non chargé par start_api.py`.

---

## api/ws.py
- STATUT: OK
- Rôle: Endpoints WebSocket v3 pour streaming d'événements mission en temps réel (FastAPI APIRouter).
- Chargé conditionnellement par main.py (try/except ImportError) — non actif dans l'API stdlib.
- Problèmes :
  - `ACTIVE_STREAMS` est un dict global en mémoire — pas de TTL, fuite mémoire possible si les streams ne sont
    jamais désenregistrés.
  - `register_stream()` est défini mais n'a pas d'équivalent `unregister_stream()` (le nettoyage dépend de la
    déconnexion WebSocket dans `finally`).
- Corrections appliquées: Aucune (hors scope de la correction critique).

---

## start_api.py
- STATUT: OK
- Rôle: Point d'entrée principal. Lance `api.control_api.ControlAPI` sur le port 7070.
  Exécute aussi `repair_approved_missions()` et démarre `ActionExecutor` en arrière-plan avant le serveur.
- Problèmes :
  - L'IP Tailscale (`100.109.1.124`) est hardcodée ligne 36 — mineur, cosmétique.
  - Pas de `--help` CLI (la demande d'audit le mentionne) — acceptable pour un lanceur simple.
- Corrections appliquées: Aucune.

---

## self_improve/__init__.py
- STATUT: OK
- Rôle: Marqueur de package vide.
- Problèmes: Aucun.

---

## self_improve/guards.py
- STATUT: OK
- Rôle: Source unique des listes de protection (FORBIDDEN_SELF_MODIFY, SENSITIVE_FILES) et helpers
  `is_forbidden()`, `is_sensitive()`, `resolve_targets()`, `check_patch_against_failure_memory()`.
- Analyse de sécurité :
  - `FORBIDDEN_SELF_MODIFY` couvre bien : .env, config/settings.py, risk/engine.py, core/execution_guard.py,
    jarvis_bot/bot.py, self_improve/engine.py, self_improve/pipeline.py, self_improve/guards.py lui-même.
  - `is_forbidden()` utilise trois modes de comparaison (exact, endswith("/f"), endswith(f)) — couvre les
    chemins relatifs et absolus.
  - `check_patch_against_failure_memory()` est fail-open (retourne True si MemoryBus indisponible) — acceptable
    car c'est une couche optionnelle sur un garde déjà multicouche.
- Trous identifiés :
  - `api/control_api.py` n'est pas dans FORBIDDEN. Jarvis pourrait s'auto-modifier l'API principale. À envisager.
  - `start_api.py` non protégé — idem.
  - Les chemins Windows (backslash) ne sont pas gérés dans `is_forbidden()` (utilise `endswith("/" + f)`).
    Sur Windows, un chemin comme `self_improve\guards.py` ne serait pas reconnu comme interdit.
- Corrections appliquées: Aucune (trous notés pour suivi, non critiques sur l'environnement cible Linux).

---

## self_improve/models.py
- STATUT: OK
- Rôle: Types de données partagés du pipeline (PatchSpec, AuditFinding, AuditReport, ImprovePipelineRun, etc.).
- Problèmes:
  - `ImprovePipelineRun` n'a pas de méthode `patches_pending_human()` documentée dans `__init__` — présente
    (ligne 204) mais pas exposée publiquement par engine.py.
- Corrections appliquées: Aucune.

---

## self_improve/auditor.py
- STATUT: OK
- Rôle: Analyse statique + LLM du code source. LECTURE SEULE. Produit un AuditReport.
- Problèmes :
  - Regex pattern pour les secrets (ligne 364) utilise `["\'\']` (deux apostrophes en séquence) au lieu de
    `["\'"]` — probablement une coquille de guillemets triplés mais fonctionne.
  - `MAX_FILES_LLM = 12` avec `half = MAX_FILES_LLM // 2 = 6` → 2 batches de 6 fichiers. Correct.
- Corrections appliquées: Aucune.

---

## self_improve/patch_builder.py
- STATUT: OK
- Rôle: Génère des PatchSpec depuis AuditFindings via LLM. Ne les applique jamais.
- Points forts : 4 fallbacks fuzzy-match pour old_str, validation AST Python, FailureMemory, normalisation chemins.
- Problèmes :
  - `_repair_json()` remplace les guillemets simples par des doubles de manière naïve (ligne 795) — casse les
    contractions françaises dans les strings (ex: `"c'est"` → `"c"est"`). Impact limité car appliqué uniquement
    comme dernier recours.
- Corrections appliquées: Aucune.

---

## self_improve/pipeline.py
- STATUT: OK
- Rôle: Orchestre les étapes 1-5 du pipeline (pré-validation humaine) + étape 6 (apply) + rollback.
- Points forts : backup obligatoire, ExecutionGuard post-apply, journalisation systématique, sandbox isolation.
- Problèmes :
  - `run_tests()` (étape 7) appelle `python3` explicitement (ligne 583) — non portable sur Windows.
    `start_api.py` tourne sur Windows (start_api.py ligne 37 mentionne Android/emulateur).
- Corrections appliquées: Aucune (trou noté).

---

## self_improve/engine.py (SelfImproveEngine)
- STATUT: OK
- Rôle: Façade principale. Délègue à ImproveDirector (enrichi) avec fallback ImprovePipeline.
- Problèmes :
  - `format_validation_card()` accède directement à `patch.old_str` sans vérification de longueur (ligne 143) —
    sécurisé par le `[:120]` slice mais aurait pu lever IndexError si old_str était None.
    (old_str est toujours str="" par défaut dans PatchSpec — pas de bug réel.)
- Corrections appliquées: Aucune.

---

## self_improve/sandbox.py
- STATUT: OK
- Rôle: Espace de travail isolé par session. Copie des fichiers, application locale des patches, génération de diffs.
- Problèmes :
  - `SANDBOXES_ROOT = Path("workspace/sandboxes")` est un chemin relatif (ligne 46). Si le CWD change,
    la sandbox serait créée au mauvais endroit. En pratique, `jarvis_root` est passé au constructeur et
    `sandbox_dir = jarvis_root / SANDBOXES_ROOT / session_id` — donc absolu. OK.
- Corrections appliquées: Aucune.

---

## self_improve/improve_director.py
- STATUT: OK
- Rôle: Orchestrateur renforcé du pipeline (TestRunner + RetryLoop + EscalationRouter).
- Problèmes :
  - `_step2_plan()` mutate `drun.audit_report.findings = []` (ligne 309) pour arrêter les étapes suivantes.
    Mutation d'un objet partagé — acceptable ici car drun est local à la run.
  - `_step6_retry()` limite à 2 patches retryables (`retryable[:2]`) sans le documenter dans la docstring.
- Corrections appliquées: Aucune.

---

## night_worker/__init__.py
- STATUT: OK
- Rôle: Marqueur de package vide.

---

## night_worker/scheduler.py
- STATUT: OK
- Rôle: NightScheduler threading simple — cycle de learning + consolidation vault toutes les 6h.
  Utilisé par `api/control_api.py` via `_get_night_scheduler()`.
- Problèmes :
  - `datetime.now().isoformat()` ligne 183 sans timezone — naïf. Mineur (timestamp de nom de fichier).
- Corrections appliquées: Aucune (non-critique, dans `_save_report` uniquement).

---

## night_worker/worker.py
- STATUT: ⚠️ → CORRIGE
- Rôle: NightWorkerEngine — moteur de cycles autonomes LLM multi-cycles.
- Problèmes détectés :
  1. `datetime.utcnow()` deprecation Python 3.12 (ligne 55, dans `CycleResult.ts`).
  2. `datetime` importé sans `timezone` (ligne 13).
- Corrections appliquées :
  1. Import corrigé : `from datetime import datetime, timezone`
  2. `datetime.utcnow().isoformat()` → `datetime.now(timezone.utc).isoformat()`

---

## scheduler/night_scheduler.py
- STATUT: ⚠️ — COMPOSANT DISTINCT (pas un doublon de night_worker/scheduler.py)
- Rôle: NightScheduler asyncio avec tâches cron/interval/once, intégration self_improve et workflows.
  C'est le planificateur de tâches récurrentes *applicatives* (lancer /improve à 02:00, exécuter un workflow, etc.).
  Il est **différent** de `night_worker/scheduler.py` qui est le moteur de learning/vault nocturne.
- Relation :
  - `night_worker/scheduler.py` = consolidation de données (learning loop, vault prune), démarré en background thread.
  - `scheduler/night_scheduler.py` = ordonnanceur de tâches (cron-like), boucle asyncio, non démarré par start_api.py.
- Problèmes :
  - Non chargé par `start_api.py` — à intégrer si les tâches planifiées sont désirées.
  - `_action_self_improve()` instancie `ActionExecutor` et `RiskEngine` sans les passer en paramètres — crée des
    instances orphelines non liées aux singletons de l'application.
- Corrections appliquées: Aucune — rôle documenté ici pour lever l'ambiguïté.
- Recommandation : ajouter en tête du fichier un commentaire distinguant les deux schedulers.

---

## business/layer.py
- STATUT: OK
- Rôle: Façade des 6 modules business (VentureBuilder, OfferDesigner, WorkflowArchitect, SaasBuilder,
  TradeOps, MetaBuilder). Détection d'intent par mots-clés.
- Problèmes :
  - `detect_intent()` retourne "venture" par défaut si aucun mot-clé ne match — acceptable mais peut
    router incorrectement des demandes ambiguës.
  - `_get_agent()` n'a pas de gestion d'erreur ImportError autour des imports de sous-modules.
    Si un module business manque, `KeyError` dans `self._agents.get(module)` → retourne None → log.error.
    Comportement correct mais silencieux.
- Corrections appliquées: Aucune.

---

## business/business_knowledge.py
- STATUT: OK
- Rôle: Base de connaissances business avec signaux scorés par catégorie. Pattern singleton.
- Problèmes :
  - `score_idea()` utilise une heuristique de matching mots-clés très approximative (≥2 mots en commun OU
    présence de mots-clés hardcodés comme "chauffag", "artisan", etc.) — adapté pour usage LLM-assisté,
    moins fiable seul.
- Corrections appliquées: Aucune.

---

## Résumé des corrections appliquées

| Fichier | Correction | Type |
|---------|-----------|------|
| `night_worker/worker.py` | `datetime.utcnow()` → `datetime.now(timezone.utc)` | deprecation fix |
| `night_worker/worker.py` | Import `timezone` ajouté | import fix |

---

## Points d'action recommandés (non appliqués — hors scope critique)

1. **api/main.py** : Ajouter `# STATUS: WIP — non chargé par start_api.py` en tête pour éviter la confusion.
2. **self_improve/guards.py** : Ajouter `api/control_api.py` et `start_api.py` à `FORBIDDEN_SELF_MODIFY`
   pour empêcher l'auto-modification de la couche API.
3. **self_improve/guards.py** : Normaliser les backslashes Windows dans `is_forbidden()` :
   `file_path.replace("\\", "/")` avant comparaison.
4. **self_improve/pipeline.py** : Remplacer `python3` par `sys.executable` dans `run_tests()` pour
   portabilité Windows.
5. **night_worker/scheduler.py** : Corriger `datetime.now().isoformat()` → `datetime.now(timezone.utc).isoformat()`
   dans `_save_report()` (déjà `from datetime import datetime, timezone`).
6. **scheduler/night_scheduler.py** : Connecter au singleton de l'application dans `_action_self_improve()`.
7. **api/ws.py** : Ajouter un TTL ou `unregister_stream()` pour éviter la fuite mémoire de `ACTIVE_STREAMS`.

---

## Compilation finale

```
python -m py_compile api/control_api.py  → OK (vérifié)
night_worker/worker.py                    → OK (corrigé)
```
