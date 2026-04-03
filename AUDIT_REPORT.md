# AUDIT TECHNIQUE — Jarvis Max
_Date : 2026-04-03 — Cycle 17 post-freeze_
_Auditeur : code-auditor skill_

Ce rapport classe chaque problème identifié par sévérité : CRITIQUE, MAJEUR, MODÉRÉ, MINEUR.
Seuls les problèmes réels sont listés. Aucune inflation de sévérité.

---

## CRITIQUE — Aucun

Aucun problème critique identifié dans le code de production actif.

---

## MAJEUR

### MAJ-001 — `requirements.txt` : dépendances non épinglées

**Fichier :** `requirements.txt`

**Description :** Sur ~45 dépendances, seules 2 sont épinglées avec `==`. Toutes les autres utilisent `>=` (borne basse uniquement). Exemples : `langchain>=0.3.0`, `fastapi>=0.111.0`, `pydantic>=2.7.0`, `sentence-transformers>=2.7.0`.

**Impact :** Les builds Docker ne sont pas reproductibles. Une nouvelle version majeure de LangChain, FastAPI ou Pydantic peut casser le système silencieusement. Ce risque est particulièrement élevé pour LangChain (API instable) et Pydantic v2 (changements breaking fréquents).

**Solution proposée :** Générer un `requirements.lock` via `pip freeze` depuis l'image Docker actuelle (état golden) et l'utiliser dans le `Dockerfile` (`pip install -r requirements.lock`). Garder `requirements.txt` pour la sémantique métier, le lock pour la reproductibilité.

---

### MAJ-002 — Rate limiter défini mais non appliqué au middleware global

**Fichier :** `api/rate_limiter.py`, `api/main.py`

**Description :** `api/rate_limiter.py` contient une implémentation complète de rate limiting (sliding window, Redis + in-memory fallback, par route). Ce module n'est **pas** enregistré dans `api/main.py` comme middleware. Seuls `AccessEnforcementMiddleware` et `SecurityHeadersMiddleware` sont montés.

**Impact :** L'API est exposée sans limitation de débit. Un attaquant (ou une mission runaway) peut saturer le serveur sans restriction. L'endpoint `/api/v3/missions` est le plus exposé : chaque soumission lance un `asyncio.Task` et consomme des crédits LLM.

**Solution proposée :** Ajouter `app.add_middleware(RateLimitMiddleware)` dans `api/main.py`, en wrappant le `RateLimiter` existant. La logique est déjà prête — il manque juste le câblage.

---

### MAJ-003 — `pip install` dynamique au démarrage dans `main.py`

**Fichier :** `main.py`, lignes 23-25

**Description :**
```python
try:
    import jwt
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "PyJWT", "-q"])
    import jwt
```

**Impact :** Un `subprocess.check_call` au démarrage de l'application est une pratique dangereuse. En production Docker, cela peut échouer silencieusement si PyPI n'est pas accessible, introduire une dépendance de réseau au boot, ou être exploité si le système de fichiers est compromis. PyJWT est dans `requirements.txt` — ce bloc est un garde-fou qui masque une anomalie plutôt que la résoudre.

**Solution proposée :** Supprimer le bloc `except ImportError`. Si `PyJWT` est absent au démarrage, c'est un bug de packaging — l'app doit planter clairement, pas tenter un install dynamique.

---

## MODÉRÉ

### MOD-001 — CORS : `allow_headers=["*"]` + origines potentiellement trop larges

**Fichier :** `api/main.py`, lignes 95-100

