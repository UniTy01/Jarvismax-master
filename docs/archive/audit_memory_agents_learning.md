# Rapport d'Audit — Memory / Agents / Learning
**Date** : 2026-03-19
**Auditeur** : Claude Sonnet 4.6 (senior Python engineer)
**Périmètre** : couches `memory/`, `agents/`, `learning/`
**Corrections mineures appliquées** : `asyncio.iscoroutinefunction` → `inspect.iscoroutinefunction` dans `parallel_executor.py` et `synthesizer_agent.py`

---

## COUCHE MEMORY

---

## memory/__init__.py
- **STATUT** : ✅ OK
- **Lignes** : 1 (fichier vide)
- **Problèmes** : aucun
- **Recommandations** : exposer les principaux symboles (`get_vault_memory`, `MemoryBus`, etc.) pour faciliter les imports dans les agents.

---

## memory/vault_memory.py
- **STATUT** : ⚠️ PROBLÈMES MINEURS
- **Lignes** : 537
- **Problèmes** :
  - [MINEUR] `_is_jaccard_dup()` itère sur tous les `_entries` en O(n) à chaque appel — appelée deux fois dans `store()` et une fois dans `is_known()`. Avec 2 000 entrées, la pénalité est perceptible à haute fréquence (ligne 409).
  - [MINEUR] `_evict_oldest()` ne recalcule pas `_fps` pour les entrées supprimées si leur fingerprint était partagé (line 419-423). Effet : les fingerprints d'entrées supprimées restent dans `_fps`, faussant la déduplication fingerprint.
  - [MINEUR] `get_by_type()` et `get_by_tag()` trient l'intégralité du dict avant de filtrer — devrait filtrer puis trier (line 330-346).
  - [INFO] Le singleton `_vault_instance` est module-level avec `global`, non thread-safe (ligne 529-536). Acceptable pour usage mono-thread asyncio, mais à documenter.
  - [INFO] Champ `last_used` est une string ISO dans `VaultEntry` mais `KnowledgeEntry.last_used` est un `float` — incohérence entre les deux mémoires.
- **Recommandations** :
  - Corriger `_evict_oldest` : appeler `self._fps.discard(entry.fingerprint)` avant `del` (déjà fait pour les autres cas).
  - Filtrer avant de trier dans `get_by_type`/`get_by_tag`.
  - Homogénéiser le type de `last_used` entre `VaultEntry` et `KnowledgeEntry`.

---

## memory/vector_memory.py
- **STATUT** : ⚠️ PROBLÈMES MINEURS
- **Lignes** : 285
- **Problèmes** :
  - [MINEUR] `_vec_to_b64()` utilise `struct.pack` au lieu de `numpy.ndarray.tobytes()` — plus lent et redondant avec l'import numpy déjà présent (ligne 112-114).
  - [MINEUR] `_encode()` peut retourner `None` ; dans `add()`, si `vec` est `None`, `vec_b64` est `""` — correct, mais pas documenté (ligne 164).
  - [MINEUR] `search()` ne filtre pas les résultats avec `score == 0.0` uniquement en mode cosine ; en mode TF-IDF, des scores 0.0 peuvent être retournés sans raison sémantique (ligne 228-237).
  - [INFO] La déduplication dans `add()` est une boucle O(n) sur `_docs` pour trouver le hash (ligne 159-161). Utiliser un `dict` `hash→id` serait O(1).
  - [INFO] `clear()` supprime le fichier mais ne réinitialise pas `_encoder` ni `_fallback` — cohérent mais potentiellement surprenant.
- **Recommandations** :
  - Ajouter un dict interne `_hash_index: dict[str, str]` pour déduplication O(1) dans `add()`.
  - Documenter le comportement `vec_b64 == ""` dans le docstring de `add()`.

---

## memory/agent_memory.py
- **STATUT** : ✅ OK
- **Lignes** : 203
- **Problèmes** :
  - [INFO] `get_context()` retourne une string vide si `bucket` est vide, mais `get_patterns()` retourne une liste vide — nommage asymétrique (lignes 146-150 vs 151-185).
  - [INFO] `clear_all()` ne reset pas `_loaded = False` (ligne 199-202), donc un rechargement ultérieur ne rechargerait pas depuis le fichier vidé — cohérent car `_data` est déjà vide, mais potentiellement surprenant en tests.
- **Recommandations** : aucune correction urgente.

---

## memory/failure_memory.py
- **STATUT** : ✅ OK
- **Lignes** : 215
- **Problèmes** :
  - [MINEUR] La déduplication par `signature()` dans `record_rejection()` itère en O(n) (ligne 137). Sur 500 entrées, acceptable, mais une `set[str]` de signatures serait O(1).
  - [INFO] `get_all_files_with_failures()` retourne un `list` depuis un `set` — l'ordre n'est pas garanti et n'est pas documenté (ligne 195-197).
- **Recommandations** : maintenir un `_signatures: set[str]` interne pour déduplication O(1).

