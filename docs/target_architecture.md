# JarvisMax — Architecture Cible

> Version : 2.0 | Date : 2026-03-19

---

## Vue d'ensemble

```
┌─────────────────────────────────────────────────────────────────────┐
│                         COUCHE API (FastAPI)                         │
│  POST /task  GET /missions  GET /health  GET /metrics  GET /agents  │
└────────────────────────────────────┬────────────────────────────────┘
                                     │
┌────────────────────────────────────▼────────────────────────────────┐
│                      COUCHE ORCHESTRATION                            │
│  JarvisOrchestrator → TaskRouter → AtlasDirector (missions complexes)│
│  MissionLifecycle: intake→plan→dispatch→execute→validate→finalize    │
│  TaskQueue (PriorityQueue async) + DAG de dépendances               │
└──────────┬────────────────────────┬───────────────────────┬─────────┘
           │                        │                       │
┌──────────▼──────────┐  ┌──────────▼──────────┐  ┌────────▼────────┐
│   COUCHE AGENTS      │  │   COUCHE EXÉCUTION   │  │ COUCHE MÉMOIRE  │
│                      │  │                      │  │                 │
│ BaseAgent            │  │ RetryEngine          │  │ MemoryBus       │
│ ├─ ScoutResearch     │  │ TaskQueue            │  │ ├─ MemoryStore  │
│ ├─ MapPlanner        │  │ ActionExecutor       │  │ ├─ VectorMemory │
│ ├─ ForgeBuilder      │  │ SupervisedExecutor   │  │ ├─ AgentMemory  │
│ ├─ LensReviewer      │  │ ExecutionGuard       │  │ └─ VaultMemory  │
│ ├─ ShadowAdvisor     │  │ RiskEngine           │  │                 │
│ ├─ VaultMemory       │  └──────────────────────┘  └─────────────────┘
│ ├─ PulseOps          │
│ ├─ DebugAgent [NEW]  │  ┌──────────────────────┐
│ ├─ RecoveryAgent[NEW]│  │ COUCHE OBSERVABILITÉ  │
│ └─ MonitoringAgent   │  │                      │
│    [NEW]             │  │ HealthChecker [NEW]   │
│                      │  │ MetricsCollector      │
│ AgentCrew (registre) │  │ LLMPerfMonitor        │
│ AgentFactory         │  │ DecisionReplay        │
│ Adapters:            │  │ SystemState           │
│ ├─ CrewAI [NEW]      │  │ structlog (JSON)      │
│ └─ OpenAI [NEW]      │  └──────────────────────┘
└──────────────────────┘
           │
┌──────────▼──────────────────────────────────────────────────────────┐
│                     COUCHE SÉCURITÉ / GARDE-FOUS                    │
│  RiskEngine (LOW/MEDIUM/HIGH)  Blacklist  Whitelist  ShadowGate     │
│  PolicyEngine  ExecutionGuard  Backup automatique                   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Les 7 Couches

### Couche 1 — API / Interface

**Technologie :** FastAPI + Uvicorn + Pydantic v2

**Responsabilités :**
- Exposer tous les endpoints REST (v2)
- Valider les inputs avec Pydantic
- Exécuter les missions en background (FastAPI BackgroundTasks)
- Exposer les métriques et reports de santé
- Maintenir compatibilité avec l'ancienne API v1 (port 7070)

**Endpoints clés :**
```
POST   /api/v2/task                → soumettre une tâche/mission
GET    /api/v2/task/{id}           → statut d'une tâche
GET    /api/v2/tasks               → liste avec filtres (status, agent, limit)
POST   /api/v2/execute             → exécution directe sans mission
GET    /api/v2/health              → health check complet
GET    /api/v2/metrics             → métriques JSON
GET    /api/v2/diagnostics         → diagnostics détaillés
GET    /api/v2/agents              → registre agents + statuts
POST   /api/v2/agents/{id}/trigger → déclencher agent manuellement
GET    /api/v2/missions            → liste missions
GET    /api/v2/missions/{id}       → détail mission
POST   /api/v2/missions/{id}/abort → annuler mission
GET    /api/v2/logs                → logs récents (tail N)
POST   /api/v2/restart             → redémarrage contrôlé
```

---

### Couche 2 — Orchestration

**Composants :**
- `JarvisOrchestrator` : point d'entrée unique
- `TaskRouter` : routing par patterns regex (sans LLM)
- `AtlasDirector` : planning LLM pour missions complexes
- `MissionSystem` : cycle de vie complet d'une mission
- `GoalManager` : file d'objectifs et historique
- `TaskQueue` : file de tâches async avec priorité

**Cycle de vie d'une mission :**
```
1. INTAKE       — réception et validation de la mission
2. PLANNING     — routing → plan statique ou AtlasDirector
3. DISPATCH     — distribution dans TaskQueue par priorité
4. EXECUTING    — exécution parallèle des agents par groupe
5. VALIDATING   — ShadowAdvisor + LensReviewer
6. FINALIZING   — rapport final, mémorisation, métriques
7. ARCHIVED     — mission terminée, conservée en historique
```

**Gestion des erreurs :**
```
Agent échoue → RetryEngine (backoff)
               → Toujours en échec → DebugAgent
               → Debug propose fix → RecoveryAgent applique
               → Impossible → Escalation (notification)