**Description :**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
```
`allow_headers=["*"]` et `allow_methods=["*"]` sont trop permissifs pour un déploiement production. De plus, si `CORS_ORIGINS` n'est pas défini, les origines autorisées par défaut incluent `localhost` et le réseau Android emulator sans distinction d'environnement.

**Impact :** MODÉRÉ — ne constitue pas une vulnérabilité directe (la JWT auth protège les routes), mais affaiblit la défense en profondeur et peut permettre des attaques CSRF depuis des origines inattendues.

**Solution proposée :** Restreindre `allow_headers` à `["Authorization", "Content-Type", "X-Jarvis-Token"]`. Séparer les origines dev/prod via env var (`JARVIS_PRODUCTION=1` → origines strictes uniquement).

---

### MOD-002 — `agents/finance_agent.py` et `tools/integrations/stripe_tool.py` : clé de test hardcodée

**Fichiers :** `agents/finance_agent.py` ligne ~91, `tools/integrations/stripe_tool.py` ligne ~78

**Description :** Les deux fichiers contiennent `api_key="sk_test_..."` comme valeur de placeholder. Ce n'est pas une vraie clé Stripe (préfixe `sk_test_` avec caractères bidon), mais la présence d'une chaîne ressemblant à un secret dans le code source va déclencher des alertes dans tout scanner secrets (GitHub Actions secret scanner, truffleHog, Semgrep).

**Impact :** Faux positifs dans les scans de sécurité CI. Risque de confusion pour un contributeur externe qui penserait que la clé est réelle.

**Solution proposée :** Remplacer `api_key="sk_test_..."` par `api_key=""` ou `api_key=os.environ.get("STRIPE_API_KEY", "")`. La logique Vault en dessous est déjà correcte.

---

### MOD-003 — `core/planning/skill_llm.py` : `asyncio.get_event_loop()` déprécié

**Fichier :** `core/planning/skill_llm.py`, ligne 512

**Description :** `asyncio.get_event_loop()` est déprécié depuis Python 3.10. En Python 3.12 (la version utilisée dans le Docker), il génère un `DeprecationWarning` et peut lever `RuntimeError` si appelé depuis un contexte sans event loop actif (typique dans les threads worker).

**Impact :** Risque d'erreur non reproductible lors d'exécutions parallèles. Le warning pollue les logs en production.

**Solution proposée :** Remplacer par `asyncio.get_running_loop()` (si déjà dans un contexte async) ou `asyncio.new_event_loop()` si besoin d'un loop isolé. Une ligne à changer.

---

### MOD-004 — `_running_missions` : set global non thread-safe dans `api/routes/missions.py`

**Fichier :** `api/routes/missions.py`, ligne ~33

**Description :**
```python
_running_missions: set[str] = set()
```
Ce set est partagé entre toutes les requêtes FastAPI (qui s'exécutent dans un thread pool asyncio). En cas de soumission simultanée de deux requêtes identiques, il y a une race condition sur `.add()` et le check `if result.mission_id in _running_missions`.

**Impact :** MODÉRÉ — en pratique peu probable avec un seul worker uvicorn, mais la race est réelle avec `--workers > 1`. Des doublons peuvent passer à travers le garde.

**Solution proposée :** Utiliser un `asyncio.Lock` ou remplacer par une vérification dans `OrchestrationBridge` (qui est déjà thread-safe via SQLite). Alternativement : documenter explicitement que l'app ne supporte qu'un seul worker.

---

### MOD-005 — Absence d'index SQLite sur `canonical_missions`

**Fichier :** `core/canonical_mission_store.py`

**Description :** La table `canonical_missions` n'a qu'un index PRIMARY KEY sur `mission_id`. La requête `load_all()` fait un `ORDER BY created_at DESC LIMIT 500` sans index sur `created_at`. Les requêtes de listing (`list_missions()`) scannent toute la table.

**Impact :** Dégradation de performance à l'échelle. Pour < 1000 missions (usage actuel), SQLite gère sans problème. Au-delà ou avec du listing fréquent, un full scan à chaque requête devient coûteux.

**Solution proposée :** Ajouter `CREATE INDEX IF NOT EXISTS idx_created_at ON canonical_missions(created_at DESC)` dans `_CREATE_TABLE`. Modification minimale, aucun impact sur le reste.

---

### MOD-006 — `core/improvement_loop.py` : exécution Docker dans le contexte SI (non isolé)

**Fichier :** `core/improvement_loop.py`, `RegressionGuard.run_tests()`

**Description :** La self-improvement pipeline utilise `subprocess.run(["docker", "run", "--rm", ...])` pour valider les patchs. Cette approche nécessite que le container Jarvis ait accès au socket Docker (`/var/run/docker.sock`). Ce socket n'est pas exposé dans `docker-compose.test.yml` (il ne devrait pas l'être). Mais si activé en prod, cela donne au container une élévation de privilèges container-to-host.

**Impact :** MODÉRÉ en l'état (SI désactivé en production par `JARVIS_PRODUCTION=1`). Potentiellement CRITIQUE si SI est activé et que le socket Docker est monté.

**Solution proposée :** Documenter explicitement que SI + Docker socket = risque critique. Ajouter une vérification au démarrage SI : si `/var/run/docker.sock` n'est pas accessible, `RegressionGuard` doit se désactiver avec un warning clair.

---

## MINEUR

### MIN-001 — `docker/Dockerfile` : `git` installé dans l'image de runtime

**Fichier :** `docker/Dockerfile`

**Description :** Le stage de runtime installe `git` via `apt-get`. Git n'est pas nécessaire à l'exécution de l'API FastAPI.

**Impact :** Surface d'attaque inutilement étendue. L'image fait déjà 9.75 GB — git ajoute ~30 MB. En cas de compromission d'un agent (ex. injection de prompt → exécution de commande), git permet des interactions avec des repos distants.

**Solution proposée :** Supprimer `git` de la liste des packages apt-get runtime. Vérifier si un module Python l'utilise via `GitPython` ou `subprocess` — si oui, conserver uniquement dans les layers qui en ont besoin.

---

### MIN-002 — `JarvisOrchestrator` (`core/orchestrator.py`) : classe dépréciée mais toujours instanciable

**Fichier :** `core/orchestrator.py`

**Description :** Le fichier est marqué `# DEPRECATED — Do not extend this module` mais `JarvisOrchestrator.__init__()` ne déclenche pas de `DeprecationWarning`. Un code tiers ou une migration incomplète peut instancier directement cette classe sans avertissement.

