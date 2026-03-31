# RUNTIME_TRUTH.md — JarvisMax Actual Execution Path

**Last updated**: 2026-03-31 (BLOC G — Improvement daemon actif au boot + BLOC F visibilité critique)
**Purpose**: Ground truth for the actual runtime. Supersedes any idealized description.
**Audience**: Developers, reviewers, OpenClaw integration agent.

---

## BLOC G (2026-03-31) — Improvement Daemon : démarrage au boot

### Vérité avant (pré-BLOC G)
- `core/improvement_daemon.py` (891 lignes) contient `start_daemon()` : thread non-bloquant, idempotent, `daemon=True`.
- **Jamais appelé depuis `main.py`**. Le cycle `SelfImprovementLoop.run_cycle()` était complètement dormant. Le système ne s'améliorait jamais de ses propres missions en production.
- Seul `core/action_executor` était démarré comme daemon de fond.

### Changements réels
- `main.py` : ajout d'un bloc `── 4. Improvement daemon ──` après l'action executor, appelant `core.improvement_daemon.start_daemon()`.
- Fail-open : `try/except → log.warning("improvement_daemon_start_failed", ...)`. Jamais bloquant.

### Preuve runtime
- **31/31 passed** ✅
- Au boot : `improvement_daemon_started status=started` visible dans les logs.
- Thread `improvement-daemon` (daemon=True) actif en arrière-plan.

---

## BLOC F (2026-03-31) — Boot Visibility : 5 registrations critiques élevées à WARNING

### Vérité avant (pré-BLOC F)
- 13 `log.debug(...)` pour des échecs de registration dans `main.py`. Tous invisibles en production (`INFO` level par défaut).
- 5 d'entre eux représentaient des défaillances critiques sans fallback :
  1. `jarvis_kernel_orchestrator_register_skipped` — kernel ne peut pas lancer de missions
  2. `kernel_evaluator_register_skipped` — pipeline d'évaluation dégradé
  3. `kernel_lesson_store_register_skipped` — système ne peut plus stocker de leçons
  4. `kernel_lesson_retrieve_register_skipped` — boucle cognitive brisée (pas de leçons passées)
  5. `kernel_facade_memory_register_skipped` — kernel memory complètement aveugle

### Changements réels
- `main.py` : 5 `log.debug(...)` → `log.warning(...)` avec nouveaux noms `*_register_failed` (vs `*_register_skipped`).
- Les 8 autres restent `log.debug` (fallback kernel natif disponible : policy, planner, classifier, router, reflection, critique, execution_memory, gate_history).

### Preuve runtime
- **31/31 passed** ✅
- Tout défaut critique déclenche un WARNING visible en production standard (INFO+).

---

## BLOC E (2026-03-31) — API Boundary : suppression import mort + frontière stable

### Vérité avant (pré-BLOC E)
- `api/routes/missions.py` importait `_get_kernel` depuis `api/_deps.py` (ligne 22).
- `_get_kernel()` n'était **jamais appelé** dans `missions.py` — import mort 100%.
- La frontière canonique API→kernel est `_get_kernel_adapter()` (R8) via `interfaces.kernel_adapter`. L'import mort créait une confusion : le lecteur pouvait croire que l'accès direct au kernel était actif.

### Changements réels
- `api/routes/missions.py` : suppression de `_get_kernel` de la liste d'imports. Commentaire explicite : `# Use _get_kernel_adapter() (R8 canonical boundary)`.

### Preuve runtime
- `python tests/test_integration_kernel_security_business.py` : **31/31 passed** ✅
- `grep "_get_kernel()" api/routes/missions.py` → vide (zéro appel)

---

## BLOC D (2026-03-31) — Security Hardening : exception visible + audit gap détectable

### Vérité avant (pré-BLOC D hardening)
- `core/meta_orchestrator.py` Phase 3-slayer : exception sur `SecurityLayer.check_action()` capturée avec `log.debug(...)`. Une SecurityLayer cassée (import manquant, timeout, etc.) était silencieuse — le log debug était noyé dans le bruit.
- `ctx.metadata["security_layer"]` n'était peuplé qu'en cas de succès → impossible de distinguer "sécurité passée" de "sécurité sautée".

### Changements réels
- `core/meta_orchestrator.py` ligne ~945 : `log.debug` → `log.warning` pour l'exception security_layer.
- Ajout dans l'except block : `ctx.metadata.setdefault("security_layer", {"skipped": True, "error": ..., "allowed": None})` — toute audit trail peut désormais détecter l'échec.

### Preuve runtime
- **31/31 passed** ✅

---

## BLOC C (2026-03-31) — Agent Authority : registration failure non silencieuse

### Vérité avant (pré-BLOC C)
- `main.py` : si `build_and_register_kernel_agents()` échouait → `log.debug("kernel_agents_register_skipped", ...)`.
- Aucun agent enregistré dans `KernelAgentRegistry` → Phase 3-kagents retourne 0 candidats → autorité kernel sur les agents = zéro. Invisible en production.

### Changements réels
- `main.py` ligne ~241 : `log.debug("kernel_agents_register_skipped", ...)` → `log.warning("kernel_agents_register_failed", ...)`.
- Tout échec d'enregistrement d'agent kernel déclenche un WARNING visible en production.

### Preuve runtime
- **31/31 passed** ✅

---

## BLOC B (2026-03-31) — Memory Unification : crew.py converge vers MemoryFacade

### Vérité avant (pré-BLOC B)
- `agents/crew.py._vec_ctx()` : utilisait `memory.vector_memory.VectorMemory` (module racine `memory/`) pour les lookups sémantiques. Ce store est isolé de `MemoryFacade` (`core.memory.vector_memory.get_vector_memory`). Les résultats de recherche sémantique des agents crew venaient d'un silo séparé de celui que le kernel interroge.
- Résultat : deux stores vecteurs distincts, résultats partiels, convergence nulle.

### Changements réels
- `agents/crew.py._vec_ctx()` : `memory.vector_memory.VectorMemory` → `core.memory_facade.MemoryFacade.search()`.
- Même logique de score/seuil conservée. Duck-typing `MemoryEntry` vs `dict` (même pattern que BLOC 1).
- Fallback silencieux inchangé (try/except → return "").

### Preuve runtime
- **31/31 passed** ✅
- `crew._vec_ctx()` interroge désormais le store unifié. Cohérence avec `learning_loop.py` et `main.py` facade_search_wrapper (BLOC 1).

---

## BLOC A (2026-03-31) — MetaOrchestrator : cerveau parallèle éliminé

### Vérité avant (pré-BLOC A)
- `core/meta_orchestrator.py` : 1688 lignes. Deux appels inline à `core.orchestration.*` subsistaient indépendamment de `_kernel_precomp_ok` :
  1. **Fallback classify** (Phase 1, ~ligne 458) : si `kernel.classifier.mission_classifier` échouait, le code tombait sur `core.orchestration.mission_classifier.classify()`. Double cerveau classification.
  2. **`compute_judgment_signals`** (Phase 3 evaluate, ~ligne 1088) : quand `_reasoning_result and _kernel_score.critique_dict`, le code reconstruisait un `CritiqueResult` et appelait `core.orchestration.reasoning_engine.compute_judgment_signals()`. Redondant — `_kernel_score` contient déjà `critique_dict`/`reflection_dict`.

### Changements réels

**Fix 1** — `core/meta_orchestrator.py` Phase 1 classify (else branch) :
- Supprimé le `try/except` imbriqué avec `from core.orchestration.mission_classifier import classify`
- Désormais : kernel classifier uniquement → si échec → `classification = None` (géré en aval)
- Suppression du cerveau parallèle classify

**Fix 2** — `core/meta_orchestrator.py` Phase 3 evaluate :
- Supprimé le bloc `if _reasoning_result and _kernel_score.critique_dict:` (25 lignes)
- Plus d'import de `compute_judgment_signals` / `CritiqueResult` depuis `core.orchestration.reasoning_engine`
- Remplacé par commentaire : kernel_score contient déjà tous les signaux
- `ctx.metadata["judgment_signals"]` n'est plus peuplé (aucun code downstream ne dépendait de ce champ)

### Preuve runtime
- `wc -l core/meta_orchestrator.py` : **1688 → 1660** (−28 lignes)
- `python tests/test_integration_kernel_security_business.py` : **31/31 passed — 254ms** ✅

---

## BLOC 4 (2026-03-31) — Security + Business Governance End-to-End

### Vérité avant (pré-BLOC 4)
- `api/routes/security_audit.py` → `list_security_rules()` accédait à `rule.action_pattern`, `rule.risk_level`, `rule.applies_to_mode`, `rule.priority` — aucun de ces champs n'existe sur `PolicyRule`. `AttributeError` → toujours `{"error": ..., "rules": [], "count": 0}`.
- `SecurityLayer.check_action()` (avec `PolicyRuleSet` + `AuditTrail`) n'était **jamais** appelée pendant l'exécution d'une mission. Seul `check_action_kernel()` (kernel policy bridge) était appelé. Les règles de gouvernance métier (paiement, déploiement, auto-amélioration) étaient silencieusement ignorées.
- `AuditTrail` singleton créé sans chemin de fichier → mémoire uniquement → perdu au redémarrage.

### Changements réels