---

## memory/knowledge_memory.py
- **STATUT** : ⚠️ PROBLÈMES MINEURS
- **Lignes** : 384
- **Problèmes** :
  - [MINEUR] `last_used` est un `float | None` ici (ligne 82) mais `last_used` dans `VaultEntry` est une `str | None` — **incohérence de type** entre les deux mémoires de connaissances pour le même concept.
  - [MINEUR] `avoid_duplicate_ideas()` effectue une Jaccard O(n) à chaque appel sans cache. Doublonne la logique avec `VaultMemory._is_jaccard_dup()` (ligne 269-285).
  - [MINEUR] `store_from_dict()` ne passe pas `ttl_days` depuis le dict — paramètre ignoré silencieusement (ligne 210-223).
  - [INFO] `VALID_AGENT_TARGETS` ne contient pas les nouveaux agents business (`venture-builder`, `saas-builder`, etc.) déclarés dans `agents/registry.py`. Toute `agent_target` inconnue est silencieusement filtrée par `__post_init__` (ligne 88-90).
  - [INFO] Le singleton `_instance` peut poser problème si plusieurs chemins de stockage sont désirés dans les tests (ligne 376-383).
- **Recommandations** :
  - Unifier le type de `last_used` entre `VaultEntry` et `KnowledgeEntry` (choisir `float` pour simplicité).
  - Mettre à jour `VALID_AGENT_TARGETS` avec les agents business.
  - Ajouter `ttl_days` dans `store_from_dict()`.

---

## memory/memory_bus.py
- **STATUT** : 🔴 PROBLÈMES CRITIQUES
- **Lignes** : 430
- **Problèmes** :
  - [CRITIQUE] `remember()` (méthode synchrone) utilise `asyncio.ensure_future()` pour appeler `MemoryStore.store()` (ligne 167-169). Si appelée hors d'une boucle asyncio active (ex: test synchrone, script standalone), cela lève `RuntimeError: no running event loop`. De plus, `ensure_future` sans gestion des exceptions peut produire des warnings "coroutine was never awaited" et silencieusement perdre des données.
  - [MINEUR] `_search_vector()` utilise `asyncio.get_event_loop()` (ligne 297) — déprécié en Python 3.10+, devrait être `asyncio.get_running_loop()`.
  - [MINEUR] Dans `get_stats()`, `_store` n'est jamais inclus dans les stats (lignes 372-392), alors que c'est un backend principal. Incohérence avec le docstring.
  - [INFO] La déduplication dans `search()` se fait sur les 100 premiers chars du texte (ligne 286) — peut laisser passer des quasi-doublons et supprimer des résultats légitimes distincts avec un début commun.
- **Recommandations** :
  - **Critique** : supprimer le `asyncio.ensure_future` dans `remember()`. Soit rendre `remember()` entièrement synchrone (sans MemoryStore), soit ajouter une note dans la docstring que cette méthode DOIT être appelée depuis un contexte asyncio. Utiliser `remember_async()` systématiquement.
  - Remplacer `asyncio.get_event_loop()` par `asyncio.get_running_loop()` (ligne 297).

---