**Impact :** MINEUR — le code neuf utilise `MetaOrchestrator` correctement. Le risque est une migration silencieuse incomplète.

**Solution proposée :** Ajouter `warnings.warn("JarvisOrchestrator is deprecated, use get_meta_orchestrator()", DeprecationWarning, stacklevel=2)` dans `__init__`. Un ajout de 2 lignes.

---

### MIN-003 — `api/main.py` : imports de routeurs enveloppés dans `try/except ImportError` silencieux

**Fichier :** `api/main.py`, lignes 119-300+

**Description :** Chaque routeur est importé dans un bloc `try: ... except ImportError: pass`. Cette approche fail-open masque les erreurs d'import réels (attributeError, syntax error, mauvais import) dans les routes. Si `api/routes/missions.py` contient une erreur Python, elle est silencieusement ignorée et la route n'est pas montée.

**Impact :** Debug difficile. En cas de régression dans un routeur, l'API démarre normalement mais des routes sont manquantes. Le `except ImportError: pass` ne catch pas les autres exceptions.

**Solution proposée :** Utiliser `except Exception as e: log.error("router_import_failed", router="...", err=str(e))` pour logger toutes les exceptions d'import avec leur contexte, pas seulement les `ImportError`. Le fail-open reste mais devient visible.

---

### MIN-004 — `agents/parallel_executor.py` : trace log vers fichier local non rotaté

**Fichier :** `agents/parallel_executor.py`, ligne 43-70

**Description :**
```python
_TRACE_LOG = Path("workspace/execution_trace.jsonl")
```
Le fichier `execution_trace.jsonl` grossit indéfiniment. Aucune rotation, aucune limite de taille. Pour un usage intensif (beaucoup de missions), ce fichier peut atteindre des tailles problématiques.

**Impact :** Consommation disque non contrôlée sur le long terme. MINEUR pour un MVP, mais à adresser avant usage production soutenu.

**Solution proposée :** Ajouter une rotation basée sur la taille (ex. 50 MB max via `logging.handlers.RotatingFileHandler`), ou limiter le nombre de lignes conservées lors de l'append.