**Fix A** — `api/routes/security_audit.py` → `list_security_rules()`:
- Remplacé `rule.action_pattern` → `rule.action_types`
- Remplacé `rule.risk_level` → `rule.min_risk_level`
- Remplacé `rule.applies_to_mode` → `rule.modes`
- Supprimé `rule.priority` (n'existe pas)

**Fix B** — `core/meta_orchestrator.py` → Phase 3-slayer (nouvelle phase):
- Après Phase 3-kernel, ajout du bloc `security.get_security_layer().check_action()`
- Mapping `task_type` → `action_type` SecurityLayer: `deployment` → `"deployment"`, `improvement` → `"self_improvement"`, `business` → `"payment"`, autres → `"mission_execution"`
- Résultat stocké dans `ctx.metadata["security_layer"]`
- Si `escalated=True` ou `allowed=False` → `needs_approval = True` (sauf `force_approved`)
- Trace: `policy: security_layer_checked` avec `action_type`, `allowed`, `escalated`, `entry_id`

**Fix C** — `security/audit/trail.py` → `get_audit_trail()`:
- Chemin par défaut: `logs/security_audit.jsonl` (ou `JARVIS_AUDIT_LOG` env)
- `logs/` créé automatiquement si absent
- AuditTrail durable entre redémarrages

### Ce qui a été supprimé
- Rien. 3 corrections chirurgicales.

### Ce qui reste ouvert
- La SecurityLayer est WARN-only pour `mission_execution` general — correct par design.
- Le contenu exact de la mission n'est pas analysé pour détecter payment inline (nécessiterait NLP).

### Preuve runtime
```
31/31 tests passed — 256ms
list_security_rules() renders 6 rules correctly
deployment → escalated=True, entry_id=audit-16e97489d...
self_improvement → escalated=True, entry_id=audit-86335c793...
mission_execution → allowed=True
AuditTrail persisted to /tmp/test_audit_trail.jsonl, entry found in file
```

---

## BLOC 3 (2026-03-31) — Agent System Under Kernel Authority

### Vérité avant (pré-BLOC 3)
- `KernelAgentRegistry` mentionnait `healthy_agents()` dans sa docstring (ligne 226) mais la méthode n'existait pas → `api/routes/kernel.py` ne pouvait pas offrir de vue santé en bulk.
- `KernelAgentRegistry` n'avait pas de méthode `dispatch()` → le kernel pouvait lister les agents mais jamais en dispatcher un.
- Un seul agent enregistré (`KernelStatusAgent` — `system_status`) → aucune couverture du type `mission_execution`.
- `MetaOrchestrator.run_mission()` ne consultait jamais le `KernelAgentRegistry` → aucune autorité kernel sur la sélection d'agents.

### Changements réels

**Fix A** — `kernel/contracts/agent.py` → `KernelAgentRegistry`:
- Ajout de `healthy_agents()` async : appelle `agent.health_check()` en concurrent sur tous les agents, retourne ceux en HEALTHY/DEGRADED
- Ajout de `dispatch(task, capability_type)` async : sélectionne l'agent par capability_type, appelle `execute()`, retourne `KernelAgentResult`. Si aucun agent disponible → SKIPPED (fail-open)

**Fix B** — `agents/kernel_bridge.py`:
- Ajout de `KernelMissionAgent` : `capability_type = "mission_execution"`, `execute()` → `kernel.run_cognitive_cycle()`, `health_check()` → vérifie kernel.booted
- Enregistré dans `build_and_register_kernel_agents()` → 2 agents au boot (status + mission_execution)

**Fix C** — `api/routes/kernel.py`:
- Ajout `GET /api/v3/kernel/agents/healthy` : appelle `registry.healthy_agents()`, retourne health count en bulk

**Fix D** — `core/meta_orchestrator.py` → Phase 3-kagents:
- Avant Phase 3 (exécution supervisée), consulte `KernelAgentRegistry.list_by_capability(task_type)` + `list_by_capability("mission_execution")`
- Stocke `ctx.metadata["kernel_agent_candidates"]` et `ctx.metadata["kernel_registry_size"]`
- Log `kernel_agent_lookup` avec mission_id, task_type, candidates

### Ce qui a été supprimé
- Rien. 4 ajouts chirurgicaux, aucun retrait.

### Ce qui reste ouvert
- Dispatch effectif via le registry (actuellement `delegate.run()` toujours utilisé pour l'exécution complète)
- Agents `crew.py` (scout-research, forge-builder, etc.) non encore enregistrés dans KernelAgentRegistry

### Preuve runtime
```
31/31 tests passed — 220ms
healthy_agents() → 2: ['kernel-status-agent', 'kernel-mission-agent']
dispatch(mission_execution) → agent=kernel-mission-agent, status=success
dispatch(system_status) → agent=kernel-status-agent, status=success
dispatch() on empty registry → SKIPPED (correct fail-open)
GET /agents/healthy route registered
```

---

## BLOC 1 (2026-03-31) — Memory Unification End-to-End

### Vérité avant (pré-BLOC 1)
- `find_relevant_lessons()` appelait `r.get("content", "")` sur des objets `MemoryEntry` (dataclass).
  → `AttributeError` silencieusement capturé → toujours `[]` retourné.
  → La boucle cognitive du kernel recevait **0 leçons**, même si des leçons existaient en mémoire.

- `register_facade_search(_mf.search)` : quand le kernel appelait `_facade_search_fn(query, top_k)`,
  `top_k` (un entier) était passé comme `content_type` (2e arg positionnel de `MemoryFacade.search()`).
  → Filtre `r.content_type == 5` → toujours `[]`.
  → `kernel.memory.search()` brisé pour tout appel avec top_k explicite.

### Changements réels

**Fix A** — `core/orchestration/learning_loop.py` → `find_relevant_lessons()`:
- Remplacé `r.get("content", "")` / `r.get("score", 0.0)` par `getattr(r, "content", "")` / `getattr(r, "score", 0.0)`
- Compatible dict ET MemoryEntry (duck-typing)

**Fix B** — `main.py` → Phase 10d:
- Remplacé `register_facade_search(_mf.search)` par un wrapper `_facade_search_wrapper(query, top_k=5)`:
  1. Passe `top_k` en kwarg → `_mf.search(query, top_k=top_k)` (plus de collision avec `content_type`)
  2. Convertit `MemoryEntry` → `dict` via `.to_dict()` ou accès attributs → kernel reçoit `list[dict]`

### Ce qui a été supprimé
- Rien. Deux corrections chirurgicales, aucune refactorisation.

### Ce qui reste ouvert
- La persistence (`_persist_record` → `_facade_store_fn`) est correcte — aucun bug trouvé.
- Les leçons sont stockées via `store_lesson(KernelLesson)` → duck-typing compat avec `Lesson` — OK.
- BLOC 3 (Agent System), BLOC 4 (Security), BLOC 5 (Observability) : à venir.

### Preuve runtime
```
31/31 tests passed — 231ms
Fix A: find_relevant_lessons correctly handles MemoryEntry objects — 2 lessons retrieved
Fix B: search wrapper correctly passes top_k=3 as keyword, content_type=None
```

---

## BLOC 2 (2026-03-31) — MetaOrchestrator Kernel-First

### Vérité avant BLOC 2
- `run_mission()` exécutait en dur : Phase 0b (semantic routing), Phase 0d (capability bridge), Phase 0e (performance intel) **à chaque mission**, même quand `kernel.run_cognitive_cycle()` avait déjà tout calculé
- Phase 3b avait un fallback `core.orchestration.learning_loop.extract_lesson` → `store_lesson` : violation directe de R5 (learning authority = kernel.learn())
- `run()` avec `mode != "auto"` → `self.jarvis.run()` directement, bypass total du pipeline kernel (pas de classify, plan, route, evaluate, learn)

### Changements réels (5 chirurgies dans `core/meta_orchestrator.py`)

| Chirurgie | Localisation | Impact |
|-----------|-------------|--------|
| `_kernel_precomp_ok = bool(_kernel_context)` | post `_run_kernel_cognitive_cycle()` | flag d'autorité kernel |
| Phase 0b guard `if not _kernel_precomp_ok:` | ~460 | semantic routing skippé si kernel OK |
| Phase 0d guard `if not _kernel_precomp_ok:` | ~600 | capability bridge skippé si kernel OK |
| Phase 0e guard `if not _kernel_precomp_ok:` | ~625 | perf intel skippé si kernel OK |
| Phase 3b fallback supprimé | ~1180 | R5 enforced — kernel.learn() seul autorité |
| `run()` bypass fermé | ~1555 | tous modes → run_mission() |

### Ce qui a été supprimé / neutralisé
- `from core.orchestration.learning_loop import extract_lesson, store_lesson` — supprimé de run_mission()
- Bypass `mode != "auto" → self.jarvis.run()` — supprimé de run()
- Exécution systématique de semantic_match_capability — guardée

### Ce qui reste ouvert
- Les phases inline 0c (routing), 1b (planning) conservent leurs fallbacks kernel — ils s'appuient sur des registrations kernel, pas sur core direct
- Phase 2 (context_assembler) — reste inline (dépend memory retrieval, pas cognitif)
- JarvisOrchestrator / OrchestratorV2 — toujours les vrais exécuteurs (BLOC 3 cible ça)

### Preuve runtime
```
✅ _kernel_precomp_ok flag présent
✅ 3 guards phases 0b/0d/0e
✅ R5 fallback learning_loop supprimé
✅ run() bypass mode non-auto fermé
✅ kernel.learn() R5 présent
✅ 31/31 tests — 245ms
```

---

## Passes 26–33 (2026-03-31) — End-to-End Hardening + Observabilité + CI

| Pass | Fichier(s) créé/modifié | Règle | Statut |
|------|------------------------|-------|--------|
| 26 | `api/routes/missions.py` → `KernelAdapter.submit()` | R8 — API adaptateur pur end-to-end | ✅ |
| 26 | `api/_deps.py` → `_get_kernel_adapter()` | R8 — point d'entrée adapté | ✅ |
| 27 | `agents/kernel_bridge.py` → `KernelStatusAgent` + `build_and_register_kernel_agents()` | R7 — agent real boot-registered | ✅ |
| 27 | `main.py` → Phase 11 boot step (`build_and_register_kernel_agents`) | R7 — registration au boot | ✅ |
| 28 | Dockerfile + docker-compose.yml validés | déploiement — 0 dep nouvelle | ✅ |
| 29 | `RUNTIME_TRUTH.md` + `KERNEL_AUDIT.md` finalisés | documentation | ✅ |
| 30 | `api/routes/kernel.py` → 4 routes: `/agents`, `/agents/{id}`, `/agents/{id}/health`, `/adapter/status` | R7/R8 observabilité | ✅ |
| 31 | `api/routes/security_audit.py` → 5 routes: `/rules`, `/audit`, `/audit/mission/{id}`, `/status`, `/check` | R3/R10 observabilité | ✅ |
| 31 | `api/main.py` → `security_audit_router` enregistré | intégration | ✅ |
| 32 | `.github/workflows/kernel_ci.yml` — 7 steps CI | automatisation K1 + R7-R10 | ✅ |
| 33 | `KERNEL_AUDIT.md` + `RUNTIME_TRUTH.md` mise à jour | documentation | ✅ |

### Détail Pass 26 — R8 end-to-end

**Avant (Pass 14–25) :** `missions.py` appelait `_get_kernel()` directement et importait `kernel.execution.contracts.ExecutionRequest` — violation R8 (API touche kernel internals).

**Après (Pass 26) :**
```python
# api/_deps.py
def _get_kernel_adapter():
    from interfaces.kernel_adapter import get_kernel_adapter
    return get_kernel_adapter()

# api/routes/missions.py
_adapter = _get_kernel_adapter()
session = await _adapter.submit(goal=..., mission_id=..., mode=...)
# → AdapterResult (découplé de ExecutionResult)
```

Chemin complet : `HTTP POST /api/v2/task` → `missions.py` → `KernelAdapter.submit()` → `kernel.execute(ExecutionRequest)` → `AdapterResult`.

Adaptations downstream : `AWAITING_APPROVAL` check étendu aux deux formes (enum `.value` et string `"awaiting_approval"`). `session.output` priorisé sur `.result` pour les résultats `AdapterResult`.

### Détail Pass 27 — R7 end-to-end

**`agents/kernel_bridge.py`** — nouveau module :
- `KernelStatusAgent` — agent conformant à `KernelAgentContract` (structural Protocol, pas d'héritage)
  - `agent_id = "kernel-status-agent"`, `capability_type = "system_status"`
  - `async execute()` → collecte kernel status, memory stats, gate status → `KernelAgentResult`
  - `async health_check()` → `AgentHealthStatus.HEALTHY`
- `build_and_register_kernel_agents()` — helper appelé au boot
- K1-compliant : imports kernel.contracts uniquement inside function bodies

**`main.py`** — Phase 11 (après Phase 10d) :
```python
from agents.kernel_bridge import build_and_register_kernel_agents
_registered_agents = build_and_register_kernel_agents()
# → ["kernel-status-agent"]
```

**Validation :** `KernelAgentContract conformance: True` | `registry.all_agents(): [KernelStatusAgent]` | `health_check(): healthy`

### Chemin d'exécution complet (post-Pass 29)

```
[HTTP] POST /api/v2/task
  → api/routes/missions.py::submit_task()
    → _get_kernel_adapter() [api/_deps.py]
      → interfaces.kernel_adapter.KernelAdapter.submit()
        → kernel.runtime.kernel.JarvisKernel.execute(ExecutionRequest)
          → cognitive_cycle: classify → plan → route → dispatch → evaluate → learn
        → AdapterResult (découplé)
    ← session = AdapterResult{status, output, metadata}
  → ms.complete(final=session.output)
[HTTP] 201 Created {mission_id, status, ...}
```

**KernelAgentRegistry au boot :**
```
main.py Phase 11
  → build_and_register_kernel_agents()
    → KernelAgentRegistry.register(KernelStatusAgent)
      → isinstance check (KernelAgentContract Protocol) → True
      → registry._agents["kernel-status-agent"] = agent
```

---

## Passes 19–22 (2026-03-31)

| Pass | Fichier(s) créé/modifié | Règle | Statut |
|------|------------------------|-------|--------|
| 19 | `kernel/memory/interfaces.py` → `_facade_store_fn`, `_facade_search_fn`, `search()` | R6 — MemoryFacade unifiée | ✅ |
| 20 | `interfaces/__init__.py`, `interfaces/kernel_adapter.py` | R8 — api adaptateur pur | ✅ |
| 21 | `kernel/runtime/boot.py` → security au boot, `KernelRuntime.security` | R3, R10 — governance native | ✅ |
| 22 | `tests/test_integration_kernel_security_business.py` — 31 tests | validation bout-en-bout | ✅ 31/31 |

### Nouveaux composants

**`kernel/memory/interfaces.py`** (Pass 19)
- `register_facade_store(fn)` / `register_facade_search(fn)` — registration slots R6
- `MemoryInterface.search()` — délègue à `_facade_search_fn` (K1-compliant)
- `_persist_record()` — priorise `_facade_store_fn` sur narrow execution slot
- `main.py` : Phase 10d — `register_facade_store(facade.store)` + `register_facade_search(facade.search)`

**`interfaces/`** (Pass 20)
- `interfaces/kernel_adapter.py` — `KernelAdapter.submit()` → `kernel.execute()` → `AdapterResult`
- `AdapterResult` — type externe découplé de `ExecutionResult` (R8)
- Callers API utilisent `AdapterResult`, jamais `ExecutionResult` directement

**`kernel/runtime/boot.py`** (Pass 21)
- `KernelRuntime.security` field ajouté
- Boot step 7 : `from security import get_security_layer` → `runtime.security = ...`
- `status()` expose `"security": self.security is not None`
- Boot time : ~60ms (security layer init = +6ms)

**`tests/test_integration_kernel_security_business.py`** (Pass 22)
- 7 groupes, 31 tests, 229ms d'exécution
- K1 Rule scan automatisé (kernel/contracts/, memory/, policy/, execution/, state/, security/)
- Boot kernel complet + cognitive cycle
- Security: payment → ESCALATE, critical → DENY, self_improvement gated
- Memory: facade slots, search(), _persist_record
- Business: _security_gate, strategy/finance agents
- AgentContract: structural typing, registry validation
- Interfaces: AdapterResult découpled

---

## Passes 16–18 (2026-03-31)

| Pass | Fichier(s) créé/modifié | Règle | Statut |
|------|------------------------|-------|--------|
| 16 | `kernel/contracts/agent.py` + `__init__.py` | R7 — agents sous contrat kernel | ✅ |
| 17 | `security/__init__.py`, `security/policies/`, `security/risk/`, `security/audit/` | R3, R10 — governance native | ✅ |
| 17b | `business/strategy/`, `business/finance/`, `business/layer.py` (R9 gate) | R9 — business never bypasses policy | ✅ |
| 18 | `core/meta_orchestrator.py` → `_run_kernel_cognitive_cycle()` | lisibilité, run_mission() réduite | ✅ |

### Nouveaux composants

**`kernel/contracts/agent.py`** (K1 strict)
- `KernelAgentContract` — Protocol structural typing (runtime_checkable)
- `KernelAgentResult` — dataclass output kernel-native
- `KernelAgentTask` — input contract créé par le kernel (R7)
- `KernelAgentRegistry` — registre singleton, validation par isinstance(agent, KernelAgentContract)

**`security/`** — couche de gouvernance native
- `security/policies/rules.py` — PolicyRule + PolicyRuleSet (first-match, configurable)
- `security/risk/profiles.py` — RiskProfile par action_type (SensitivityLevel: PUBLIC/INTERNAL/RESTRICTED/CONFIDENTIAL)
- `security/audit/trail.py` — AuditTrail append-only, frozen AuditEntry, JSONL file sink optionnel
- `security/__init__.py` — SecurityLayer facade (check_action → ALLOW/WARN/ESCALATE/DENY)
- Défaut: payment/data_delete/deployment → ESCALATE, critical/auto → DENY, external_api → WARN

**`business/strategy/`** + **`business/finance/`** (Pass 17b)
- 2 nouveaux agents blueprint-aligned, branchés dans BusinessLayer.intent_map
- `business/layer.py` : `_security_gate()` pour les modules sensibles (R9)

**`MetaOrchestrator._run_kernel_cognitive_cycle()`** (Pass 18)
- Extraction du bloc inline de 33 lignes vers méthode privée
- `run_mission()` : 1591 → ~1591 lignes (bloc inline → 5 lignes d'appel)
- Toutes les fallbacks (Phase 1, 0c, 1b) préservées

---

## 1. Boot Sequence (verified, `main.py`)

```
python main.py
  └─► asyncio.run(main())
        └─► config.settings.get_settings()
        └─► create_api(settings)
              └─► api.main.app  ← FastAPI singleton
              └─► @startup handler:
                    1. kernel.runtime.boot.get_runtime()        ← FIRST
                    2. memory.vector_store.VectorStore.ensure_table()
                    3. core.action_executor.get_executor().start()
        └─► uvicorn.Server.serve()
```

### Kernel Boot Subsystems (all verified operational)
- `kernel/capabilities/registry.py` — 19 capabilities registered
- `kernel/policy/engine.py` — RiskEngine + KernelPolicyEngine + ApprovalGate
- `kernel/memory/interfaces.py` — working/episodic/semantic/procedural/execution memory
- `kernel/events/canonical.py` — event emitter

Kernel observable at: `GET /kernel/status`

---

## 2. Mission Execution Path (verified, `MetaOrchestrator.run_mission()`)

```
POST /run  OR  POST /api/v2/task
  └─► MetaOrchestrator.run_mission()
        │
        ├─ KERNEL PRE-COMPUTATION  ← MetaOrchestrator._run_kernel_cognitive_cycle() (Pass 18)
        │    └─► kernel.run_cognitive_cycle(): classify → plan → route → lessons
        │        populates: ctx.metadata[classification/kernel_plan/capability_routing/routed_provider]
        │        sets: _k_classification_obj, _kernel_plan (used as fast-path below)
        │
        ├─ Phase 0a: Reasoning pre-pass (core.orchestration.reasoning_engine)
        ├─ Phase 0b: Semantic capability match (core.capabilities.semantic_router)
        ├─ Phase 0c: Capability-first routing [fast-path if kernel pre-computed, else inline]
        ├─ Phase 0c-bis: Kernel performance routing enrichment  ← NEW (Pass 2)
        │              (kernel.convergence.performance_routing.enrich_providers)
        ├─ Phase 0d: Kernel capability registry enrichment
        │              (kernel.convergence.capability_bridge.query_capabilities)
        ├─ Phase 0e: Kernel performance intelligence
        │              (kernel.capabilities.performance.get_performance_store)
        ├─ Phase 1: Mission classification
        ├─ Phase 1b: Kernel planning  ← NEW (Pass 9)
        │              (kernel.planning.planner.get_planner().build())
        │              KernelGoal(goal, task_type) → KernelPlan → ctx.metadata["kernel_plan"]
        │              Steps injected into enriched_goal at Phase 3 (executor receives plan)
        ├─ Phase 2: Context assembly (core.orchestration.context_assembler)
        │
        ├─ [CREATED → PLANNED → RUNNING]
        │
        ├─ Phase 3-kernel: Kernel policy check  ← NEW (Pass 2)
        │              (kernel.convergence.policy_bridge.check_action_kernel)
        │              Merges kernel approval requirement with classification result.
        ├─ Phase 3-kmem: Kernel working memory write  ← NEW (Pass 2)
        │              (kernel.memory.interfaces.write_working)
        │              Live mission context now visible to kernel subsystems.
        ├─ Phase 3: Supervised execution
        │              (core.orchestration.execution_supervisor.supervise)
        │              └─► delegate.run()
        │                   ├─ use_budget=True  → OrchestratorV2 (DAG/budget)
        │                   └─ use_budget=False → JarvisOrchestrator (standard)
        │
        ├─ [RUNNING → REVIEW → DONE  or  FAILED]
        │
        ├─ Phase 3a: Output formatting
        ├─ Phase 3b: Kernel learning  ← NOW AUTHORITATIVE (Pass 10)
        │              (kernel.learning.learner.get_learner().learn())
        │              KernelScore → KernelLearner.should_learn() → KernelLesson → store
        │              Fallback: core.orchestration.learning_loop if kernel unavailable
        ├─ Phase 4: Skill recording
        ├─ Phase 5: Memory facade store (core.memory_facade)
        │
        └─ Kernel working memory cleared on completion  ← NEW (Pass 2)
```

### Key Rules
- Always use `get_meta_orchestrator()` from `core` — never instantiate lower layers
- `OrchestratorV2` is an internal DAG/budget delegate, NOT deprecated

---

## 3. Public API Surface (`core/__init__.py`)

| Symbol | Status | Source |
|---|---|---|
| `MissionStatus` | ✅ Canonical | `core/state.py` |
| `JarvisSession` | ✅ Canonical | `core/state.py` |
| `SessionStatus` | ✅ Canonical | `core/state.py` |
| `MetaOrchestrator` | ✅ Canonical | `core/meta_orchestrator.py` |
| `get_meta_orchestrator` | ✅ Canonical | `core/meta_orchestrator.py` |
| `JarvisOrchestrator` | ⚠️ Shim — emits DeprecationWarning, redirects to internal class |

---

## 4. Orchestration Layer Truth

| Layer | File | Status |
|---|---|---|
| **MetaOrchestrator** | `core/meta_orchestrator.py` | ✅ CANONICAL entry point |
| **JarvisOrchestrator** | `core/orchestrator.py` | ⚙️ Internal standard delegate |
| **OrchestratorV2** | `core/orchestrator_v2.py` | ⚙️ Internal DAG/budget delegate |

`OrchestratorV2` was previously mislabelled DEPRECATED. It is **active** — used for budget-constrained missions via `MetaOrchestrator(use_budget=True)`.

---

## 5. Self-Improvement Pipeline

### Canonical (V3) — USE THIS
```
core/self_improvement/          ← canonical package
  __init__.py                   ← check_improvement_allowed(), get_self_improvement_manager()
  engine.py                     ← SelfImprovementEngine.run_cycle() (V3 facade)
  failure_collector.py
  improvement_planner.py
  candidate_generator.py
  validation_runner.py
  promotion_pipeline.py
  improvement_memory.py
```

### Other files (status clarified)
| File | Status | Reason |
|---|---|---|
| `core/self_improvement.py` | ☠️ DEAD | Shadowed by package — unreachable |
| `core/self_improvement_engine.py` | ⚠️ Superseded V2 | Use engine.py |
| `core/self_improvement_loop.py` | ✅ ACTIVE (partial) | LessonMemory class is live, used by 3 modules |

### API Routes (all mounted)
| File | Status | Prefix |
|---|---|---|
| `api/routes/self_improvement.py` | ✅ Mounted | `/self-improvement/` |
| `api/routes/self_improvement_v2.py` | ✅ NOW MOUNTED | `/api/v2/self-improvement/*` |

---

## 6. Tool System

| Registry | File | Role | Return type of list_tools() |
|---|---|---|---|
| **Executor** | `tools/tool_registry.py` | Live instances + execute | `List[str]` (tool names, merged from both) |
| **Definition** | `core/tool_registry.py` | Metadata + ranking/gap | `List[ToolDefinition]` |

```python
# Execute a tool:
from tools.tool_registry import get_tool_registry
result = get_tool_registry().execute("filesystem_tool", "read", {"path": "..."})

# Discover/rank tools:
from core.tool_registry import get_tool_registry, rank_tools_for_task
tools = get_tool_registry().list_tools()  # → List[ToolDefinition]
```

---

## 7. Memory Layers

| Layer | Location | Role | Adoption |
|---|---|---|---|
| Kernel working memory | `kernel/memory/interfaces.py` | In-mission live context | ✅ Written on mission start, cleared on end |
| Kernel episodic memory | `kernel/memory/interfaces.py` | Event history | ✅ Via event_bridge |
| Vector store | `memory/store.py` | Long-term Qdrant/PG | ✅ Booted on startup |
| Memory facade | `core/memory_facade.py` | Unified aggregator | ✅ Used by MetaOrchestrator Phase 5 |
| Decision memory | `memory/decision_memory.py` | Mission outcome records | Partial |
| Mission memory | `core/mission_memory.py` | Per-mission context | Partial |

---

## 8. Kernel Integration Status

| Integration | Status | How |
|---|---|---|
| Kernel boot | ✅ Wired | `main.py` startup handler, step 1 |
| Kernel event emission | ✅ Active | `emit_kernel_event()` on create/complete/fail |
| Kernel capability query | ✅ Active | Phase 0d in MetaOrchestrator |
| Kernel performance intelligence | ✅ Active | Phase 0e in MetaOrchestrator |
| Kernel performance routing | ✅ NOW ACTIVE | Phase 0c-bis in MetaOrchestrator |
| Kernel policy check | ✅ NOW ACTIVE | Phase 3-kernel in MetaOrchestrator |
| Kernel working memory | ✅ NOW ACTIVE | Phase 3-kmem in MetaOrchestrator |
| Kernel /kernel/status endpoint | ✅ Active | `GET /kernel/status` |
| Kernel evaluator (mission scoring) | ✅ NOW AUTHORITATIVE | Phase 8 — KernelEvaluator.evaluate() replaces dual reflect+critique blocks in MetaOrchestrator |
| Kernel evaluation registration | ✅ NOW ACTIVE | main.py registers reflect + critique_output at boot |
| Kernel planner (mission planning) | ✅ NOW AUTHORITATIVE | Phase 1b — KernelPlanner.build() produces KernelPlan, steps injected into enriched_goal at Phase 3 |
| Kernel planner registration | ✅ FIXED | main.py: core.planner.build_plan (was broken MissionPlanner().build_plan, 4 required args → TypeError) |
| Kernel learner (learning loop) | ✅ NOW AUTHORITATIVE | Phase 3b — KernelLearner.learn() replaces core extract_lesson+store_lesson in MetaOrchestrator |
| Kernel learner registration | ✅ NOW ACTIVE | main.py registers store_lesson from core.orchestration.learning_loop |

---

## 9. API Routes — ALL MOUNTED (corrected)

### Previously unmounted — now registered in api/main.py
```
system_v2.py          ✅ NOW MOUNTED → /api/system/mode/*, /api/v2/decision-memory/*, etc.
self_improvement_v2.py ✅ NOW MOUNTED → /api/v2/self-improvement/failures, /proposals, etc.
modules.py             ✅ NOW MOUNTED → /modules/agents, /modules/skills, /modules/mcp, etc.
```

### Route namespace (no conflicts verified)
```
/modules/*             ← modules.py      (agent/skill/mcp CRUD)
/api/v3/*              ← modules_v3.py   (same resources, v3 API)
/self-improvement/*    ← self_improvement.py   (role-auth endpoints)
/api/v2/self-improvement/* ← self_improvement_v2.py  (V2 endpoints)
/api/v2/system/*       ← system.py
/api/system/mode/*     ← system_v2.py
/health                ← api/main.py (Docker healthcheck, first registered, wins)
```

---

## 10. What Still Blocks Final Convergence

### Critical (true remaining gaps)
1. **JarvisOrchestrator inline** — `core/orchestrator.py` (1100+ lines) should be absorbed into `MetaOrchestrator` to remove the delegation indirection. The internal delegate is functional but creates cognitive overhead.

2. **LessonMemory extraction** — `core/self_improvement_loop.py` is 1200 lines kept alive for `LessonMemory`. Extract `LessonMemory` to `core/self_improvement/lesson_memory.py`, update 3 callers, delete the file.

3. **Memory facade completeness** — `core/memory_facade.py` is used by MetaOrchestrator Phase 5, but agent-level code still bypasses it. Full adoption would give a single memory audit path.

### Resolved in this pass
- ✅ Kernel policy, performance routing, and working memory now participate in execution
- ✅ 3 previously unmounted route files are now registered
- ✅ OrchestratorV2 correctly documented as active internal delegate
- ✅ self_improvement_loop.py status clarified

---

## 11. Developer Rules

1. **Never import `JarvisOrchestrator` directly** — use `get_meta_orchestrator()`
2. **Never import from `core/self_improvement.py`** — use `core/self_improvement/` package
3. **Never add to `core/self_improvement_engine.py`** — superseded by `engine.py`
4. **Tool execution** → `from tools.tool_registry import get_tool_registry`
5. **Tool discovery** → `from core.tool_registry import get_tool_registry`
6. **Verify kernel** → `GET /kernel/status` returns `booted: true`
7. **`OrchestratorV2` is NOT deprecated** — it is an active internal DAG delegate

---

## 12. OpenClaw Deploy Checklist

```bash
# 1. Kernel health
GET /kernel/status  →  { "booted": true, "capabilities": 19 }

# 2. API health (Docker healthcheck)
GET /health  →  { "status": "ok" }

# 3. Mission execution
POST /run {"mission": "hello", "mode": "chat"}  →  { "status": "DONE" }

# 4. New route verification
GET /api/v2/decision-memory/stats  →  200 (not 404)
GET /api/v2/self-improvement/status  →  200 (not 404)
GET /modules/agents  →  200 (not 404)

# 5. Kernel policy in mission metadata
POST /run {...}  →  response.metadata.kernel_policy.allowed == true

# 6. No DeprecationWarning in logs
grep "DeprecationWarning.*JarvisOrchestrator" logs/*.log  →  (empty)
```

---

## 13. Kernel Architecture Verdict (Pass 3)

> Voir `KERNEL_AUDIT.md` pour l'analyse complète.

**Verdict** : JarvisMax est un framework multi-agents complexe, **pas encore un AI OS avec kernel cognitif**.

Le répertoire `kernel/` contient des services d'infrastructure (contrats, politique, registre, mémoire de travail, événements) mais **ne contrôle rien**. Le vrai noyau décisionnel est `core/meta_orchestrator.py` + `core/orchestrator.py` — deux fichiers qui totalisent 2 483 lignes et n'ont pas le nom "kernel".

**La dépendance est circulaire** : kernel/ importe depuis core/ (20 fois) ET core/ importe depuis kernel/ (25 fois). Un vrai kernel ne dépend JAMAIS de ses couches gérées.

**Roadmap de transformation** (voir KERNEL_AUDIT.md — 7 phases) :
```
Phase 1 — Vérité architecturale          → 60% complété (Pass 1+2+3)
Phase 2 — Suppression des redondances    → Prochain : supprimer self_improvement_loop.py
Phase 3 — Extraction / Recentrage kernel → Créer kernel/state/ + kernel/planning/
Phase 4 — Stabilisation des interfaces   → Créer JarvisKernel class canonique
Phase 5 — Consolidation mémoire          → MemoryFacade obligatoire
Phase 6 — Auto-amélioration kernel-gatée → ImprovementGate dans kernel/
Phase 7 — AI OS mature                   → kernel/ contrôle tout
```

**Règles architecturales ajoutées (voir KERNEL_AUDIT.md section 6) :**
- K1 : kernel/ n'importe JAMAIS depuis core/, agents/, api/, tools/
- K2 : Tout accès mémoire passe par MemoryFacade
- K3 : Toute action passe par kernel/policy/engine.py — jamais fail-open
- K4 : Aucun nouveau module dans core/ sans sous-couche identifiée

---

## 14. Files Changed — Full Pass History

### Pass 1 (initial)
- `core/__init__.py` — canonical API, DeprecationWarning shim
- `core/orchestrator.py` — INTERNAL IMPLEMENTATION docstring
- `core/self_improvement/__init__.py` — bug fix + re-exposed get_self_improvement_manager
- `core/self_improvement.py` — tombstone (DEAD/SHADOWED)
- `core/self_improvement_engine.py` — tombstone (SUPERSEDED)
- `tools/tool_registry.py` — role clarification + bridge
- `core/tool_registry.py` — role clarification header
- `main.py` — kernel boot wired + /kernel/status
- `RUNTIME_TRUTH.md` — created

### Pass 2 (extended)
- `core/meta_orchestrator.py` — kernel policy check, working memory write, perf routing
- `core/orchestrator_v2.py` — corrected from DEPRECATED to active internal delegate
- `core/self_improvement_loop.py` — LessonMemory status clarified
- `api/main.py` — 3 previously unmounted routers now registered
- `api/routes/system_v2.py` — header corrected, /health conflict noted
- `api/routes/self_improvement_v2.py` — header corrected (was wrongly tombstoned)
- `api/routes/modules.py` — header corrected (was wrongly tombstoned)
- `RUNTIME_TRUTH.md` — updated (this file)

### Pass 3 (kernel audit + LessonMemory extraction)
- `core/self_improvement/lesson_memory.py` — CREATED: canonical Lesson + LessonMemory
- `core/self_improvement/__init__.py` — re-exports Lesson, LessonMemory from canonical module
- `core/self_improvement_loop.py` — Lesson+LessonMemory defs replaced by import from canonical; header corrected (JarvisImprovementLoop is canonical V3 loop, not deletable)
- `KERNEL_AUDIT.md` — CREATED: full architectural audit + verdict + roadmap 7 phases
- `RUNTIME_TRUTH.md` — section 13 kernel verdict added (this file)

### Pass 4 (kernel recentering — Phases 2-5 of roadmap)
- `kernel/adapters/policy_adapter.py` — CIRCULAR DEP FIXED: removed `from core.policy_engine import PolicyEngine`; registration pattern added (`register_core_policy_fn`); kernel-native fallback always available
- `main.py` — registers 3 callables with kernel at boot: core PolicyEngine, core MissionPlanner, MetaOrchestrator (zero circular imports)
- `kernel/state/__init__.py` — CREATED: kernel state package
- `kernel/state/mission_state.py` — CREATED: MissionContext, VALID_TRANSITIONS, MissionStateMachine, get_state_machine(); pure data, zero imports from core
- `core/meta_orchestrator.py` — imports MissionContext + VALID_TRANSITIONS from kernel/state/mission_state; _transition() uses kernel MissionStateMachine for validation
- `kernel/planning/__init__.py` — CREATED: kernel planning package
- `kernel/planning/goal.py` — CREATED: KernelGoal, KernelPlanStep, KernelPlan (pure kernel data types)
- `kernel/planning/planner.py` — CREATED: KernelPlanner with registration pattern; heuristic fallback; core MissionPlanner registered at boot
- `kernel/runtime/kernel.py` — CREATED: JarvisKernel class — single kernel entry point with .planning, .state, .policy, .memory, .capabilities, .events; submit() method; get_kernel() singleton
- `agents/crew.py` — MEMORY FACADE: _get_memory_context() now uses MemoryFacade.search_relevant() first (Kernel Rule K2); store output via MemoryFacade.store(); MemoryBus kept as fallback

### Pass 5 (kernel cognitive authority — Phase 5 of roadmap)
STATUS NOTE: Pass 5 created kernel/classifier, kernel/improvement, kernel/evaluation, kernel/routing and wired kernel.classifier in MetaOrchestrator Phase 1. However post-audit revealed: kernel.evaluator, kernel.gate, kernel.router were still DECORATIVE (registered but never called in runtime paths). Pass 6 corrected this for routing.

- `kernel/classifier/__init__.py` — CREATED: kernel classification package
- `kernel/classifier/mission_classifier.py` — CREATED: KernelTaskType, KernelComplexity, KernelRisk enums; KernelClassification dataclass; KernelClassifier with registration pattern; heuristic fallback (keyword-based, deterministic)
- `kernel/improvement/__init__.py` — CREATED: kernel improvement gating package
- `kernel/improvement/gate.py` — CREATED: ImprovementGate with hard-coded safety invariants (MAX_PER_RUN=1, COOLDOWN_HOURS=24, MAX_FAILURES=3); ImprovementDecision; registration pattern for history provider [STILL DECORATIVE — not wired to runtime]
- `kernel/evaluation/__init__.py` — CREATED: kernel evaluation package
- `kernel/evaluation/scorer.py` — CREATED: KernelEvaluator; KernelScore; heuristic scorer [STILL DECORATIVE — not called in MetaOrchestrator reflection/critique path]
- `kernel/routing/__init__.py` — CREATED: kernel routing package
- `kernel/routing/router.py` — CREATED: KernelCapabilityRouter with registration pattern [UPGRADED in Pass 6: now transparent passthrough, Phase 0c uses it]
- `kernel/runtime/kernel.py` — UPDATED to Phase 5: added .classifier, .gate, .evaluator, .router properties; convenience kernel.classify() and kernel.evaluate() methods; version bumped to 1.0.0-phase5; boot() initializes all 7 subsystems; KernelStatus extended with 4 new fields
- `core/meta_orchestrator.py` — Phase 1 WIRED TO KERNEL: tries kernel.classifier.classify() first; falls back to core.orchestration.mission_classifier.classify(); same interface (to_dict(), task_type.value, reasoning)
- `main.py` — registers 4 more callables at boot: core classifier, improvement history provider, core evaluator, core capability router (all registration pattern, zero circular imports)

### Pass 6 (kernel.router authoritative — routing réel dans Phase 0c)
WHAT CHANGED: kernel.router goes from DECORATIVE to AUTHORITATIVE for all mission routing.

BEFORE: Phase 0c in MetaOrchestrator imported `from core.capability_routing import route_mission`
directly. kernel.router existed but was never called. Routing impact is REAL (provider_id injected
into LLMFactory._provider_override contextvar → changes which LLM handles the mission).

AFTER: Phase 0c calls `from kernel.routing.router import get_router` + `_get_kernel_router().route()`.
kernel.router is the SINGLE CALL POINT for all routing. When core router registered: transparent
passthrough (RoutingDecision objects returned unchanged). When no core: heuristic with
compatible interface.

CIRCULAR DEP REDUCTION: core/meta_orchestrator → core.capability_routing.route_mission (direct)
replaced by core/meta_orchestrator → kernel.routing (OK: core→kernel, not kernel→core).

- `kernel/routing/router.py` — REWRITTEN: transparent passthrough design; removed KernelRouteDecision
  conversion (was breaking interface); added _KernelHeuristicDecision with full RoutingDecision-
  compatible interface (success, selected_provider, score, candidates_evaluated, fallback_used,
  to_dict); kernel logs all routing calls at DEBUG level; core router passthrough confirmed via test
- `kernel/routing/__init__.py` — updated exports (KernelRouteDecision removed, _KernelHeuristicDecision added)
- `core/meta_orchestrator.py` — Phase 0c: replaced `from core.capability_routing import route_mission`
  with `from kernel.routing.router import get_router as _get_kernel_router`; routing call now
  `_get_kernel_router().route(goal, classification, mode)`; remaining 2 imports of
  core.capability_routing.feedback are feedback RECORDING only (not routing)

RUNTIME PROOF: kernel_router_core_used log emitted at DEBUG → passthrough confirmed
EXECUTION IMPACT: provider_id from routing → LLMFactory._provider_override → actual LLM selection

STILL DECORATIVE (not yet wired):
- kernel.evaluator — MetaOrchestrator still uses core.orchestration.reflection + critique_output
- kernel.gate — CORRECTED in Pass 7 (see below)

### Pass 7 (kernel.gate authoritative — auto-amélioration contrôlée par le kernel)

DIAGNOSTIC AVANT:
- improvement_daemon.run_cycle() — ZÉRO gate check, chemin autonome s'exécutait sans aucune protection
- check_improvement_allowed() — implémentation locale dans core/self_improvement/__init__.py, ignorait kernel.gate
- api/routes/self_improvement_v2.py → run_improvement_cycle() — ZÉRO gate check
- kernel.gate — existait, invariants corrects, jamais appelé
- DEUX historiques séparés: daemon utilisait .improvement_lessons.json, API utilisait history.json

WHAT CHANGED:
1. core/improvement_daemon.py::run_cycle() — kernel.gate.check() INJECTÉ comme première opération,
   AVANT detect_weaknesses(). Si gate.allowed=False → return immédiat avec decision="gate_blocked".
   Après expérience réussie/échouée → get_gate().record() écrit dans history.json.
   Fail-open avec WARNING si import gate échoue (évite blocage permanent du daemon).
2. core/self_improvement/__init__.py::check_improvement_allowed() — DÉLÈGUE à kernel.gate.check()
   comme autorité primaire. L'implémentation locale reste en fallback uniquement si kernel indisponible.
   Tous les callers existants (api/routes/self_improvement.py, core/planner.py, legacy_adapter.py)
   passent maintenant automatiquement par le kernel.

CHEMINS COUVERTS PAR kernel.gate MAINTENANT:
- improvement_daemon.py autonomous loop → authoritative (was completely ungated)
- api/routes/self_improvement.py /run → authoritative (via check_improvement_allowed delegation)
- core/planner.py context check → authoritative (via check_improvement_allowed delegation)

CHEMINS ENCORE NON COUVERTS:
- api/routes/self_improvement_v2.py → calls core.self_improvement_engine.run_improvement_cycle()
  directly, no gate check. This V2 engine is a separate isolated path.
- core/self_improvement/engine.py::SelfImprovementEngine.run_cycle() — no gate check.

RUNTIME PROOF: tests 1-7 passing, including:
  - gate blocks correctly on cooldown (1h elapsed, 23h remaining)
  - gate blocks on consecutive failures (3 >= 3)
  - gate allows after 25h
  - check_improvement_allowed() propagates kernel gate block
  - daemon gate check at pos 24412 < detect_weaknesses at pos 25365 (correct order)

STILL DECORATIVE after Pass 7:
- kernel.evaluator — MetaOrchestrator reflection path still uses core.orchestration.reflection
  + critique_output() directly. kernel.evaluator never called in real execution.

### Pass 8 (kernel.evaluator authoritative — cycle mission→résultat→évaluation→retry)

DIAGNOSTIC AVANT:
- MetaOrchestrator post-execution path: TWO separate blocks: (1) reflect() → reflection_dict,
  (2) critique_output() → CritiqueResult → retry logic. Scattered, no unified score.
- kernel.evaluator — KernelEvaluator.evaluate() existed but was NEVER called in MetaOrchestrator.
- Retry threshold table lived in MetaOrchestrator (core). Kernel had no ownership of scoring logic.
- result_confidence set independently from retry logic — no unified signal.

WHAT CHANGED:
1. kernel/evaluation/scorer.py — REWRITTEN as cognitive convergence point:
   - KernelScore extended: retry_recommended, weaknesses, improvement_signals,
     improvement_suggestion, verdict, critique_dict, reflection_dict fields added
   - register_core_reflection(fn) + register_core_critique(fn) registration slots added
   - Extension slots reserved: register_skill_evaluator, register_agent_evaluator,
     register_improvement_scorer (future passes)
   - _RETRY_THRESHOLDS dict moved FROM MetaOrchestrator INTO kernel (kernel now owns retry thresholds)
   - KernelEvaluator.evaluate(): (1) calls registered reflect() fail-open,
     (2) calls registered critique_output() fail-open, (3) heuristic baseline,
     (4) _synthesize() → unified KernelScore
   - Priority in _synthesize(): confidence ← reflect > critique > heuristic;
     score ← critique.overall > reflect.confidence > heuristic;
     verdict ← reflect (learning_loop compat); weaknesses ← critique > heuristic

2. core/meta_orchestrator.py — reflection+critique+retry REPLACED by single kernel.evaluate() call:
   - Single kernel.evaluate(goal, result, task_type, mission_id, duration_ms, retries,
     output_shape, reasoning_frame) → KernelScore
   - result_confidence = kernel_score.confidence (unified signal)
   - ctx.metadata["kernel_score"] = kernel_score.to_dict()
   - Backward compat: critique_dict/reflection_dict written to ctx.metadata["critique"]/["reflection"]
   - Retry decision reads kernel_score_meta.retry_recommended + score + retry_threshold_used
   - Weaknesses/improvement_suggestion from kernel score → retry goal construction
   - Judgment signals still computed from critique_dict if reasoning frame available (no regression)

3. kernel/evaluation/__init__.py — exports: register_core_reflection, register_core_critique,
   register_skill_evaluator, register_agent_evaluator, register_improvement_scorer

4. main.py — two new registrations at boot (Phase 8):
   - register_core_reflection(core.orchestration.reflection.reflect)
   - register_core_critique(core.orchestration.reasoning_engine.critique_output)
   Both fail-open (try/except log.debug) — kernel never blocks mission on registration failure.

RUNTIME PROOF (7/7 tests passing):
  - standalone heuristic evaluate() → KernelScore with valid fields
  - empty result → retry_recommended=True, verdict="empty", confidence=0.0
  - all registration functions importable from kernel.evaluation
  - registered critique.overall overrides heuristic score (score=0.85 from mock critique)
  - registered reflection.confidence+verdict override heuristic (confidence=0.91)
  - shape-aware thresholds present in kernel (moved from meta_orchestrator)
  - KernelScore.to_dict() contains all required downstream fields

DOWNSTREAM CONSUMERS OF KernelScore (all wired in meta_orchestrator):
  result_confidence  ← kernel_score.confidence
  retry decision     ← kernel_score.retry_recommended + score vs retry_threshold_used
  retry goal         ← kernel_score.weaknesses + improvement_suggestion
  ctx.metadata       ← kernel_score / critique_dict / reflection_dict (backward compat)
  trace.record       ← score, confidence, retry, source
  learning loop      ← ctx.metadata["reflection"]["verdict"] (populated via reflection_dict)

KERNEL SUBSYSTEM STATUS AFTER PASS 8:
- kernel.classifier  ✅ AUTHORITATIVE (Phase 1 — mission classification)
- kernel.router      ✅ AUTHORITATIVE (Phase 0c — routing → LLMFactory._provider_override)
- kernel.gate        ✅ AUTHORITATIVE (improvement_daemon.run_cycle() + check_improvement_allowed())
- kernel.evaluator   ✅ AUTHORITATIVE (post-execution: reflection + critique + retry → KernelScore)
- kernel.planning    🔶 PARTIAL (KernelPlanner exists, not in mission hot path)
- kernel.state       🔶 PARTIAL (MissionStateMachine used for transitions, not full state authority)

STILL NOT KERNEL-AUTHORITATIVE:
- Mission planning (goal decomposition, plan selection) — core/orchestration/mission_planner.py
- Agent selection — core/orchestrator.py agent_registry logic
- Tool selection — core/tool_registry.py ranking
- Memory consolidation — learning loop writes to decision_memory directly

NEXT PASS TARGET:
- kernel.evaluator extension to skill scoring and tool scoring (reserved slots in scorer.py)
- OR: kernel owns learning signal → move verdict-based lesson storage into kernel.evaluator pipeline

### Pass 9 (kernel.planner authoritative — planning réel dans le cycle cognitif)

DIAGNOSTIC AVANT:
- kernel/planning/planner.py::KernelPlanner.build() — JAMAIS appelé dans MetaOrchestrator
- main.py registrait MissionPlanner().build_plan (4 args requis), KernelPlanner appelait
  _core_planner_fn(goal.description) (1 arg) → TypeError silencieuse → heuristic only
- Transition CREATED→PLANNED dans MetaOrchestrator était COSMÉTIQUE (aucun plan réel construit)
- Pas de plan structuré passé à l'executor

WHAT CHANGED:
1. main.py — registration CORRIGÉE:
   AVANT: register_core_planner(MissionPlanner().build_plan)  ← 4 args requis, TypeError silencieuse
   APRÈS: register_core_planner(core.planner.build_plan)
     core.planner.build_plan(goal, mission_type="coding_task", complexity="medium", mission_id="unknown") → dict
     1 arg obligatoire, reste optionnel → KernelPlanner l'appelle correctement
     RICHER: inclut memory facade, knowledge graph, difficulty estimation, agent routing
   Note: commentaire documente l'ancienne registration cassée pour traçabilité

2. core/meta_orchestrator.py — Phase 1b INJECTÉE entre Phase 0e et Phase 2:
   - KernelGoal(description=goal, goal_type=task_type_from_classification)
   - _get_kernel_planner().build(_kgoal) → KernelPlan
   - ctx.metadata["kernel_plan"] = _kernel_plan.to_dict()
   - trace.record("plan", "kernel_planned", steps=N, complexity=X, source=Y)
   - _kernel_plan en scope pour Phase 3

3. core/meta_orchestrator.py — Phase 3 enrichment ÉTENDU:
   - Si _kernel_plan.step_count > 1: injecte les steps dans enriched_goal
   - Format: "Execution Plan (N steps, source=X):\n  Step 1: ...\n  Step 2: ..."
   - L'executor (JarvisOrchestrator/OrchestratorV2) reçoit désormais un plan structuré
   - trace.record("plan", "kernel_plan_injected", steps=N, source=X)

RUNTIME PROOF (6/6 logic tests passing):
  - heuristic KernelPlanner.build() → valid KernelPlan
  - registered mock (1 arg, returns dict) → source=core_planner
  - core.planner.build_plan importable with keyword defaults
  - Phase 1b+3 simulation: goal → KernelPlan → enriched_goal with plan steps
  - KernelPlan steps have step_id + action for Phase 3 injection loop
  - Phase 1b wiring present in core/meta_orchestrator.py (all marker strings found)
  - main.py: build_plan import + register call confirmed (MissionPlanner only in comment)

KERNEL PLANNER FALLBACK CHAIN:
  1. core.planner.build_plan registered → PRIORITY (rich: memory + KG + difficulty)
  2. heuristic: analyse → execute → review (always available, no dependencies)

KERNEL SUBSYSTEM STATUS AFTER PASS 9:
- kernel.classifier  ✅ AUTHORITATIVE (Phase 1 — mission classification)
- kernel.router      ✅ AUTHORITATIVE (Phase 0c — routing → LLMFactory._provider_override)
- kernel.gate        ✅ AUTHORITATIVE (improvement_daemon + check_improvement_allowed)
- kernel.evaluator   ✅ AUTHORITATIVE (Pass 8 — reflection + critique + retry → KernelScore)
- kernel.planner     ✅ **AUTHORITATIVE** (Pass 9 — Phase 1b: goal → KernelPlan → injected into execution)
- kernel.planning    ✅ WIRED (KernelGoal, KernelPlan, KernelPlanStep are canonical types)
- kernel.state       🔶 PARTIAL (MissionStateMachine used for transitions, not full authority)

BOUCLE COGNITIVE KERNEL — ÉTAT D'AVANCEMENT:
  goal
  → kernel.classify   ✅ Phase 1 (authoritative)
  → kernel.plan       ✅ Phase 1b (authoritative — Pass 9)
  → kernel.route      ✅ Phase 0c (authoritative — Pass 6)
  → kernel.policy     ✅ Phase 3-kernel (active — Pass 2)
  → kernel.execute    🔶 Delegated to JarvisOrchestrator/OrchestratorV2 (Bloc 3 target)
  → kernel.evaluate   ✅ Post-execution (authoritative — Pass 8)
  → kernel.gate       ✅ improvement_daemon + check_improvement_allowed (Pass 7)
  → kernel.memory     🔶 Partial (Bloc 4 target)
  → kernel.learn      🔶 Not yet (Bloc 5 / Bloc 3 target)

### Pass 10 (kernel.learner authoritative — boucle cognitive fermée)

DIAGNOSTIC AVANT:
- Phase 3b en MetaOrchestrator: appelait core.orchestration.learning_loop.extract_lesson()
  directement → re-dérivait verdict + confidence depuis ctx.metadata (string parsing)
- kernel.evaluator (Pass 8) produisait déjà verdict, confidence, weaknesses, improvement_suggestion
  dans KernelScore — mais ces signaux n'étaient PAS utilisés pour la décision d'apprentissage
- Duplication de logique: kernel_score.improvement_suggestion disponible mais ignoré; core
  générait un texte générique basé sur le verdict string seul
- Aucun package kernel/learning/ n'existait

WHAT CHANGED:
1. kernel/learning/ — NOUVEAU PACKAGE (3 fichiers):
   - lesson.py: KernelLesson dataclass — canonical lesson type avec:
     verdict, confidence, weaknesses, improvement_suggestion depuis KernelScore
     to_dict() + to_core_lesson_dict() (compat backward)
   - learner.py: KernelLearner — décision + extraction + stockage:
     should_learn(verdict, confidence) → bool (threshold kernel-owned: confidence >= 0.8)
     extract(goal, result, mission_id, verdict, confidence, weaknesses, improvement_suggestion, ...) → KernelLesson | None
     store(lesson) → appelle _lesson_store_fn ou log.info fallback
     learn() = extract + store (fail-open, never raises)
     register_lesson_store(fn) — registration slot
   - __init__.py: exports KernelLesson, KernelLearner, get_learner, register_lesson_store
   K1 RULE: zéro import depuis core/ dans kernel/learning/

2. core/meta_orchestrator.py — Phase 3b REMPLACÉE par kernel.learn():
   - Lit KernelScore depuis ctx.metadata["kernel_score"] (Pass 8)
   - verdict = kernel_score.verdict (pas re-dérivé depuis string)
   - confidence = kernel_score.confidence (unifié)
   - weaknesses = kernel_score.weaknesses (de critique)
   - improvement_suggestion = kernel_score.improvement_suggestion (de critique)
   - _get_kernel_learner().learn(...) → KernelLesson
   - ctx.metadata["kernel_lesson"] = lesson.to_dict()
   - trace.record("learn", "kernel_lesson_extracted", verdict=..., confidence=...)
   - Fallback: core.orchestration.learning_loop.extract_lesson (si kernel unavailable)

3. main.py — registration Phase 10:
   - register_lesson_store(core.orchestration.learning_loop.store_lesson)
   - log.info("kernel_lesson_store_registered")

RUNTIME PROOF (9/9 tests passing):
  - should_learn() threshold (kernel-owned, accept+0.9→False, retry_suggested→True)
  - extract() uses improvement_suggestion > generic verdict text
  - extract() falls back to verdict-based text when no improvement_suggestion
  - registered mock store called on kernel.learn()
  - KernelLesson.to_dict() has all required fields
  - clean accept + confidence >= 0.8 → no lesson (correct suppression)
  - Phase 3b wiring present in meta_orchestrator.py (all markers found)
  - main.py registers lesson store
  - K1 rule: zero imports from core/ in kernel/learning/

COGNITIVE LOOP CLOSED — PASS 10:
  kernel.classify(goal)  →  KernelClassification
  kernel.plan(goal)      →  KernelPlan
  kernel.route(plan)     →  RoutingDecision
  kernel.policy(plan)    →  PolicyDecision
  [core executor runs]
  kernel.evaluate(result) → KernelScore (verdict, confidence, weaknesses, ...)
  kernel.learn(score)    →  KernelLesson (stored via registered lesson store)
  ↑____________________________________________________________________|
  Next mission gets memory context from stored lessons

KERNEL SUBSYSTEM STATUS AFTER PASS 10:
- kernel.classifier  ✅ AUTHORITATIVE (Phase 1)
- kernel.router      ✅ AUTHORITATIVE (Phase 0c)
- kernel.gate        ✅ AUTHORITATIVE (improvement_daemon + check_improvement_allowed)
- kernel.evaluator   ✅ AUTHORITATIVE (Pass 8)
- kernel.planner     ✅ AUTHORITATIVE (Pass 9)
- kernel.learner     ✅ **AUTHORITATIVE** (Pass 10 — boucle cognitive fermée)
- kernel.state       🔶 PARTIAL (transitions validées, pas autorité complète)
- kernel.execute     🔶 Delegated (MetaOrchestrator → JarvisOrchestrator/OrchestratorV2)
- kernel.memory      🔶 Partial (Bloc 4 cible)

NEXT PASS TARGET (Bloc 3 — orchestration):
  Option A: kernel.run(goal) as single entry point — wrap MetaOrchestrator
  Option B: simplify MetaOrchestrator → make it thin coordinator calling kernel subsystems
  Option C: kernel.learn() — move learning loop signal (verdict → lesson) into kernel
  Recommandé: Option C (kernel.learn = verdict→lesson) car ferme la boucle cognitive
  immédiatement sans risque de régression sur l'orchestration.

---

## PASS 11 — kernel.run_cognitive_cycle() : le kernel devient le cerveau cognitif

OBJECTIF: Le JarvisKernel séquence classify → plan → route EN AMONT de MetaOrchestrator.
MetaOrchestrator devient un coordinateur mince qui réutilise les résultats pré-calculés.

CHANGEMENTS APPLIQUÉS:

1. kernel/runtime/kernel.py — AJOUT: run_cognitive_cycle(goal, mode, mission_id) → dict
   Séquence:
     1. self.classify(goal)      → KernelClassification → result["classification"]
     2. self.planning.build(goal) → KernelPlan          → result["kernel_plan"]
     3. self.router.route(goal)  → RoutingDecision[]    → result["capability_routing"]
   Retourne dict avec objets Python live (_classification_obj, _kernel_plan_obj)
   + représentations sérialisées (classification, kernel_plan, capability_routing, routed_provider)
   K1 RULE: seul import interne = kernel.planning.goal.KernelGoal (kernel→kernel, autorisé)
   Fail-open: chaque étape est try/except — jamais d'exception propagée

2. core/meta_orchestrator.py — BLOC PRÉ-CALCUL (avant Phase 0b)
   Nouveau bloc: "KERNEL COGNITIVE PRE-COMPUTATION (Pass 11)"
   - Appelle _get_jk().run_cognitive_cycle(goal, mode, mission_id)
   - Stocke résultats dans ctx.metadata (classification, kernel_plan, capability_routing, routed_provider)
   - Conserve objets Python: _k_classification_obj, _kernel_plan (pour fast-path downstream)
   - Fail-open: except → log.debug("kernel_cognitive_cycle_skipped")

3. core/meta_orchestrator.py — Phase 1 (classify) FAST-PATH
   if _k_classification_obj is not None:
       classification = _k_classification_obj  # Skip classify inline
       trace.record("classify", "kernel_precomputed: ...")
   else:
       [code classify inline original — inchangé]

4. core/meta_orchestrator.py — Phase 1b (plan) FAST-PATH
   if _kernel_plan is not None:
       ctx.metadata["kernel_plan"] = _kernel_plan.to_dict()  # Skip build inline
       trace.record("plan", "kernel_planned_precomputed", ...)
   else:
       [code planner inline original — inchangé]

5. core/meta_orchestrator.py — Phase 0c (routing) FAST-PATH
   if ctx.metadata.get("capability_routing"):
       _routing_decisions = []  # No live objects — pre-computed as dicts
       trace.record("route", "capability_routed_precomputed", ...)
   else:
       [code routing inline original — inchangé]
   Phase 0c-bis (performance enrichment) s'exécute toujours (fonctionne sur les dicts)

VALIDATION (8/8 tests passing):
  1. run_cognitive_cycle exists in JarvisKernel class (AST check)
  2. run_cognitive_cycle @ char 14696 is BEFORE Phase 1 (classify) @ char 18057
  3. Phase 1 classification fast-path present (_k_classification_obj is not None)
  4. Phase 1b plan fast-path present (_kernel_plan is not None)
  5. Phase 0c routing fast-path guard present (ctx.metadata.get("capability_routing"))
  6. K1 — no direct core imports in kernel/runtime/kernel.py
  7. kernel pre-computation block variables present
  8. pre-computation block precedes Phase 1, Phase 1b, Phase 0c

SYNTAXE: py_compile clean on both files (exit 0)

ARCHITECTURE RÉELLE APRÈS PASS 11:
  user → API → MetaOrchestrator.run_mission()
                  │
                  ▼ [FIRST CALL — Pass 11]
           JarvisKernel.run_cognitive_cycle(goal)
                  │  classify → plan → route
                  │  returns pre-computed dict
                  ▼
           MetaOrchestrator uses pre-computed results
           (fast-path skips inline classify/plan/route)
                  │
                  ▼ [execution unchanged]
           JarvisOrchestrator / OrchestratorV2
                  │
                  ▼ [evaluation — Pass 8]
           kernel.evaluate() → KernelScore
                  │
                  ▼ [learning — Pass 10]
           kernel.learn() → KernelLesson

KERNEL SUBSYSTEM STATUS AFTER PASS 11:
- kernel.classifier  ✅ AUTHORITATIVE (Phase 1 + run_cognitive_cycle)
- kernel.planner     ✅ AUTHORITATIVE (Phase 1b + run_cognitive_cycle)
- kernel.router      ✅ AUTHORITATIVE (Phase 0c + run_cognitive_cycle)
- kernel.gate        ✅ AUTHORITATIVE (improvement_daemon + check_improvement_allowed)
- kernel.evaluator   ✅ AUTHORITATIVE (Pass 8)
- kernel.learner     ✅ AUTHORITATIVE (Pass 10)
- kernel.cognitive   ✅ **AUTHORITATIVE** (Pass 11 — run_cognitive_cycle séquence classify→plan→route AVANT MetaOrchestrator)
- kernel.state       🔶 PARTIAL (transitions validées, pas autorité complète)
- kernel.execute     🔶 Delegated (MetaOrchestrator → JarvisOrchestrator/OrchestratorV2)
- kernel.memory      🔶 Partial (Bloc 4 cible)

NEXT PASS TARGET (Bloc 3 — stabilisation orchestration):
  MetaOrchestrator est maintenant un coordinateur, pas le cerveau.
  Prochaine étape naturelle: simplifier MetaOrchestrator (réduire phases redondantes)
  ou Bloc 4 (memory unifiée via MemoryFacade kernel-side).

---

## PASS 12 — kernel.state K1-compliant : MissionStatus canonical dans kernel/

OBJECTIF: Fermer la dernière violation K1 dans kernel/ — kernel.state importait
`from core.state import MissionStatus`, violant la règle "kernel/ never imports from core/".

PROBLÈME:
  kernel/state/mission_state.py ligne 30:
    try:
        from core.state import MissionStatus   # ← K1 VIOLATION
    except ImportError:
        class MissionStatus(str, Enum): ...   # ← définition inline existait déjà

  Le docstring de __init__.py prétendait "no imports from core/" — mensonge.

FIX MINIMAL (2 fichiers):

1. kernel/state/mission_state.py:
   - Suppression du try/except import bloc
   - Promotion de la définition inline comme source canonique kernel
   - Nouveau commentaire: "K1 RULE: no import from core/ anywhere in this module"
   - Docstring module mis à jour: "KERNEL RULE K1: ZERO imports from core/..."

2. kernel/state/__init__.py:
   - Docstring corrigé: "K1 RULE: zero imports from core/, agents/, api/, tools/"
   - Suppression de la mention "re-exported from core.state, single source"
   - Ajout: "Note: core/state.py defines an identical MissionStatus (str, Enum)"

INTEROPÉRABILITÉ GARANTIE:
  Les deux enums (kernel.state.MissionStatus et core.state.MissionStatus) héritent
  de (str, Enum). Les membres hashent et comparent par valeur string.
  Preuve: CoreMissionStatus.DONE in {KernelMissionStatus.DONE} → True (car "DONE" == "DONE").
  MetaOrchestrator continue d'utiliser core.state.MissionStatus sans modification.
  MissionStateMachine.apply() accepte les deux variants de façon transparente.

VALIDATION (7/7 tests passing):
  1. K1 — zéro imports from core/ dans kernel/state/mission_state.py
  2. MissionStatus défini inline (kernel-canonical)
  3. Ancien core.state import supprimé
  4. str,Enum interoperability verified (core ↔ kernel dict/set lookup)
  5. MissionStateMachine fonctionnelle après fix (REVIEW→DONE valid, DONE→RUNNING invalid)
  6. __init__.py docstring corrigé (ne référence plus core.state)
  7. K1 scan clean sur tous les fichiers kernel/state/

SYNTAXE: py_compile clean sur les deux fichiers modifiés.

KERNEL SUBSYSTEM STATUS AFTER PASS 12:
- kernel.classifier  ✅ AUTHORITATIVE (Phase 1 + run_cognitive_cycle)
- kernel.planner     ✅ AUTHORITATIVE (Phase 1b + run_cognitive_cycle)
- kernel.router      ✅ AUTHORITATIVE (Phase 0c + run_cognitive_cycle)
- kernel.gate        ✅ AUTHORITATIVE (improvement_daemon + check_improvement_allowed)
- kernel.evaluator   ✅ AUTHORITATIVE (Pass 8)
- kernel.learner     ✅ AUTHORITATIVE (Pass 10)
- kernel.cognitive   ✅ AUTHORITATIVE (Pass 11 — run_cognitive_cycle)
- kernel.state       ✅ **K1-COMPLIANT** (Pass 12 — MissionStatus kernel-canonical, zero core imports)
- kernel.execute     🔶 Delegated (MetaOrchestrator → JarvisOrchestrator/OrchestratorV2)
- kernel.memory      🔶 Partial (Bloc 4 cible)

K1 RULE STATUS:
  kernel/runtime/kernel.py    — ✅ K1 clean (Pass 11)
  kernel/state/               — ✅ K1 clean (Pass 12 — résout la dernière violation connue)
  kernel/learning/            — ✅ K1 clean (Pass 10)
  kernel/evaluation/          — ✅ K1 clean (Pass 8)
  kernel/planning/            — ✅ K1 clean (Pass 9)
  kernel/routing/             — ✅ K1 clean (registration pattern)

NEXT PASS TARGET (Bloc 4 — kernel.memory + MemoryFacade):
  kernel.memory est partial: working memory write existe (Phase 3-kmem),
  mais la lecture (retrieval) pour enrichir les missions futures n'est pas
  pilotée par le kernel.
  Cible: kernel.memory.retrieve(goal) → contexte pertinent injecté dans enriched_goal
  avant l'exécution. Ferme la boucle cognitive: classify→plan→route→execute→
  evaluate→learn→[store]→retrieve→classify...

---

## PASS 13 — kernel.memory.retrieve_lessons() : boucle cognitive fermée

OBJECTIF: Fermer la boucle cognitive complète en permettant au kernel de récupérer
les leçons des missions passées et de les injecter dans enriched_goal avant exécution.
Bonus: nettoyer les 2 violations K1 pré-existantes dans kernel/memory/interfaces.py.

PROBLÈME IDENTIFIÉ:
  kernel.learn() (Pass 10) stocke des leçons via registration pattern.
  Mais kernel.memory n'avait pas de retrieve_lessons() — les leçons n'étaient
  jamais réutilisées par le kernel. La boucle cognitif restait incomplète.

  En prime: 2 violations K1 cachées dans kernel/memory/interfaces.py:
    - _persist_record(): from core.planning.execution_memory import ...
    - recall_execution_patterns(): from core.planning.execution_memory import ...

CHANGEMENTS APPLIQUÉS (5 fichiers + registration):

1. kernel/memory/interfaces.py — 3 nouvelles registration slots + méthodes K1-clean:
   - _lesson_retrieve_fn      → register_lesson_retrieve(fn)
   - _execution_persist_fn    → register_execution_persist(fn)  [K1 fix]
   - _execution_patterns_fn   → register_execution_patterns(fn) [K1 fix]
   - retrieve_lessons(goal, task_type, max_results) → list[dict] (fail-open → [])
   - _persist_record(): suppression lazy import, délègue via _execution_persist_fn
   - recall_execution_patterns(): suppression lazy import, délègue via _execution_patterns_fn

2. kernel/memory/__init__.py — exports mis à jour (register_lesson_retrieve, register_execution_persist, register_execution_patterns)

3. kernel/runtime/kernel.py — step 4 dans run_cognitive_cycle():
   _task_type = classification.get("task_type")
   _lessons = self.memory.retrieve_lessons(goal, task_type, max_results=3)
   result["kernel_lessons"] = _lessons
   log.debug("kernel_cognitive_cycle_complete", has_lessons=bool(...))

4. core/orchestration/learning_loop.py — find_relevant_lessons() ajoutée:
   Appelle memory_facade.search(goal, top_k=max_results*3)
   Filtre "[lesson]" entries, parse "goal_summary: what_to_do" format
   Retourne list[dict] avec goal_summary, what_to_do_differently, relevance

5. core/meta_orchestrator.py — injection dans enriched_goal (après plan steps):
   _kernel_lessons = _kernel_context.get("kernel_lessons", [])
   → enriched_goal += "\\n\\n---\\nKernel memory — lessons from similar tasks:\\n  [1] ..."
   trace.record("retrieve", "kernel_lessons_injected", count=...)

6. main.py — 3 nouvelles registrations:
   register_lesson_retrieve(find_relevant_lessons)     [Pass 13]
   register_execution_persist(_exec_persist_wrapper)  [K1 fix]
   register_execution_patterns(get_successful_patterns) [K1 fix]

VALIDATION (10/10 tests passing):
  1. retrieve_lessons() défini dans MemoryInterface
  2. 3 registration slots présents
  3. K1 clean — zéro imports core dans kernel/memory/interfaces.py (3 violations corrigées)
  4. step 4 retrieve dans run_cognitive_cycle()
  5. find_relevant_lessons() dans learning_loop.py
  6. kernel_lessons injectés dans enriched_goal
  7. 3 registrations dans main.py
  8. retrieve_lessons et recall_execution_patterns sont fail-open
  9. K1 full scan clean sur kernel/memory/
  10. Ordre cognitif: classify(12685) < plan(13372) < route(13747) < retrieve(14917)

SYNTAXE: py_compile clean sur les 6 fichiers modifiés.

BOUCLE COGNITIVE FERMÉE (Pass 13):
  ┌─────────────────────────────────────────────────────────────────────┐
  │  classify → plan → route → retrieve → execute → evaluate → learn   │
  │     ↑                          │                            │       │
  │     └──────────────────────────┘ ←── [store] ←────────────┘       │
  │                                                                      │
  │  kernel.run_cognitive_cycle(): 1.classify 2.plan 3.route 4.retrieve │
  │  MetaOrchestrator: injecte kernel_lessons dans enriched_goal        │
  └─────────────────────────────────────────────────────────────────────┘

KERNEL SUBSYSTEM STATUS AFTER PASS 13:
- kernel.classifier  ✅ AUTHORITATIVE
- kernel.planner     ✅ AUTHORITATIVE
- kernel.router      ✅ AUTHORITATIVE
- kernel.gate        ✅ AUTHORITATIVE
- kernel.evaluator   ✅ AUTHORITATIVE (Pass 8)
- kernel.learner     ✅ AUTHORITATIVE (Pass 10)
- kernel.cognitive   ✅ AUTHORITATIVE (Pass 11 — run_cognitive_cycle)
- kernel.state       ✅ K1-COMPLIANT  (Pass 12)
- kernel.memory      ✅ **AUTHORITATIVE** (Pass 13 — retrieve_lessons + K1 clean)
- kernel.execute     🔶 Delegated (MetaOrchestrator → JarvisOrchestrator/OrchestratorV2)

K1 RULE STATUS — COMPLET:
  kernel/runtime/kernel.py    — ✅ K1 clean
  kernel/state/               — ✅ K1 clean (Pass 12)
  kernel/learning/            — ✅ K1 clean
  kernel/evaluation/          — ✅ K1 clean
  kernel/planning/            — ✅ K1 clean
  kernel/routing/             — ✅ K1 clean
  kernel/memory/              — ✅ K1 clean (Pass 13 — 3 violations corrigées)

NEXT PASS TARGET (Bloc 3 / Stabilisation):
  kernel.execute est le dernier sous-système 🔶.
  Option A: kernel.submit() comme entry point réel (adapte retour JarvisSession ↔ dict)
  Option B: simplifier MetaOrchestrator (réduire phases redondantes maintenant que
            le kernel est le cerveau cognitif)
  Option C: pass de stabilisation — tests d'intégration runtime complets,
            benchmarks de régression, vérification end-to-end du cycle cognitif complet

---

## PASS 14 — kernel.execute() : le kernel devient le vrai point d'entrée

OBJECTIF: Créer kernel/execution/ avec les contrats ExecutionRequest/ExecutionResult
et faire de kernel.execute() l'entry point canonique pour l'API.
Ferme le dernier sous-système 🔶 (kernel.execute).

DIAGNOSTIC:
  - kernel/execution/ : inexistant
  - API → _get_orchestrator() → MetaOrchestrator.run() DIRECT (kernel bypassé)
  - kernel.submit() : registré mais jamais appelé depuis l'API
  - run_mission() retourne MissionContext objet (pas un dict)

PROBLÈME:
  R2 ("toute mission cognitive passe par kernel.run()") non respectée.
  L'API ne passait pas par le kernel — elle appelait MetaOrchestrator directement.

CHANGEMENTS APPLIQUÉS (5 fichiers):

1. kernel/execution/contracts.py — CRÉÉ (K1-compliant, pure data):
   - ExecutionStatus(str, Enum): CREATED, RUNNING, AWAITING_APPROVAL, REVIEW, DONE, FAILED, CANCELLED
   - ExecutionRequest: goal, mission_id, mode, callback, metadata, created_at + to_dict()
   - ExecutionResult: mission_id, status, result, error, metadata, goal, mode
     + get_output(agent) [compat JarvisSession]
     + final_report [property, compat JarvisSession]
     + is_terminal()
     + from_context(ctx) [classmethod — accepte MissionContext OU dict]
   - ExecutionHandle: mission_id, status, started_at

2. kernel/execution/__init__.py — CRÉÉ:
   Exports: ExecutionRequest, ExecutionResult, ExecutionHandle, ExecutionStatus

3. kernel/runtime/kernel.py — AJOUT: async execute(request) → ExecutionResult:
   Pipeline:
     1. policy check (fail-open, même pattern que submit())
     2. emit kernel.execute_started event
     3. delegate → _orchestrator_fn(goal, mode, mission_id, callback)
     4. ExecutionResult.from_context(raw) — wrap MissionContext ou dict
   Fail-open: retourne ExecutionResult(FAILED) sur exception

4. api/_deps.py — AJOUT: _get_kernel():
   Retourne JarvisKernel singleton (fail-open → None si kernel non booté)
   Usage: from api._deps import _get_kernel

5. api/routes/missions.py — MODIFICATION: call kernel.execute() en priorité:
   # AVANT:
   orch = _get_orchestrator()
   session = await orch.run(user_input=..., mode=..., session_id=...)

   # APRÈS:
   _kernel = _get_kernel()
   if _kernel is not None:
       session = await _kernel.execute(ExecutionRequest(goal, mission_id, mode))
   else:
       session = await orch.run(...)  # fallback backward compat

   ExecutionResult est compatible avec MissionContext:
   - .status (ExecutionStatus → même .value string)
   - .result (str)
   - .get_output(agent) → pour JarvisSession compat
   - .final_report → property
   L'API en aval n'a rien à changer.

BACKWARD COMPAT:
  - fallback orch.run() si _get_kernel() retourne None
  - ExecutionResult.get_output() + .final_report → compat JarvisSession
  - MissionContext attributes (status.value, result) → mappés dans from_context()

VALIDATION (10/10 tests passing):
  1. K1 clean dans kernel/execution/
  2. Imports contracts OK
  3. from_context(MissionContext-like object)
  4. from_context AWAITING_APPROVAL préservé
  5. from_context(dict)
  6. JarvisSession compat (get_output + final_report)
  7. execute() AsyncFunctionDef dans JarvisKernel
  8. API uses _get_kernel + _kernel.execute()
  9. Backward compat fallback orch.run() preserved
  10. _get_kernel() dans api/_deps.py

SYNTAXE: py_compile clean sur 5 fichiers modifiés.

KERNEL SUBSYSTEM STATUS AFTER PASS 14 — TOUS VERTS:
- kernel.classifier  ✅ AUTHORITATIVE
- kernel.planner     ✅ AUTHORITATIVE
- kernel.router      ✅ AUTHORITATIVE
- kernel.gate        ✅ AUTHORITATIVE
- kernel.evaluator   ✅ AUTHORITATIVE (Pass 8)
- kernel.learner     ✅ AUTHORITATIVE (Pass 10)
- kernel.cognitive   ✅ AUTHORITATIVE (Pass 11 — run_cognitive_cycle)
- kernel.state       ✅ K1-COMPLIANT  (Pass 12)
- kernel.memory      ✅ AUTHORITATIVE (Pass 13)
- kernel.execute     ✅ **AUTHORITATIVE** (Pass 14 — ExecutionRequest/ExecutionResult, API → kernel.execute())

PIPELINE COMPLET KERNEL-DRIVEN:
  API → kernel.execute(ExecutionRequest)
          ↓
    policy check
          ↓
    [MetaOrchestrator.run_mission() délégué]
          ↓ (à l'intérieur de run_mission)
    run_cognitive_cycle: classify → plan → route → retrieve
          ↓
    execute (JarvisOrchestrator / OrchestratorV2)
          ↓
    kernel.evaluate() → KernelScore
          ↓
    kernel.learn() → KernelLesson
          ↓
    ExecutionResult.from_context(MissionContext)
          ↓
    API response

R1  kernel/ n'importe jamais depuis core/ ✅ (K1 clean sur tous les sous-systèmes)
R2  Toute mission cognitive passe par kernel.run() ✅ (kernel.execute → via API)
R3  Toute action sensible passe par kernel.policy() ✅ (kernel.execute policy check)
R5  Tout apprentissage passe par kernel.learn() ✅ (Pass 10)

NEXT PASS TARGET (Bloc 2 — MetaOrchestrator simplification / Bloc 3 — agents layer):
  Option A: simplifier MetaOrchestrator — supprimer phases redondantes
            (classify/plan/route inline sont maintenant des fallbacks morts en pratique)
  Option B: kernel/agents/ contract layer — AgentContract Protocol, agent registry
            côté kernel (R7: "agents remplaçables, kernel autorité")
  Option C: KERNEL_AUDIT.md — cartographie complète kernel vs core vs agents
            pour identifier ce qui reste décoratif
