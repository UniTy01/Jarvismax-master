# JarvisMax — Audit d'Architecture

> Rédigé : 2026-03-19 | Auditeur : Antigravity Lead Engineer

---

## 1. Vue d'ensemble de l'existant

JarvisMax est une plateforme agentique Python async reposant sur LangChain/LangGraph,
avec des composants répartis en plusieurs couches distinctes.

### Arborescence principale

```
jarvismax/
├── agents/          # Agents spécialisés + registre AgentCrew
├── api/             # API HTTP de contrôle (stdlib http.server)
├── core/            # Orchestrateur, task router, mission system, état
├── executor/        # Exécution d'actions (runner, supervised)
├── memory/          # 4 backends mémoire (store, vector, agent, vault)
├── monitoring/      # Métriques légères
├── risk/            # Moteur de risque (LOW/MEDIUM/HIGH)
├── learning/        # LearningEngine (historique runs)
├── night_worker/    # Worker multi-cycles nuit
├── self_improve/    # Auto-amélioration du système
├── workflow/        # Moteur de workflows
├── tools/           # Outils (browser, n8n)
├── scheduler/       # Planificateur
├── tests/           # Tests (15 fichiers, validate.py ~125KB)
└── docs/            # Documentation (vide hors VALIDATION_PROTOCOL.md)
```

---

## 2. Agents Existants

| Nom | Classe | Rôle | Timeout |
|-----|--------|------|---------|
| `atlas-director` | `AtlasDirector` | Orchestration du plan (LLM, JSON) | 60s |
| `scout-research` | `ScoutResearch` | Recherche et synthèse | 120s |
| `map-planner` | `MapPlannerWithCritic` | Planification SMART + auto-critique | 120s |
| `forge-builder` | `ForgeBuilderWithCritic` | Génération de code + auto-critique | 180s |
| `lens-reviewer` | `LensReviewer` | QA et contrôle qualité | 120s |
| `vault-memory` | `VaultMemory` | Rappel mémoire (MemoryStore) | 120s |
| `shadow-advisor` | `ShadowAdvisor` | Validation critique structurée (JSON) | 30s |
| `pulse-ops` | `PulseOps` | Préparation des actions concrètes | 120s |
| `night-worker` | `NightWorker` | Worker long multi-cycles | 300s |

**Agents business (routing uniquement, pas encore implémentés dans crew.py) :**
`venture-builder`, `offer-designer`, `workflow-architect`, `saas-builder`, `trade-ops`

---

## 3. Points Forts

### ✅ Orchestration
- `JarvisOrchestrator` bien séparé du routing (`TaskRouter`)
- Lazy-loading de tous les modules (aucune dépendance circulaire au boot)
- Timeout global par mode de session (600s auto, 1800s night, etc.)
- `_compute_mission_complexity()` adaptatif (heuristique + ModelSelector)
- `AtlasDirector` → plan LLM sur mission complexe, `TaskRouter` → plan statique sinon
- Cycle de mission riche : GoalManager → routing → memory → plan → execute → observe → actions → report

### ✅ Agents
- `BaseAgent` propre avec `system_prompt()` / `user_message()` séparés
- `SelfCriticMixin` : round d'auto-critique si score < seuil
- `ShadowAdvisor V2` : JSON structuré + scorer calibré
- Injection de contexte sémantique via `_vec_ctx()` / `_mem_ctx()` / `_knowledge_ctx()`

### ✅ Exécution
- `ActionExecutor` avec handlers typés pour 10 types d'actions
- Blacklist regex absolue + whitelist pour les commandes shell
- Backup automatique avant toute modification de fichier
- `ExecutionGuard` post-écriture
- Log JSONL complet par action

### ✅ Mémoire
- 4 backends orthogonaux : MemoryStore (SQLite/JSON), VectorMemory (local embeddings),
  AgentMemory (patterns réussis per-agent), VaultMemory (mémoire structurée long-terme)
- `MemoryBus` : interface unifiée sur tous les backends