```

---

### Couche 3 — Agents

**Contrat de base :**
Chaque agent respecte l'interface `BaseAgent` :
- `system_prompt() → str` : identité et règles de l'agent
- `user_message(session) → str` : message utilisateur contextualisé
- `run(session) → AgentResult` : exécution avec résultat typé

**Communication inter-agents :**
Les agents communiquent via `core/contracts.py` :
- Lecture : `session.get_output(agent_name)` → `AgentResult`
- Écriture : `session.set_output(name, result)` → stocke un `AgentResult`
- Messages directs : `AgentMessage(sender, recipient, payload, correlation_id)`

**Adapters (optionnels) :**
| Adapter | Frameworks | Fallback |
|---------|-----------|----------|
| `CrewAIAdapter` | CrewAI Crew + Agent + Task | JarvisMax natif |
| `OpenAIAgentsAdapter` | OpenAI Agents SDK | JarvisMax natif |

---

### Couche 4 — Exécution

**`TaskQueue`** (nouveau) :
- `asyncio.PriorityQueue` sous le capot
- États : `pending → assigned → running → succeeded / failed / retrying / cancelled`
- Isolation : chaque tâche dans son propre try/except avec état indépendant

**`RetryEngine`** (nouveau) :
- Basé sur `tenacity` (déjà dans requirements)
- Config par agent : `max_attempts=3`, `base_delay=2s`, `max_delay=30s`
- Exponential backoff avec jitter
- Retry uniquement sur erreurs transitoires (timeout, réseau)
- Pas de retry sur erreurs logiques (validation, sécurité)

**États d'une tâche :**
```
PENDING   → tâche en file d'attente
ASSIGNED  → agent sélectionné, prêt à démarrer
RUNNING   → agent en cours d'exécution
RETRYING  → échec transitoire, attente avant retry
SUCCEEDED → succès, résultat disponible
FAILED    → échec définitif (max retries atteint ou erreur logique)
CANCELLED → annulé par l'utilisateur ou mission avortée
```

---

### Couche 5 — Mémoire / État

**`MemoryBus`** : interface unifiée sur 4 backends :
| Backend | Usage | Persistence |
|---------|-------|------------|
| `MemoryStore` | Mémoire de session (SQLite/JSON) | SQLite |
| `VectorMemory` | Recherche sémantique (embeddings locaux) | Fichier local |
| `AgentMemory` | Patterns réussis par agent | JSON |
| `VaultMemory` | Mémoire structurée long-terme | SQLite |

**Questions que le système peut répondre :**
- Quelle tâche a échoué et combien de fois ?
- Quel agent l'a traitée ?
- Quelle erreur a été levée et quel retry a réussi ?
- Quel contexte a été injecté dans le prompt ?
- Quel outil a été appelé et avec quel résultat ?

---

### Couche 6 — Observabilité

**Logs structurés :**
- `structlog` avec rendu JSON en production
- Champs obligatoires : `correlation_id`, `mission_id`, `task_id`, `agent`, `ts`
- Niveaux : DEBUG, INFO, WARNING, ERROR

**Métriques :**
- `MetricsCollector` : taux de succès, latences, distribution des modes
- `LLMPerformanceMonitor` : drift latence/erreur par modèle
- `HealthChecker` (nouveau) : statut par composant (LLM, mémoire, executor, queue, API)

**Health Report :**
```json
{
  "status": "healthy | degraded | unhealthy",
  "components": {
    "llm": {"status": "ok", "latency_ms": 850, "model": "gpt-4o-mini"},
    "memory": {"status": "ok", "backend": "sqlite"},
    "executor": {"status": "ok", "queue_size": 3},
    "task_queue": {"status": "ok", "pending": 2, "running": 1}
  },
  "checked_at": "2026-03-19T01:33:55"
}
```

---

### Couche 7 — Sécurité / Garde-fous

**Actions AUTO (sans validation) :**
- Lecture (fichiers, répertoires, logs)
- Analyse et synthèse (agents LLM)
- Planification et recherche
- Backup et archivage
- Tests en environnement prévu

**Actions VALIDÉES (MEDIUM) :**
- Écriture de fichiers
- Exécution de scripts Python (workspace uniquement)
- Création de workflows
- Appels API externes

**Actions BLOQUÉES (HIGH) :**
- Suppression de fichiers système
- Commandes shell hors whitelist
- Modifications de configuration critique
- Déploiements non réversibles

---

## Flux d'une Mission Type

```
1. Utilisateur → POST /api/v2/task {"input": "Analyse le code..."}
2. API → TaskQueue.enqueue(task)
3. Orchestrateur.run() → TaskRouter.route() → mode=RESEARCH
4. Orchestrateur → vault-memory (rappel contexte)
5. Orchestrateur → [scout-research, shadow-advisor] en parallèle (P2)
6. Orchestrateur → lens-reviewer (P3)
   → Si lens-reviewer échoue → RetryEngine (max 3, backoff 2s)
   → Si tous retries échouent → DebugAgent analyse l'erreur
7. Orchestrateur → rapport final → MemoryBus.store()
8. GET /api/v2/task/{id} → status=DONE, result=...
```

---

## Points d'Extension

| Point | Mécanisme |
|-------|-----------|
| Ajouter un agent | Créer classe héritant de `BaseAgent`, enregistrer dans `AgentCrew.discover()` |
| Nouveau type d'action | Ajouter handler dans `ActionExecutor.handlers` dict |
| Nouveau backend mémoire | Implémenter interface `MemoryBackend`, enregistrer dans `MemoryBus` |
| Nouveau mode de routing | Ajouter pattern dans `TaskRouter._PATTERNS` et plan dans `_AGENT_PLANS` |
| Nouveau framework agent | Créer adapter dans `adapters/` héritant de `BaseAdapter` |