## memory/store.py
- **STATUT** : ⚠️ PROBLÈMES MINEURS
- **Lignes** : 371
- **Problèmes** :
  - [MINEUR] `search()` retourne `list[str]` dans la signature publique (ligne 63), mais `_qdrant_search()` retourne `list[str]` alors que `MemoryBus._search_store()` s'attend à `list[dict]` avec clés `"key"`, `"text"`, `"score"` (memory_bus.py ligne 310-318). **Incohérence d'interface** : le bus adapte le retour de `MemoryStore.search()` en supposant des dicts, mais `MemoryStore.search()` renvoie des strings brutes.
  - [MINEUR] `_pg_search()` ne cherche que sur le premier mot de la requête (ligne 354-356) — très limitée comme recherche fulltext. Pas de score de pertinence retourné.
  - [MINEUR] `_get_client()` ne met pas en cache les échecs : Qdrant sera retenté à chaque appel si la connexion échoue, ce qui peut ralentir le système (remarqué dans le commentaire ligne 99-100, mais le `self._client = None` en cas d'échec confirme ce comportement voulu). Acceptable mais à documenter clairement.
  - [INFO] `index_workspace()` indexe uniquement les fichiers `.md` et `.txt` — les fichiers `.py` (plus pertinents pour un système de code) sont ignorés.
- **Recommandations** :
  - Corriger l'incohérence de type de retour de `search()` : retourner `list[dict]` avec au minimum `{"text": ..., "score": 0.0}` pour être compatible avec `MemoryBus`.

---

## memory/patch_memory.py
- **STATUT** : ✅ OK
- **Lignes** : 226
- **Problèmes** :
  - [MINEUR] Déduplication `pattern_key()` itère en O(n) sur `_entries` à chaque `record_success()` (ligne 142). Sur 1000 entrées, perceptible mais non critique.
  - [INFO] `get_success_patterns()` trie par récence mais le commentaire dit "fréquence d'utilisation" (ligne 158-160). Incohérence documentation/code.
- **Recommandations** : corriger le commentaire ou implémenter le tri par fréquence.

---

## COUCHE AGENTS

---

## agents/__init__.py
- **STATUT** : ✅ OK
- **Lignes** : 1 (fichier vide)
- **Problèmes** : aucun

---

## agents/registry.py
- **STATUT** : 🔴 PROBLÈMES CRITIQUES
- **Lignes** : 86
- **Problèmes** :
  - [CRITIQUE] Tous les imports de `agents.crew` et `business.*` sont au niveau module (lignes 15-38). Si **l'une** de ces dépendances échoue à l'import (ex: `langchain_core` absent, `business.meta_builder.agent` non présent), **tout le registre échoue**, rendant inutilisable l'ensemble du système d'agents. Aucun try/except n'est présent.
  - [CRITIQUE] `from agents.openhands_agent import OpenHandsAgent` (ligne 38) — si `openhands_agent.py` a une dépendance manquante, le registre entier échoue. Ce pattern de fail-fast sur les imports du registre est fragile.
  - [MINEUR] `build_registry()` instancie **tous** les agents (ligne 74) même ceux qui ne seront pas utilisés dans la session. Coût mémoire non nul si les constructeurs font des I/O.
- **Recommandations** :
  - Envelopper les imports business dans des blocs try/except avec warning pour isoler les échecs.
  - Envisager une instanciation lazy dans le registre (factory functions au lieu d'instances).

---

## agents/agent_factory.py
- **STATUT** : ⚠️ PROBLÈMES MINEURS
- **Lignes** : 328
- **Problèmes** :
  - [MINEUR] `create_with_critic()` crée une classe dynamique avec `type()` en assignant `"run": SelfCriticMixin.run_with_self_critic` (ligne 243). Cela ne tient pas compte du MRO Python : si `ForgeBuilderWithCritic` est déjà dans `AGENT_CLASSES` (ce qui est le cas), une double-wrapping est possible.
  - [MINEUR] `register()` accepte n'importe quel objet non-DynamicAgent (ligne 280) sans validation — peut stocker des objets incompatibles.
  - [INFO] `_save_custom()` garde uniquement les 20 derniers agents (ligne 160), ce qui peut supprimer des agents persistés créés plus tôt si on en crée 21+.
- **Recommandations** : vérifier que `create_with_critic` n'est pas appliqué à un agent déjà "critic-wrapped".

---

## agents/shadow_advisor/__init__.py
- **STATUT** : ✅ OK
- **Lignes** : 5
- **Problèmes** : aucun

---

## agents/shadow_advisor/scorer.py
- **STATUT** : 🔴 PROBLÈMES CRITIQUES
- **Lignes** : 177
- **Problèmes** :
  - [CRITIQUE] Comparaison type-unsafe à la ligne 113 : `sev = str(issue.severity).lower()` puis `if sev == IssueSeverity.HIGH`. `IssueSeverity.HIGH` est une `str, Enum` avec valeur `"high"`, et `str(IssueSeverity.HIGH)` en Python 3.11+ retourne `"IssueSeverity.HIGH"` (et non `"high"`). La comparaison sera donc **toujours fausse** pour les sévérités HIGH et MEDIUM, les malus ne sont jamais appliqués correctement. Il faut comparer avec `.value` : `sev == IssueSeverity.HIGH.value`.
  - [MINEUR] `explain()` accède à `report._score_steps` via `getattr(report, "_score_steps", [])` (ligne 164). Cet attribut "privé" non déclaré dans le dataclass est fragile — si `score()` n'a pas été appelé avant `explain()`, le fallback `[]` donne une explication vide sans erreur.
- **Recommandations** :
  - **Urgent** : remplacer les comparaisons `sev == IssueSeverity.HIGH/MEDIUM` par `sev == IssueSeverity.HIGH.value` (i.e., `sev == "high"` / `sev == "medium"`).

---

## agents/shadow_advisor/schema.py
- **STATUT** : ⚠️ PROBLÈMES MINEURS
- **Lignes** : 413
- **Problèmes** :
  - [MINEUR] `_fallback_report()` utilise `AdvisoryReport.__new__(AdvisoryReport)` pour contourner `__post_init__` (ligne 393). Cela laisse des attributs non initialisés si le dataclass évolue — fragile.
  - [MINEUR] `_repair_json()` remplace tous les guillemets simples par des doubles (ligne 362), ce qui casse le code Python contenu dans les strings JSON (ex: `"it's fine"` → `"it"s fine"`).
  - [INFO] `validate_advisory_structure()` calcule `dec_val` deux fois consécutivement (lignes 296 et 316) — code mort dupliqué.
- **Recommandations** :
  - Corriger `_fallback_report` pour utiliser le constructeur normal avec des valeurs par défaut.
  - La réparation JSON par remplacement de quotes est dangereuse : utiliser `demjson3` ou accepter l'échec.

---

## agents/evaluator.py
- **STATUT** : ⚠️ PROBLÈMES MINEURS
- **Lignes** : 498
- **Problèmes** :
  - [MINEUR] `_parse_response()` extrait le JSON d'un bloc ``` en splitant sur "```" (ligne 363), ce qui échoue si le bloc est ` ```json` avec espace. Même pattern imparfait que `debug_agent.py`.
  - [MINEUR] Si `total_weight == 0` dans `_parse_response()` (aucune dimension reconnue), le score est `0.0` mais `pass_eval` peut être `True` si `pass_score = 0.0` — logique correcte mais à documenter.
  - [INFO] `evaluate_session()` lire `session.context` pour les outputs (ligne 304) alors que la couche memory utilise `session.outputs`. Incohérence d'accès aux données de session.
- **Recommandations** :
  - Utiliser le même parseur JSON que `shadow_advisor/schema.py` (`_extract_json` + `_repair_json`) pour la cohérence.

---

## agents/self_critic.py
- **STATUT** : ⚠️ PROBLÈMES MINEURS
- **Lignes** : 248
- **Problèmes** :
  - [MINEUR] Dans `run_with_self_critic()`, le contexte de révision tronque `output` à 1 000 chars (ligne 133). Pour des sorties de code longues, le LLM ne voit qu'un fragment de sa propre réponse à réviser.
  - [MINEUR] `_critique()` catch `asyncio.TimeoutError` et retourne un score de 7.0/PASS (ligne 231). En cas de timeout Ollama récurrent, les critiques sont silencieusement skippées et l'agent passe toujours sans révision — fausse l'auto-critique.
  - [MINEUR] `critic_loop()` (usage standalone) initialise `critique = {}` et peut retourner ce dict vide si le premier round passe (ligne 177). L'appelant doit gérer le cas où `critique` est vide.
  - [INFO] `LLMFactory` est instancié à chaque appel de `_critique()` et dans `run_with_self_critic()` (lignes 123, 211) — double instanciation inutile par round.
- **Recommandations** :
  - Instancier `LLMFactory` une seule fois dans le mixin ou le passer en paramètre.
  - Documenter explicitement que le timeout critique retourne PASS par défaut.

---

## agents/web_scout.py
- **STATUT** : ✅ OK
- **Lignes** : 249
- **Problèmes** :
  - [MINEUR] `_run_with_browser()` crée une nouvelle `LLMFactory` à chaque appel (ligne 193) — pattern consistant avec le reste du code mais instanciation répétée.
  - [INFO] Si `search_results` est vide mais `page_contents` n'est pas vide (cas théorique impossible avec le code actuel), le fallback est quand même appelé (ligne 186-187) — logique correcte.
- **Recommandations** : aucune correction urgente.

---

## agents/parallel_executor.py
- **STATUT** : ⚠️ PROBLÈMES MINEURS (correction mineure appliquée)
- **Lignes** : 370
- **Corrections appliquées** :
  - `asyncio.iscoroutinefunction` → `inspect.iscoroutinefunction` + `import inspect` ajouté (ligne 132).
- **Problèmes restants** :
  - [MINEUR] Timeout global de 300s (ligne 36) retourne un dict vide `{}` en cas de dépassement (ligne 169), sans exposer les résultats partiels déjà collectés. Les agents qui ont terminé avant le timeout sont perdus.
  - [MINEUR] `run_with_replan()` crée un `AgentResult` temporaire pour accéder à `.success` via un objet de fallback (lignes 244-248) — pattern hacky, utiliser `results.get(name).success` avec garde serait plus propre.
  - [INFO] `group_by_priority()` est une méthode statique utilitaire non utilisée par `run()` lui-même — c'est un outil à appeler depuis l'orchestrateur.
- **Recommandations** :
  - Retourner les résultats partiels en cas de timeout global au lieu de `{}`.

---

## agents/synthesizer_agent.py
- **STATUT** : ⚠️ PROBLÈMES MINEURS (correction mineure appliquée)
- **Lignes** : 249
- **Corrections appliquées** :
  - `asyncio.iscoroutinefunction` → `inspect.iscoroutinefunction` + `import inspect` ajouté (ligne 63).
- **Problèmes restants** :
  - [MINEUR] Le no-op fallback `emit or (lambda m: asyncio.sleep(0))` (ligne 62) crée une coroutine non-attendue à chaque appel — `asyncio.sleep(0)` est un appel qui retourne une coroutine. Remplacé par le pattern correct via `inspect.iscoroutinefunction` juste après, mais le no-op initial est toujours incorrect.
  - [MINEUR] `_llm_merge()` appelle `self.s.get_llm("fast")` directement sans `LLMFactory.safe_invoke()` (ligne 178-188), contournant le circuit breaker et le fallback.
  - [INFO] `synthesize()` indique `agents_ok == agents_total` systématiquement (ligne 239-241) sans vérifier quels agents ont réellement produit une sortie.
- **Recommandations** :
  - Corriger le no-op lambda : remplacer par `async def _noop(msg): pass` comme dans `parallel_executor.py`.
  - Utiliser `LLMFactory.safe_invoke()` dans `_llm_merge()`.

---

## agents/debug_agent.py
- **STATUT** : ⚠️ PROBLÈMES MINEURS
- **Lignes** : 162
- **Problèmes** :
  - [MINEUR] `from_error_report()` est un `@classmethod` qui retourne `None` (ligne 151). Sa signature suggère qu'il retourne une instance ou un statut — le retour `None` est trompeur.
  - [MINEUR] Le parsing JSON (ligne 106-108) splitte sur `"```"` puis `lstrip("json")` — si le LLM retourne ` ```json\n`, le premier caractère `\n` reste. Pattern fragile partagé avec evaluator.py et recovery_agent.py.
  - [INFO] `RootCauseType` importé depuis `core.contracts` mais jamais utilisé dans ce fichier (ligne 28).
- **Recommandations** :
  - Centraliser la logique de parsing JSON (strip backticks) dans une fonction utilitaire partagée.
  - Supprimer l'import inutilisé `RootCauseType`.

---

## agents/recovery_agent.py
- **STATUT** : ⚠️ PROBLÈMES MINEURS
- **Lignes** : 182
- **Problèmes** :
  - [CRITIQUE] `_apply_rollback()` copie un fichier depuis `_BACKUP_DIR` vers `Path(target)` sans **aucune validation du chemin `target`** (ligne 176). Un LLM compromis ou mal configuré pourrait fournir `target = "/etc/passwd"` ou un chemin système critique — **path traversal via injection LLM**.
  - [MINEUR] `_BACKUP_DIR = Path("workspace/.backups")` est un chemin relatif hardcodé (ligne 24) — peut pointer vers un répertoire incorrect selon le CWD. Devrait utiliser `settings.workspace_dir`.
  - [MINEUR] Même pattern de parsing JSON fragile (ligne 102-104).
- **Recommandations** :
  - **Urgent** : valider que `Path(target).resolve()` est contenu dans le workspace avant tout `shutil.copy2`.
  - Remplacer le chemin hardcodé par `Path(settings.workspace_dir) / ".backups"`.

---

## agents/monitoring_agent.py
- **STATUT** : 🔴 PROBLÈMES CRITIQUES
- **Lignes** : 213
- **Problèmes** :
  - [CRITIQUE] `health_dict()` appelle `asyncio.get_event_loop()` (ligne 86) — déprécié en Python 3.10+. Dans un contexte asyncio actif (FastAPI/aiohttp), `loop.run_until_complete()` lève une `RuntimeError: This event loop is already running`.
  - [CRITIQUE] `_check_executor()` retourne toujours `HealthStatus.OK` à cause de `or True` (ligne 162) : `status.get("running", False) or True` est toujours vrai quelle que soit la valeur de `running`. **Le check executor est ineffectif.**
  - [MINEUR] `_check_llm()` fait un appel LLM réel avec la requête `"ping"` à chaque health check (ligne 120). Sur un health check fréquent, cela génère du trafic LLM et de la latence.
  - [INFO] `MonitoringAgent` n'hérite pas de `BaseAgent` — non registrable dans le registre d'agents sans adaptation.
- **Recommandations** :
  - **Urgent** : corriger la condition `or True` : `status=HealthStatus.OK if status.get("running", False) else HealthStatus.DEGRADED`.
  - Remplacer `asyncio.get_event_loop()` par un pattern asyncio correct.
  - Remplacer le ping LLM par un check de disponibilité plus léger (ex: vérifier que la factory est instanciable).

---

## COUCHE LEARNING

---

## learning/__init__.py
- **STATUT** : ✅ OK
- **Lignes** : 1 (fichier vide)
- **Problèmes** : aucun

---

## learning/learning_loop.py
- **STATUT** : ⚠️ PROBLÈMES MINEURS
- **Lignes** : 406
- **Problèmes** :
  - [MINEUR] `observe_session()` accède à `session.agents_outputs` (ligne 179), mais `JarvisSession` expose `session.outputs` (dict de `AgentOutput`), pas `agents_outputs`. **AttributeError garanti si `agents_outputs` n'est pas défini sur l'objet session** — testé uniquement avec des stubs dans les tests.
  - [MINEUR] `_validate_and_store()` instancie `KnowledgeValidator()` et appelle `get_vault_memory()` à **chaque insight** (lignes 320-322). Pour 10 insights par cycle, 10 instanciations de KnowledgeValidator. Validator devrait être instancié une seule fois par `LearningLoop`.
  - [MINEUR] `_split_sentences()` filtre les lignes commençant par `#` (commentaires Python) mais pas les blocs de code JSON ou YAML qui peuvent contenir des patterns `.startswith("{")` (ligne 238).
  - [INFO] `_TYPE_CONFIDENCE` définit un score pour `"code"` (0.70) mais `_classify_sentence()` ne peut jamais retourner `type="code"` — ce type n'est jamais sélectionné (lignes 54-61 vs 262-272).
  - [INFO] Le singleton `_loop_instance` et la fonction shortcut `learning_loop()` ont le même nom que la classe `LearningLoop` — peut créer de la confusion à l'import.
- **Recommandations** :
  - **Urgent** : corriger l'accès `session.agents_outputs` — utiliser `session.outputs` et adapter le parsing `AgentOutput`.
  - Instancier `KnowledgeValidator` une seule fois dans `LearningLoop.__init__`.
  - Supprimer `"code"` de `_TYPE_CONFIDENCE` ou implémenter sa détection dans `_classify_sentence`.

---

## learning/learning_engine.py
- **STATUT** : ✅ OK
- **Lignes** : 316
- **Problèmes** :
  - [MINEUR] `recommend_strategy()` retourne `preferred_model: None` systématiquement (ligne 264) avec le commentaire "déterminé par ModelSelector". Si `ModelSelector` n'est jamais appelé, ce champ reste toujours `None` — potentiellement inutile.
  - [MINEUR] `generate_report()` appelle `compute_success_rates()` ET `recommend_strategy()` séquentiellement, et `recommend_strategy()` appelle à nouveau `compute_success_rates()` en interne — double calcul inutile (lignes 279-281).
  - [INFO] Aucune validation des champs requis dans `record_run()` — un dict vide est accepté silencieusement.
- **Recommandations** :
  - Dans `generate_report()`, passer `rates` à `recommend_strategy()` pour éviter le recalcul, ou cacher le résultat.

---

## learning/knowledge_filter.py
- **STATUT** : ✅ OK
- **Lignes** : 343
- **Problèmes** :
  - [MINEUR] `_freshness_score()` utilise `time.localtime().tm_year` pour l'année courante. Cohérent mais `time.gmtime()` serait plus robuste pour les serveurs en différentes timezones (ligne 249).
  - [MINEUR] `_detect_type()` vérifie `domain in _BANNED_DOMAINS` mais `quora.com` est aussi listé dans la vérification des forums (ligne 229), créant une redondance. La vérification `_BANNED_DOMAINS` est prioritaire (correct), mais la deuxième vérification est du code mort pour quora.
  - [INFO] `wikihow.com` est dans `_BANNED_DOMAINS` avec le commentaire "trop généraliste" mais n'est pas en contradiction avec certains cas d'usage techniques.
- **Recommandations** : supprimer `quora.com` de la liste forum si déjà dans `_BANNED_DOMAINS`.

---

## learning/knowledge_validator.py
- **STATUT** : ⚠️ PROBLÈMES MINEURS
- **Lignes** : 400
- **Problèmes** :
  - [MINEUR] `_DANGEROUS_PATTERNS` contient `exec\(|eval\(` (ligne 91-97). Ces patterns vont **rejeter des connaissances légitimes** sur l'utilisation sécurisée d'`eval` (ex: "Never use eval() in production code" sera rejeté car il contient `eval(`). Le pattern devrait être plus contextuel.
  - [MINEUR] `_is_compatible()` rejette toute connaissance contenant `time.sleep()` (ligne 339), ce qui inclut des connaissances sur le fait de *ne pas* utiliser `time.sleep()` — faux positifs fréquents.
  - [MINEUR] `validate_batch()` accumule `existing_knowledge` avec les contenus acceptés au fil du batch (ligne 258). Si deux items similaires sont validés en parallèle, le deuxième peut être rejeté comme doublon sans avoir vu le premier — comportement attendu mais l'ordre du batch impacte les résultats.
  - [INFO] `_decide()` n'utilise pas les paramètres `utility`, `reusability`, `is_testable` pour affiner la décision — seul `global_score` et `credibility` comptent (lignes 388-399). Ces paramètres sont calculés mais n'influencent le verdict qu'indirectement via `global_score`.
- **Recommandations** :
  - Rendre `_DANGEROUS_PATTERNS` plus précis : détecter `exec(` uniquement s'il n'est pas précédé de `"never"`, `"avoid"`, `"don't use"`.
  - Corriger `_is_compatible` pour ne rejeter que l'*utilisation* de `time.sleep`, pas les discussions à son sujet.

---

## TABLEAU RÉCAPITULATIF

| Fichier | Statut | Nb problèmes | Priorité correction |
|---|---|---|---|
| memory/__init__.py | ✅ OK | 0 | — |
| memory/vault_memory.py | ⚠️ MINEURS | 5 | Basse |
| memory/vector_memory.py | ⚠️ MINEURS | 4 | Basse |
| memory/agent_memory.py | ✅ OK | 2 infos | — |
| memory/failure_memory.py | ✅ OK | 2 | Basse |
| memory/knowledge_memory.py | ⚠️ MINEURS | 5 | Moyenne |
| memory/memory_bus.py | 🔴 CRITIQUES | 4 | **Haute** |
| memory/store.py | ⚠️ MINEURS | 4 | Moyenne |
| memory/patch_memory.py | ✅ OK | 2 | Basse |
| agents/__init__.py | ✅ OK | 0 | — |
| agents/registry.py | 🔴 CRITIQUES | 3 | **Haute** |
| agents/agent_factory.py | ⚠️ MINEURS | 3 | Basse |
| agents/shadow_advisor/__init__.py | ✅ OK | 0 | — |
| agents/shadow_advisor/scorer.py | 🔴 CRITIQUES | 2 | **Urgente** |
| agents/shadow_advisor/schema.py | ⚠️ MINEURS | 3 | Moyenne |
| agents/evaluator.py | ⚠️ MINEURS | 3 | Basse |
| agents/self_critic.py | ⚠️ MINEURS | 4 | Moyenne |
| agents/web_scout.py | ✅ OK | 1 | — |
| agents/parallel_executor.py | ⚠️ MINEURS | 2 | Basse (corrigé) |
| agents/synthesizer_agent.py | ⚠️ MINEURS | 3 | Moyenne (corrigé partiellement) |
| agents/debug_agent.py | ⚠️ MINEURS | 3 | Basse |
| agents/recovery_agent.py | 🔴 CRITIQUES | 3 | **Haute** |
| agents/monitoring_agent.py | 🔴 CRITIQUES | 3 | **Haute** |
| learning/__init__.py | ✅ OK | 0 | — |
| learning/learning_loop.py | ⚠️ MINEURS | 5 | **Haute** |
| learning/learning_engine.py | ✅ OK | 3 | Basse |
| learning/knowledge_filter.py | ✅ OK | 2 | Basse |
| learning/knowledge_validator.py | ⚠️ MINEURS | 4 | Moyenne |

---

## TOP 10 CORRECTIONS PRIORITAIRES

### 1. [URGENTE] `agents/shadow_advisor/scorer.py` — comparaison Enum type-unsafe
**Fichier** : `agents/shadow_advisor/scorer.py`, lignes 113-120
**Problème** : `sev == IssueSeverity.HIGH` compare une string `"high"` avec l'objet enum `IssueSeverity.HIGH`. En Python 3.11+, `str(IssueSeverity.HIGH)` = `"IssueSeverity.HIGH"`. Les malus pour sévérités HIGH et MEDIUM ne sont jamais appliqués. Le Shadow-Advisor sous-évalue systématiquement les risques.
**Correction** : Remplacer `sev == IssueSeverity.HIGH` par `sev == IssueSeverity.HIGH.value` (et idem MEDIUM/LOW) — ou comparer directement `sev == "high"`.

---

### 2. [HAUTE] `agents/monitoring_agent.py` — check executor toujours OK
**Fichier** : `agents/monitoring_agent.py`, ligne 162
**Problème** : `status.get("running", False) or True` est tautologiquement `True`. Le health check de l'executor retourne toujours `HealthStatus.OK` quelle que soit la réalité.
**Correction** : Remplacer par `HealthStatus.OK if status.get("running", False) else HealthStatus.DEGRADED`.

---

### 3. [HAUTE] `agents/monitoring_agent.py` — `asyncio.get_event_loop()` déprécié
**Fichier** : `agents/monitoring_agent.py`, ligne 86
**Problème** : `asyncio.get_event_loop()` lève une `DeprecationWarning` en Python 3.10+ et une `RuntimeError` si appelé dans un contexte asyncio actif (FastAPI). La méthode `health_dict()` est inutilisable dans un serveur async.
**Correction** : Utiliser `asyncio.get_running_loop()` dans les contextes async, ou refactoriser `health_dict()` pour ne pas appeler `run_until_complete`.

---

### 4. [HAUTE] `agents/recovery_agent.py` — path traversal via LLM
**Fichier** : `agents/recovery_agent.py`, lignes 167-181
**Problème** : `_apply_rollback()` accepte un `target` fourni par le LLM sans validation. Un LLM mal aligné ou compromis peut écrire n'importe où sur le filesystem (ex: `/etc/passwd`, clés SSH).
**Correction** : Ajouter avant `shutil.copy2` :
```python
workspace_root = Path(getattr(self.s, "workspace_dir", "workspace")).resolve()
if not Path(target).resolve().is_relative_to(workspace_root):
    return {"ok": False, "error": "Target outside workspace — rejected"}
```

---

### 5. [HAUTE] `memory/memory_bus.py` — `asyncio.ensure_future` hors contexte async
**Fichier** : `memory/memory_bus.py`, lignes 165-169
**Problème** : `remember()` (méthode synchrone) appelle `asyncio.ensure_future()` pour le backend MemoryStore. En dehors d'une boucle asyncio active, cela lève `RuntimeError`. Les coroutines non-attendues produisent des `RuntimeWarning` silencieux et perdent des données.
**Correction** : Soit supprimer le `BACKEND_STORE` de `BACKEND_ALL` pour `remember()` synchrone, soit documenter que `remember()` exige un contexte asyncio actif et préférer systématiquement `remember_async()`.

---

### 6. [HAUTE] `agents/registry.py` — fail-fast sur tous les imports
**Fichier** : `agents/registry.py`, lignes 15-38
**Problème** : Un import manquant (langchain, business module, openhands) fait échouer l'intégralité du registre. Tout le système d'agents devient inutilisable.
**Correction** : Envelopper les imports de `business.*` et `agents.openhands_agent` dans des blocs `try/except ImportError` avec logging warning et exclusion de l'agent du registre.

---

### 7. [HAUTE] `learning/learning_loop.py` — AttributeError sur `session.agents_outputs`
**Fichier** : `learning/learning_loop.py`, ligne 179
**Problème** : `session.agents_outputs` n'existe pas dans `JarvisSession`. La vraie propriété est `session.outputs` (dict de `AgentOutput`). La méthode `observe_session()` lève une `AttributeError` à l'exécution.
**Correction** : Remplacer `session.agents_outputs or {}` par `{name: {"output": o.output, "success": o.success} for name, o in (getattr(session, "outputs", {}) or {}).items()}`.

---

### 8. [MOYENNE] `memory/store.py` — incohérence de type de retour avec MemoryBus
**Fichier** : `memory/store.py`, ligne 63 + `memory/memory_bus.py`, lignes 310-318
**Problème** : `MemoryStore.search()` retourne `list[str]`, mais `MemoryBus._search_store()` s'attend à `list[dict]` avec clés `"key"`, `"text"`, `"score"`. L'adaptation dans le bus suppose une structure qui n'existe pas — les résultats `store` ne sont jamais retournés correctement dans `MemoryBus.search()`.
**Correction** : Modifier `MemoryStore.search()` pour retourner `list[dict]` : `[{"text": t, "score": 0.0, "key": "", "metadata": {}} for t in raw_texts]`.

---

### 9. [MOYENNE] `memory/knowledge_memory.py` — `VALID_AGENT_TARGETS` obsolète
**Fichier** : `memory/knowledge_memory.py`, lignes 58-63
**Problème** : `VALID_AGENT_TARGETS` ne contient pas les agents business (`venture-builder`, `saas-builder`, `trade-ops`, `meta-builder`, `openhands`). Toute connaissance ciblant ces agents voit son `agent_targets` vidé silencieusement dans `__post_init__`, rendant `get_for_agent()` incapable de retourner des connaissances pour ces agents.
**Correction** : Synchroniser `VALID_AGENT_TARGETS` avec `AGENT_CLASSES.keys()` de `agents/registry.py`, ou supprimer la validation et laisser les noms passer librement.

---

### 10. [MOYENNE] `agents/synthesizer_agent.py` — no-op lambda crée une coroutine non-attendue
**Fichier** : `agents/synthesizer_agent.py`, ligne 62
**Problème** : `_emit = emit or (lambda m: asyncio.sleep(0))` — si `emit` est `None`, `_emit("msg")` appelle `asyncio.sleep(0)` et retourne une coroutine non-attendue. Cela produit un `RuntimeWarning: coroutine 'sleep' was never awaited` et ne constitue pas un no-op valide.
**Correction** : Remplacer par le même pattern que `parallel_executor.py` :
```python
async def _noop(msg: str) -> None: pass
_emit = emit or _noop
```

---

## PROBLÈMES TRANSVERSAUX

### Duplication de logique
- La déduplication Jaccard est implémentée 3 fois indépendamment : `VaultMemory._is_jaccard_dup()`, `KnowledgeMemory.avoid_duplicate_ideas()`, `KnowledgeValidator._is_duplicate()`. Une fonction utilitaire partagée dans `utils/similarity.py` réduirait la dette.
- Le parsing JSON "strip backticks" est copié-collé dans `debug_agent.py`, `recovery_agent.py`, `evaluator.py`, `self_critic.py`. Une fonction `parse_llm_json(raw: str) -> dict` centralisée dans `utils/` est nécessaire.

### Incohérences de types
- `last_used` : `str|None` dans `VaultEntry`, `float|None` dans `KnowledgeEntry`.
- `session.outputs` vs `session.agents_outputs` : une seule doit exister.

### Tests manquants (fonctions critiques)
- `AdvisoryScorer.score()` — le bug de comparaison Enum aurait été détecté par un test unitaire.
- `MonitoringAgent._check_executor()` — le `or True` aurait été détecté.
- `LearningLoop.observe_session()` — l'AttributeError aurait été détectée.
- `RecoveryAgent._apply_rollback()` — aucun test de path traversal.

---

*Rapport généré le 2026-03-19 — JarvisMax audit v1.0*