### ✅ Observabilité
- `structlog` partout avec tags bien définis
- `LLMPerformanceMonitor` : détection de drift latence/erreur
- `DecisionReplay` : audit des décisions
- `SystemState` : santé des modules
- `MetricsCollector` : métriques légères

---

## 4. Faiblesses Critiques

### ❌ API — stdlib http.server (CRITIQUE)
- `api/control_api.py` utilise `http.server.HTTPServer` + `BaseHTTPRequestHandler`
- Pas thread-safe pour les requêtes concurrentes
- Pas de validation des inputs (body parsé manuellement)
- FastAPI + Pydantic déjà dans `requirements.txt` — inutilisés
- Pas d'async : chaque requête bloque le thread

### ❌ Pas de retry/backoff dans l'executor (CRITIQUE)
- `ActionExecutor.execute()` : une erreur → échec définitif, aucune reprise
- `ParallelExecutor` : un agent qui timeout → résultat vide, pas de retry
- `tenacity` déjà dans requirements → inutilisé pour les retries

### ❌ Communication inter-agents par état mutable partagé (CRITIQUE)
- Tous les agents lisent/écrivent sur `JarvisSession` (dataclass mutable)
- Pas de contrats typés : un agent écrit `session.set_output(name, str, bool, int)`
- Pas de traçabilité de message entre agents
- Pas de corrélation possible pour le debug

### ❌ Registre d'agents hardcodé (IMPORTANT)
- `AgentCrew.__init__()` instancie manuellement 9 agents
- Impossible d'ajouter un agent sans modifier crew.py
- `AgentFactory` existe mais n'est pas branché à `AgentCrew`

### ❌ Agents manquants (IMPORTANT)
- Pas de `DebugAgent` dédié : les erreurs agents sont juste loggées, pas analysées
- Pas de `RecoveryAgent` : la reprise après erreur n'est pas orchestrée
- Pas de `MonitoringAgent` consolidé : composants épars (SystemState, LLMPerf, Metrics)
- Business agents définis dans TaskRouter mais absents de crew.py

### ❌ CrewAI / OpenAI Agents SDK inutilisés (OPPORTUNITÉ)
- `crewai` nouvellement installé
- `openai-agents-python` disponible dans GitHub/
- Aucun adaptateur entre JarvisMax et ces frameworks

### ❌ Documentation quasi-inexistante (IMPORTANT)
- Seul fichier dans `/docs/` : `VALIDATION_PROTOCOL.md`
- Pas d'architecture cible documentée
- Pas de registre d'agents
- Pas de référence API

---

## 5. Zones à Risque

| Zone | Risque | Impact |
|------|--------|--------|
| `orchestrator.py` l.464–574 | Try/except silencieux sur 8 modules | Masque des erreurs |
| `crew.py` registre hardcodé | Fragile à l'extension | Moyen |
| `control_api.py` HTTPServer | Non async, non thread-safe | Élevé |
| `executor/runner.py` whitelist regex | Trop restrictive pour certains usages | Moyen |
| `mission_system.py` JSON fallback | Perte de missions si SQLite fail | Moyen |
| `agents_plan` list[dict] | Pas de validation de schéma | Faible |

---

## 6. Duplications Identifiées

- Advisory évalué 2 fois : dans `core/mission_system.py` (heuristique) et dans `agents/crew.py ShadowAdvisor` (LLM)
- Logging d'exécution : `executor/runner.py._log()` (JSONL) et `monitoring/metrics.py` (JSON séparé)
- Backup : logique dupliquée dans `_write_file()` et `_replace_in_file()`

---

## 7. Conclusion

JarvisMax est un projet ambitieux avec une base solide et des patterns bien pensés.
L'orchestration est la partie la plus mature. Les faiblesses principales sont :
1. L'absence de retry/backoff (fiabilité d'exécution)
2. L'API non-async (scalabilité)
3. L'absence de contrats inter-agents (traçabilité et maintenabilité)
4. Les agents manquants pour la supervision et la recovery

Ces points sont adressés dans `target_architecture.md` et `implementation_plan.md`.