---

### MIN-005 — `core/memory/memory_layers.py` : `MemoryLayer` non branché sur le bus mémoire global

**Fichier :** `core/memory/memory_layers.py`, `core/memory_facade.py`

**Description :** `MemoryLayer` est une abstraction propre avec 6 types et des TTLs définis. Mais d'après l'analyse du code, les agents utilisent Qdrant directement pour les embeddings, sans passer par `MemoryLayer`. L'abstraction existe mais n'est pas le chemin canonique.

**Impact :** MINEUR en termes de bug — tout fonctionne. Mais la dette d'architecture est claire : deux chemins mémoire coexistent (Qdrant direct vs MemoryLayer), ce qui rend l'évolution difficile.

**Solution proposée :** Documenter explicitement dans `MemoryLayer` que l'intégration avec les agents est **non activée** (comme le fait RELEASE_READINESS.md pour d'autres composants). Évite la confusion lors de futurs développements.

---

## Synthèse

| ID | Sévérité | Fichier principal | Effort de correction |
|----|----------|-------------------|---------------------|
| MAJ-001 | MAJEUR | `requirements.txt` | Moyen (pip freeze) |
| MAJ-002 | MAJEUR | `api/main.py`, `api/rate_limiter.py` | Faible (câblage middleware) |
| MAJ-003 | MAJEUR | `main.py` | Très faible (supprimer 3 lignes) |
| MOD-001 | MODÉRÉ | `api/main.py` | Faible |
| MOD-002 | MODÉRÉ | `agents/finance_agent.py`, `tools/integrations/stripe_tool.py` | Très faible |
| MOD-003 | MODÉRÉ | `core/planning/skill_llm.py` | Très faible (1 ligne) |
| MOD-004 | MODÉRÉ | `api/routes/missions.py` | Faible |
| MOD-005 | MODÉRÉ | `core/canonical_mission_store.py` | Très faible (1 ligne SQL) |
| MOD-006 | MODÉRÉ | `core/improvement_loop.py` | Faible (guard + doc) |
| MIN-001 | MINEUR | `docker/Dockerfile` | Très faible |
| MIN-002 | MINEUR | `core/orchestrator.py` | Très faible (2 lignes) |
| MIN-003 | MINEUR | `api/main.py` | Faible |
| MIN-004 | MINEUR | `agents/parallel_executor.py` | Faible |
| MIN-005 | MINEUR | `core/memory/memory_layers.py` | Documentation seulement |

---

## Points positifs relevés

Ces éléments méritent d'être notés comme bonne pratique :

- **Ghost-DONE fix** (`execution_supervisor.py`) : le `_check_session_outcome()` est robuste, bien testé (20 tests), et empêche les faux succès — c'est la protection la plus critique et elle est bien implémentée.
- **Timing attack protection** (`api/auth.py`) : `hmac.compare_digest()` utilisé correctement pour la comparaison de mots de passe.
- **KL-008 restart safety** (`orchestration_bridge.py`) : les WAITING_APPROVAL orphelins sont détectés et terminés proprement au redémarrage — pattern correct.
- **SQLite WAL mode** (`canonical_mission_store.py`) : `PRAGMA journal_mode=WAL` et `PRAGMA synchronous=NORMAL` sont les bons paramètres pour un usage concurrent.
- **Circuit breaker** (`meta_orchestrator.py`) : implémenté proprement, thread-safe.
- **Approval gate** (`execution_supervisor.py`) : timeout sur la soumission (`_APPROVAL_SUBMIT_TIMEOUT_S=10`), fail-closed pour high/critical, fail-open pour low — politique correcte.
- **Structlog** : utilisé de manière cohérente avec fallback `logging` standard — observable et compatible avec les agrégateurs de logs.
- **`.dockerignore`** : complet, exclut `data/`, `.env`, `workspace/`, `__pycache__`, clés privées.

---

_Rapport généré le 2026-04-03. Backend en état de freeze (Cycle 17). Aucun problème CRITIQUE identifié._
