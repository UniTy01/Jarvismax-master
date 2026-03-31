# JARVISMAX — Documentation Technique Complète
*État au 2026-03-19 — 251 tests passants, 0 échec*

---

## TABLE DES MATIÈRES

1. [Vue d'ensemble du projet](#1-vue-densemble)
2. [Architecture globale](#2-architecture-globale)
3. [Structure des fichiers](#3-structure-des-fichiers)
4. [Frameworks & dépendances](#4-frameworks--dépendances)
5. [Configuration & Settings](#5-configuration--settings)
6. [Couche Core — Cerveau du système](#6-couche-core)
7. [Les Agents — Registre complet](#7-les-agents)
8. [Mémoire — 4 couches](#8-mémoire)
9. [Auto-amélioration (Self-Improve)](#9-auto-amélioration)
10. [Couche d'exécution (Executor)](#10-couche-dexécution)
11. [Night Worker](#11-night-worker)
12. [Business Layer](#12-business-layer)
13. [Interfaces externes](#13-interfaces-externes)
14. [Observabilité & Monitoring](#14-observabilité--monitoring)
15. [Tests](#15-tests)
16. [Docker & Infrastructure](#16-docker--infrastructure)
17. [Variables d'environnement](#17-variables-denvironnement)
18. [Flux d'exécution complet](#18-flux-dexécution-complet)
19. [État actuel & Ce qui reste à faire](#19-état-actuel)

---

## 1. VUE D'ENSEMBLE

JarvisMax est un **système multi-agents IA autonome** conçu pour :
- Répondre à des missions en langage naturel
- Planifier, exécuter et superviser des tâches complexes
- S'auto-améliorer en analysant son propre code
- Fonctionner **100% en local** (Ollama/DeepSeek) avec escalade cloud optionnelle
- Tourner via un bot **Telegram** ou une **API HTTP REST**

**Chiffres clés :**
| Métrique | Valeur |
|---|---|
| Fichiers Python | 157 |
| Tests | 251 (100% passants) |
| Agents enregistrés | 12 (9 crew + 3 v2) |
| Modes d'exécution | 8 (chat, research, plan, code, auto, night, improve, business) |
| Frameworks LLM | LangChain (backbone) |
| LLMs supportés | Ollama, OpenAI, Anthropic, Google |

---

## 2. ARCHITECTURE GLOBALE

```
┌─────────────────────────────────────────────────────────────┐
│                     INTERFACES                              │
│   Telegram Bot       Control API (HTTP)     FastAPI (WIP)   │
│   /auto /night      POST /api/mission        /api/v2/*      │
│   /improve /status  GET  /api/actions                       │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                  CORE ORCHESTRATOR                          │
│   JarvisOrchestrator                                        │
│   ├── TaskRouter      → détecte le mode (chat/code/auto...) │
│   ├── AgentCrew       → dispatch vers les agents            │
│   ├── ParallelExecutor→ exécution concurrente               │
│   ├── ShadowGate      → validation critique avant actions   │
│   ├── RiskEngine      → classification des actions          │
│   ├── ActionExecutor  → application des actions             │
│   ├── ResourceGuard   → limite mémoire/agents (anti-crash)  │
│   └── LearningLoop    → apprentissage post-session          │
└──────┬──────────────────┬───────────────────────────────────┘
       │                  │
┌──────▼───────┐  ┌───────▼──────────────────────────────────┐
│   AGENTS     │  │           LLM FACTORY                    │
│  (12 agents) │  │   LLMFactory                             │
│              │  │   ├── Routing par rôle                   │
│  AtlasDir.   │  │   ├── Circuit breaker Ollama             │
│  ScoutRes.   │  │   ├── Fallback cloud automatique         │
│  MapPlanner  │  │   ├── safe_invoke() unifié               │
│  ForgeBuilder│  │   └── Langfuse tracer (optionnel)        │
│  LensReviewer│  │                                          │
│  VaultMemory │  │   PROVIDERS :                            │
│  ShadowAdvis │  │   ollama → openai → anthropic → google   │
│  PulseOps    │  └──────────────────────────────────────────┘
│  NightWorker │
│  DebugAgent  │  ┌───────────────────────────────────────────┐
│  RecovAgent  │  │           MÉMOIRE (4 couches)            │
│  MonitAgent  │  │   MemoryBus                              │
└──────────────┘  │   ├── MemoryStore  (PostgreSQL/Redis/RAM)│
                  │   ├── VectorMemory (TF-IDF + embeddings) │
                  │   ├── PatchMemory  (patterns réussis)    │
                  │   └── FailureMemory(erreurs passées)     │
                  └───────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│              SELF-IMPROVE PIPELINE                          │
│   Audit → Plan → Build → Review → [Validation Telegram]     │
│        → Apply → Test → Journal                             │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│              INFRASTRUCTURE DOCKER                          │
│   PostgreSQL  Redis  Qdrant  Ollama  n8n  Langfuse          │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. STRUCTURE DES FICHIERS

```
jarvismax/
├── jarvis.py               # Entrypoint CLI principal
├── main.py                 # Entrypoint FastAPI (développement)
├── start_api.py            # Lance l'API de contrôle (port 7070)
│
├── config/
│   └── settings.py         # Configuration centrale (@dataclass + lru_cache)
│
├── core/                   # Cerveau du système (35 fichiers)
│   ├── state.py            # JarvisSession, ActionSpec, RiskLevel (types partagés)
│   ├── orchestrator.py     # JarvisOrchestrator — chef d'orchestre
│   ├── task_router.py      # TaskRouter — routing par intention (regex)
│   ├── llm_factory.py      # LLMFactory — routing LLM, circuit breaker, safe_invoke
│   ├── mission_system.py   # MissionSystem — cycle de vie missions
│   ├── action_queue.py     # ActionQueue — queue des actions à exécuter
│   ├── action_executor.py  # ActionExecutor — applique les actions
│   ├── shadow_gate.py      # ShadowGate — verrou ShadowAdvisor
│   ├── resource_guard.py   # ResourceGuard — anti-crash RAM/agents [NOUVEAU]
│   ├── reasoning_framework.py # Patterns OHVC, fact_check, anti_halluc
│   ├── contracts.py        # Types partagés (AgentResult, HealthReport...)
│   ├── event_stream.py     # EventStream — journal append-only
│   ├── mission_repair.py   # Répare missions APPROVED bloquées
│   └── [+ 21 autres]       # db, decision_replay, escalation_engine...
│
├── agents/                 # Agents spécialisés
│   ├── crew.py             # BaseAgent + 9 agents + AgentCrew registry
│   ├── parallel_executor.py # ParallelExecutor — asyncio.gather + ResourceGuard
│   ├── shadow_advisor/
│   │   ├── schema.py       # AdvisoryReport, parse_advisory()
│   │   └── scorer.py       # AdvisoryScorer — recalibre décision + score
│   ├── debug_agent.py      # DebugAgent — analyse pannes
│   ├── recovery_agent.py   # RecoveryAgent — rollback, reprise
│   ├── monitoring_agent.py # MonitoringAgent — HealthReport
│   ├── web_scout.py        # WebScout — Playwright + DuckDuckGo
│   ├── workflow_agent.py   # WorkflowAgent — création workflows n8n
│   ├── self_critic.py      # SelfCriticMixin — auto-critique avant livraison
│   ├── evaluator.py        # Evaluator — évalue qualité des agents
│   └── autonomous/
│       ├── devin_agent.py  # DevinAgent — agent autonome ReAct
│       └── scout_agent.py  # ScoutAgent — research autonome
│
├── memory/                 # 4 couches mémoire
│   ├── memory_bus.py       # MemoryBus — interface unifiée
│   ├── store.py            # MemoryStore — PostgreSQL/Redis/in-memory
│   ├── vector_memory.py    # VectorMemory — TF-IDF + sentence-transformers
│   ├── patch_memory.py     # PatchMemory — patterns de patchs réussis
│   ├── failure_memory.py   # FailureMemory — erreurs passées
│   ├── agent_memory.py     # AgentMemory — mémoire per-agent
│   ├── knowledge_memory.py # KnowledgeMemory — connaissances validées
│   └── vault_memory.py     # VaultMemory — stockage long terme
│
├── self_improve/           # Auto-amélioration (8 modules)
│   ├── pipeline.py         # ImprovePipeline — orchestrateur 8 étapes
│   ├── auditor.py          # Auditor — détecte les problèmes dans le code
│   ├── patch_builder.py    # PatchBuilder — génère les patchs LLM
│   ├── regression_reviewer.py # RegressionReviewer — filtre les patchs risqués
│   ├── sandbox.py          # ImproveSandbox — test des patchs en isolation
│   ├── patch_journal.py    # PatchJournal — historique des patchs
│   ├── pending_store.py    # PendingPatchStore — survit aux redémarrages
│   └── models.py           # PatchSpec, AuditFinding, PatchStatus...
│
├── executor/               # Moteur d'exécution
│   ├── execution_engine.py # ExecutionEngine v2 — heapq + retry + timeout
│   ├── task_model.py       # ExecutionTask, ExecutionResult
│   ├── retry_policy.py     # RetryPolicy — backoff exponentiel
│   ├── handlers.py         # Handlers par type de tâche
│   ├── supervised_executor.py # SupervisedExecutor — exécution avec validation
│   ├── risk_engine.py      # RiskEngine — classification LOW/MEDIUM/HIGH
│   ├── task_queue.py       # TaskQueue — queue persistante
│   └── desktop_env/        # Sandbox local (Terminal, Editor, Browser)
│
├── learning/               # Apprentissage continu
│   ├── learning_loop.py    # LearningLoop — observe → extrait → valide → stocke
│   ├── learning_engine.py  # LearningEngine — moteur principal
│   ├── knowledge_validator.py # Valide les connaissances (KEEP/DISCARD/NEEDS_TEST)
│   ├── knowledge_filter.py # Filtre les connaissances redondantes
│   └── web_learning_engine.py # Apprentissage depuis le web
│
├── business/               # Business Layer (5 domaines)
│   ├── layer.py            # BusinessLayer — orchestrateur
│   ├── venture/            # Analyse d'opportunités business
│   ├── offer/              # Design d'offres commerciales
│   ├── saas/               # Blueprint SaaS/MVP
│   ├── trade_ops/          # Agents métiers (artisans, TPE)
│   ├── workflow/           # Automatisation business
│   └── meta_builder/       # Duplication d'agents business
│
├── night_worker/           # Travaux longs autonomes
│   ├── worker.py           # NightWorkerEngine — cycles autonomes
│   └── scheduler.py        # NightScheduler — planification
│
├── monitoring/
│   └── metrics.py          # MetricsCollector — JSON append-only
│
├── observability/          # [NOUVEAU]
│   └── langfuse_tracer.py  # LangfuseTracer — traçage LLM optionnel
│
├── api/
│   ├── control_api.py      # Control API stdlib HTTP (port 7070) — EN PROD
│   └── main.py             # FastAPI (port 8000) — EN DÉVELOPPEMENT
│
├── jarvis_bot/
│   └── bot.py              # Bot Telegram — interface principale
│
├── tools/
│   ├── browser/scraper.py  # WebScraper Playwright + DuckDuckGo
│   └── n8n/bridge.py       # N8nBridge — API REST n8n
│
├── workflow/
│   └── workflow_engine.py  # WorkflowEngine — création/exécution workflows
│
├── risk/
│   └── engine.py           # RiskEngine — classification des actions
│
├── scheduler/
│   └── night_scheduler.py  # NightScheduler — tâches planifiées
│
├── docker/
│   ├── Dockerfile          # Image Python 3.12 slim
│   └── postgres/init.sql   # Initialisation DB
│
├── docker-compose.yml      # Stack complète
├── requirements.txt        # Dépendances Python
├── .env.example            # Template configuration
└── tests/                  # 251 tests, 15 fichiers
```

---

## 4. FRAMEWORKS & DÉPENDANCES

### LLM / IA
| Package | Version | Rôle |
|---|---|---|
| `langchain` | >=0.2.0 | Backbone LLM — messages, abstractions |
| `langchain-core` | >=0.2.0 | BaseChatModel, SystemMessage, HumanMessage |
| `langchain-openai` | >=0.1.0 | Provider OpenAI (gpt-4o, gpt-4o-mini) |
| `langchain-anthropic` | >=0.1.0 | Provider Anthropic (claude-3-5-sonnet) |
| `langchain-google-genai` | >=1.0.0 | Provider Google (gemini-1.5-pro) |
| `langchain-ollama` | >=0.1.0 | Provider Ollama (llama3.1, deepseek-coder, mistral) |
| `langchain-community` | >=0.2.0 | Utilitaires communautaires |
| `openai` | >=1.30.0 | SDK OpenAI direct (embeddings) |
| `sentence-transformers` | >=3.0.0 | Embeddings locaux pour VectorMemory |

> **Note importante** : LangGraph est installé mais **n'est pas utilisé** dans le code. Dépendance morte à nettoyer ou à utiliser pour le human-in-loop.

### API & Serveur
| Package | Version | Rôle |
|---|---|---|
| `fastapi` | >=0.111.0 | API REST (en développement, non en prod) |
| `uvicorn` | >=0.30.0 | Serveur ASGI |
| `httpx` | >=0.27.0 | Client HTTP async |
| `pydantic` | >=2.7.0 | Validation de données |
| `python-telegram-bot` | >=21.0 | Interface Telegram |

### Bases de données & Stockage
| Package | Version | Rôle |
|---|---|---|
| `asyncpg` | >=0.29.0 | PostgreSQL async |
| `psycopg2-binary` | >=2.9.9 | PostgreSQL sync |
| `redis` | >=5.0.0 | Cache Redis |
| `qdrant-client` | >=1.9.0 | Mémoire vectorielle Qdrant |

### Outils
| Package | Version | Rôle |
|---|---|---|
| `playwright` | >=1.44.0 | Browser automation (WebScout) |
| `structlog` | >=24.1.0 | Logging structuré JSON (113 fichiers) |
| `tenacity` | >=8.3.0 | Retry avec backoff |
| `psutil` | >=5.9.0 | Monitoring RAM/CPU (ResourceGuard) |
| `langfuse` | >=2.0.0 | Traçage LLM optionnel (self-hosted) |

---

## 5. CONFIGURATION & SETTINGS

**Fichier** : `config/settings.py`
**Pattern** : `@dataclass` + `@lru_cache` singleton, pas de pydantic-settings

```python
from config.settings import get_settings
s = get_settings()  # singleton — même instance partout
```

### Paramètres principaux

| Variable ENV | Défaut | Description |
|---|---|---|
| `JARVIS_NAME` | `JarvisMax` | Nom du système |
| `WORKSPACE_DIR` | `./workspace` | Répertoire de travail |
| `JARVIS_MODE` | `local` | `local` (2 agents max) ou `vps` (5 agents max) |
| `JARVIS_SAFE_MODE` | `false` | Force le mode SAFE (1 agent simultané) |
| `DRY_RUN` | `false` | Simule sans écrire sur le disque |
| `MAX_AUTO_ACTIONS` | `25` | Limite d'actions automatiques par session |

### LLM
| Variable ENV | Défaut | Description |
|---|---|---|
| `OPENAI_API_KEY` | — | Clé OpenAI |
| `OPENAI_MODEL` | `gpt-4o` | Modèle principal |
| `OPENAI_MODEL_FAST` | `gpt-4o-mini` | Modèle rapide |
| `ANTHROPIC_API_KEY` | — | Clé Anthropic |
| `ANTHROPIC_MODEL` | `claude-3-5-sonnet-20241022` | Modèle Anthropic |
| `GOOGLE_API_KEY` | — | Clé Google |
| `OLLAMA_HOST` | `http://ollama:11434` | Hôte Ollama |
| `OLLAMA_MODEL_MAIN` | `llama3.1:8b` | Modèle généraliste |
| `OLLAMA_MODEL_CODE` | `deepseek-coder-v2:16b` | Modèle code |
| `OLLAMA_MODEL_FAST` | `mistral:7b` | Modèle rapide |
| `MODEL_STRATEGY` | `openai` | Provider principal |
| `ESCALATION_ENABLED` | `false` | Activer le fallback cloud |

### Rôles LLM et leurs providers
```
director  → openai (gpt-4o)        — Planification mission
research  → ollama/deepseek-coder   — Recherche & synthèse
planner   → ollama/llama3.1         — Planification
builder   → ollama/deepseek-coder   — Génération code (LOCAL_ONLY)
reviewer  → ollama/llama3.1         — Review qualité (LOCAL_ONLY)
memory    → ollama/mistral          — Mémoire (LOCAL_ONLY)
advisor   → ollama → openai         — Shadow Advisor (fallback cloud OK)
ops       → openai                  — PulseOps
fast      → openai/gpt-4o-mini      — Appels rapides
```

---

## 6. COUCHE CORE

### 6.1 JarvisSession — État partagé (`core/state.py`)

Objet central passé à travers tout le pipeline. **Source unique de vérité** pour une session.

```python
@dataclass
class JarvisSession:
    session_id:       str          # UUID unique
    user_input:       str          # Texte original de l'utilisateur
    mode:             str          # "auto" | "chat" | "code" | "night" | "improve"
    mission_summary:  str          # Résumé de la mission (défini par AtlasDirector)
    agents_plan:      list[dict]   # Plan [{agent, task, priority}] (défini par AtlasDirector)
    needs_actions:    bool         # True si PulseOps doit générer des actions
    outputs:          dict[str, AgentOutput]  # Résultats de chaque agent
    actions_pending:  list[ActionSpec]        # Actions à valider/exécuter
    actions_executed: list[dict]             # Actions déjà exécutées
    actions_rejected: list[dict]             # Actions refusées
    auto_count:       int          # Compteur d'actions auto (limite MAX_AUTO_ACTIONS)
    metadata:         dict         # shadow_advisory, shadow_score, shadow_decision
    status:           SessionStatus # RUNNING | WAITING_VALIDATION | COMPLETED | ERROR
    event_stream:     EventStream   # Journal append-only des événements
    night_cycle:      int           # Numéro de cycle NightWorker
    night_productions: list[str]   # Productions par cycle
```

**Méthodes clés :**
- `set_output(agent, content, success)` — enregistre le résultat d'un agent + émet un Event
- `get_output(agent)` — récupère le résultat d'un agent (vide si échec)
- `context_snapshot(limit)` — dict des outputs réussis (pour prompts)
- `ctx_block(skip, limit)` — bloc texte formaté pour injection dans prompts

### 6.2 TaskRouter (`core/task_router.py`)

Détecte le **mode** d'exécution par regex, **sans LLM**.

```
BUSINESS → /venture|opportunite|offre commerciale|saas|trade_ops|...
IMPROVE  → /ameliore|auto-ameli|corrige tes bug|/improve|...
NIGHT    → /night|travail de nuit|mission longue|multi-cycle|...
CODE     → écris un script|génère du code|implémente|...
PLAN     → planifie|roadmap|étapes pour|stratégie|...
RESEARCH → recherche|synthétise|qu'est-ce que|comment fonctionne|...
CHAT     → message < 30 chars ou salutation
AUTO     → tout le reste
```

**Agents sélectionnés par mode :**
| Mode | Agents mobilisés | needs_actions |
|---|---|---|
| CHAT | shadow-advisor | false |
| RESEARCH | vault-memory, scout-research, shadow-advisor, lens-reviewer | false |
| PLAN | vault-memory, scout-research, map-planner, shadow-advisor, lens-reviewer | false |
| CODE | vault-memory, scout-research, forge-builder, shadow-advisor, lens-reviewer, pulse-ops | true |
| AUTO | vault-memory, atlas-director, scout-research, shadow-advisor, map-planner, forge-builder, lens-reviewer, pulse-ops | true |
| IMPROVE | (self_improve pipeline) | — |
| NIGHT | vault-memory, atlas-director, night-worker | true |
| BUSINESS | (BusinessLayer) | — |

### 6.3 LLM Factory (`core/llm_factory.py`)

```python
factory = LLMFactory(settings)
resp = await factory.safe_invoke(messages, role="fast", timeout=60.0,
                                  session_id="...", agent_name="scout")
```

**Architecture interne :**
```
safe_invoke(messages, role, timeout, session_id, agent_name)
  ├── LangfuseTracer.generation(...)    # trace optionnelle
  ├── OllamaCircuitBreaker.allow()      # fail-fast si Ollama down
  ├── llm.ainvoke(messages)             # tentative principale
  │   ├── succès → record_success() + métriques + gen_ctx.finish()
  │   └── échec  → record_failure() + métriques + gen_ctx.finish(error)
  └── fallback cloud (si role non LOCAL_ONLY)
      ├── essaie openai → anthropic → google dans l'ordre
      └── raise TimeoutError si tout échoue
```

**Circuit breaker Ollama :**
- 3 échecs en 60s → OPEN (fallback cloud activé)
- 30s après → HALF-OPEN (test de récupération)
- 1 succès → CLOSED (retour normal)

### 6.4 Reasoning Framework (`core/reasoning_framework.py`)

Blocs de raisonnement injectés dans les prompts système des agents.

```python
INJECT_SCOUT    = inject(["ohvc", "fact_check", "anti_halluc"])
INJECT_PLANNER  = inject(["decompose", "risk", "proof"])
INJECT_BUILDER  = inject(["fact_check", "anti_halluc", "proof"])
INJECT_REVIEWER = inject(["proof", "fact_check", "risk"])
INJECT_ADVISOR  = inject(["compare", "risk", "anti_halluc"])
```

**Patterns disponibles :**
- `OHVC` : Observation → Hypothèse → Vérification → Conclusion
- `DECOMPOSE` : décomposition en sous-problèmes
- `COMPARE` : comparaison multi-options
- `RISK` : analyse probabilité × impact
- `PROOF` : validation par preuve — [NON PROUVÉ] obligatoire
- `FACT_CHECK` : ✅ FAIT / ⚠️ HYPOTHÈSE / ❓ INCONNU / ❌ HALLUC
- `ANTI_HALLUC` : règle absolue contre l'invention de faits

### 6.5 ResourceGuard (`core/resource_guard.py`) [NOUVEAU]

Protège la machine contre les crashs OOM. Créé suite au crash 2026-03-19.

```python
guard = get_resource_guard(settings)
ok, reason = guard.check_before_agent("scout-research")
if ok:
    acquired = guard.acquire_slot("scout-research")
    try:
        # ... exécuter l'agent
    finally:
        guard.release_slot("scout-research")
```

**Profils :**
| | LOCAL | VPS |
|---|---|---|
| `JARVIS_MODE` | `local` | `vps` |
| Agents max simultanés | 2 | 5 |
| RAM → WARNING | < 2048 MB | < 4096 MB |
| RAM → SAFE (1 agent) | < 1024 MB | < 2048 MB |
| RAM → BLOCKED | < 512 MB | < 1024 MB |

**Statuts :** `NORMAL` → `SOFT_WARN` → `SAFE` → `BLOCKED` → `UNKNOWN` (si psutil absent)

### 6.6 ShadowGate (`core/shadow_gate.py`)

Verrou entre l'orchestrateur et les actions critiques. Bloque si :
- Decision ShadowAdvisor = `NO-GO`
- Score < 3.5/10

```python
gate = ShadowGate(session)
result = gate.check()
if result.is_blocked():
    # Arrêter — ShadowAdvisor a refusé
```

---

## 7. LES AGENTS

### Architecture BaseAgent

Tous les agents héritent de `BaseAgent` (`agents/crew.py`) :

```python
class BaseAgent(ABC):
    name:      str  # Identifiant unique (ex: "scout-research")
    role:      str  # Rôle LLM (ex: "research") → LLMFactory.get(role)
    timeout_s: int  # Timeout de l'appel LLM

    async def run(session: JarvisSession) -> str
    # Pipeline : system_prompt() + user_message() → safe_invoke() → set_output()
```

**Helpers disponibles dans BaseAgent :**
- `_task(session)` — récupère la tâche assignée à cet agent dans le plan
- `_ctx(session, skip, limit)` — snapshot des outputs des autres agents (pour prompt)
- `_mem_ctx(n)` — contexte AgentMemory (patterns réussis passés)
- `_knowledge_ctx(query, n)` — connaissances validées depuis KnowledgeMemory
- `_vec_ctx(query, n, min_score)` — recherche sémantique VectorMemory

### Registre des 12 Agents

#### 1. AtlasDirector
| Attribut | Valeur |
|---|---|
| **Clé** | `atlas-director` |
| **Rôle LLM** | `director` (openai gpt-4o) |
| **Timeout** | 60s |
| **Mission** | Chef d'orchestre — décompose la mission en plan d'agents |
| **Sortie** | JSON : `{mission_summary, needs_actions, tasks[], reasoning}` |
| **Particularité** | Parse le JSON et peuple `session.mission_summary` + `session.agents_plan` |

**Prompt système :**
Décompose en tâches pour les agents disponibles. Priorise `openhands` pour le code complexe. Répond uniquement en JSON.

---

#### 2. ScoutResearch
| Attribut | Valeur |
|---|---|
| **Clé** | `scout-research` |
| **Rôle LLM** | `research` (ollama/deepseek) |
| **Timeout** | 120s |
| **Mission** | Recherche, analyse, synthèse d'informations |
| **Sortie** | Markdown structuré : Synthèse, Faits clés, Tendances, Risques, Limites |
| **Inject** | `INJECT_SCOUT` (OHVC + fact_check + anti_halluc) |
| **Mémoire** | Injecte vec_ctx, mem_ctx, knowledge_ctx dans le prompt |

---

#### 3. MapPlanner (avec SelfCriticMixin)
| Attribut | Valeur |
|---|---|
| **Clé** | `map-planner` |
| **Rôle LLM** | `planner` (ollama/llama3.1) |
| **Timeout** | 120s |
| **Mission** | Transformer des objectifs en plans avec jalons SMART |
| **Sortie** | Markdown : Objectif, MVP, Jalons, Dépendances, Risques, Effort |
| **Inject** | `INJECT_PLANNER` (decompose + risk + proof) |
| **Auto-critique** | `SelfCriticMixin` — si score < 6.0 → 1 round de révision |

---

#### 4. ForgeBuilder (avec SelfCriticMixin)
| Attribut | Valeur |
|---|---|
| **Clé** | `forge-builder` |
| **Rôle LLM** | `builder` (ollama/deepseek-coder — LOCAL_ONLY) |
| **Timeout** | 180s |
| **Mission** | Génération de code Python/Shell/YAML production-ready |
| **Sortie** | Markdown : Description, Code (bloc ```python), Utilisation, Tests recommandés |
| **Inject** | `INJECT_BUILDER` (fact_check + anti_halluc + proof) |
| **Auto-critique** | `SelfCriticMixin` — si score < 6.5 → 1 round de révision |
| **Standards** | Type hints, gestion d'erreurs explicite, pas de hardcoding |

---

#### 5. LensReviewer
| Attribut | Valeur |
|---|---|
| **Clé** | `lens-reviewer` |
| **Rôle LLM** | `reviewer` (ollama — LOCAL_ONLY) |
| **Timeout** | 120s |
| **Mission** | Contrôle qualité des travaux des autres agents |
| **Sortie** | Score /10, Points forts, Problèmes, Risques sécurité, Améliorations, Verdict |
| **Verdict** | `APPROUVÉ` / `APPROUVÉ_AVEC_RÉSERVES` / `REFUSÉ` |
| **Règle** | Note < 6/10 = REFUSÉ obligatoire |
| **Inject** | `INJECT_REVIEWER` (proof + fact_check + risk) |

---

#### 6. VaultMemory
| Attribut | Valeur |
|---|---|
| **Clé** | `vault-memory` |
| **Rôle LLM** | `memory` (ollama — LOCAL_ONLY) |
| **Timeout** | 120s |
| **Mission** | Rappel et synthèse de la mémoire contextuelle |
| **Particularité** | Fait un `MemoryStore.search()` AVANT l'appel LLM |
| **Sortie** | Résumé du contexte mémorisé + ce qui devrait être retenu |

---

#### 7. ShadowAdvisor V2
| Attribut | Valeur |
|---|---|
| **Clé** | `shadow-advisor` |
| **Rôle LLM** | `advisor` (ollama → openai fallback OK, 30s timeout) |
| **Timeout** | 30s |
| **Mission** | Validateur critique structuré — détecter ce qui peut échouer |
| **Sortie** | JSON strict : decision, confidence, blocking_issues[], risks[], improvements[], final_score |
| **Décisions** | `GO` / `IMPROVE` / `NO-GO` |
| **Post-processing** | AdvisoryScorer recalibre le score + ShadowGate utilise la décision |
| **Inject** | `INJECT_ADVISOR` (compare + risk + anti_halluc) |
| **Processus** | 6 questions : Que peut casser ? Suppositions ? Ce qui manque ? Contradiction ? Pire conséquence ? Amélioration principale ? |

**Structure JSON de sortie :**
```json
{
  "decision": "GO|IMPROVE|NO-GO",
  "confidence": 0.85,
  "blocking_issues": [{"type": "securite", "description": "...", "severity": "high"}],
  "risks": [{"type": "...", "probability": "medium", "impact": "high"}],
  "weak_points": ["..."],
  "improvements": ["..."],
  "tests_required": ["..."],
  "final_score": 7.2,
  "justification": "..."
}
```

---

#### 8. PulseOps
| Attribut | Valeur |
|---|---|
| **Clé** | `pulse-ops` |
| **Rôle LLM** | `ops` (openai) |
| **Timeout** | 120s |
| **Mission** | Traduire les outputs agents en actions JSON concrètes |
| **Sortie** | JSON : `{actions: [{action_type, target, content, description, reversible}], summary}` |
| **Types d'action** | `create_file`, `write_file`, `replace_in_file`, `run_command`, `backup_file` |
| **Particularité** | Peuple `session._raw_actions` — traités ensuite par RiskEngine |

---

#### 9. NightWorker
| Attribut | Valeur |
|---|---|
| **Clé** | `night-worker` |
| **Rôle LLM** | `builder` (ollama/deepseek) |
| **Timeout** | 300s |
| **Mission** | Production de livrables sur missions longues multi-cycles |
| **Sortie** | JSON : analysis, production, review, next_steps, should_continue, progress_percent, files_to_create[] |
| **Usage** | Appelé par NightWorkerEngine en boucle (max 5 cycles) |

---

#### 10. DebugAgent (v2)
| Attribut | Valeur |
|---|---|
| **Clé** | `debug-agent` |
| **Rôle LLM** | `builder` (deepseek — LLM puissant) |
| **Timeout** | 90s |
| **Mission** | Analyser les erreurs agents et proposer des corrections |
| **Déclencheur** | Agent échoue 2+ fois ou RetryEngine épuisé |
| **Sortie** | `{fix_proposal, root_cause, confidence, is_auto_fixable}` |

---

#### 11. RecoveryAgent (v2)
| Attribut | Valeur |
|---|---|
| **Clé** | `recovery-agent` |
| **Rôle LLM** | `advisor` (ollama) |
| **Timeout** | 60s |
| **Mission** | Rollback et reprise contrôlée après erreur |
| **Stratégies** | ROLLBACK, SKIP, PARTIAL_RETRY, ESCALATE, ABORT |
| **Sécurité** | Path traversal protection — liste blanche de répertoires autorisés |

---

#### 12. MonitoringAgent (v2)
| Attribut | Valeur |
|---|---|
| **Clé** | `monitoring-agent` |
| **Rôle LLM** | Aucun (collecteur système pur) |
| **Mission** | Collecter la santé de tous les composants |
| **Sortie** | `HealthReport` avec `ComponentHealth` pour LLM, Memory, Executor, Telegram |

---

### Agents supplémentaires (hors AgentCrew)

| Agent | Fichier | Rôle |
|---|---|---|
| **WebScout** | `agents/web_scout.py` | Recherche web réelle via Playwright + DuckDuckGo |
| **WorkflowAgent** | `agents/workflow_agent.py` | Création de workflows n8n via NL |
| **DevinAgent** | `agents/autonomous/devin_agent.py` | Agent autonome ReAct (actions Terminal/Editor/Browser) |
| **ScoutAgent** | `agents/autonomous/scout_agent.py` | Recherche autonome background |

---

### SelfCriticMixin (`agents/self_critic.py`)

Mixin injectable dans n'importe quel agent pour ajouter un round d'auto-critique.

```python
class ForgeBuilderWithCritic(SelfCriticMixin, ForgeBuilder):
    critic_max_rounds = 1    # 1 révision max
    critic_pass_score = 6.5  # seuil de passage

    async def run(self, session):
        return await self.run_with_self_critic(session)
```

**Fonctionnement :** après la sortie initiale, le LLM s'évalue lui-même. Si score < seuil → une révision avec la critique injectée dans le prompt.

---

## 8. MÉMOIRE

### Architecture 4 couches via MemoryBus

```python
from memory.memory_bus import MemoryBus
bus = MemoryBus(settings)

# Stocker
bus.remember("Le projet utilise FastAPI pour l'API REST", tags=["architecture"])
bus.remember_patch(patch_spec, success=True, model="deepseek-coder")

# Rechercher
results = await bus.search("architecture API", top_k=5)
ctx = bus.get_patch_context("core/orchestrator.py", "performance")
```

### Couche 1 — MemoryStore (`memory/store.py`)
- **Backends** : PostgreSQL (prod), Redis (cache), in-memory (fallback)
- **Opérations** : `store(key, text, tags)`, `search(query, k)`, `get(key)`, `delete(key)`
- **Usage** : mémoire générale clé-valeur, sessions passées, knowledge global

### Couche 2 — VectorMemory (`memory/vector_memory.py`)
- **Backends** : TF-IDF (défaut, 0 dépendance GPU), sentence-transformers (si disponible)
- **Opérations** : `add(text, metadata, tags)`, `search(query, top_k, min_score)`, `delete(id)`
- **Persistance** : `workspace/vector_store.json` (JSON) + Qdrant (si configuré)
- **Déduplication** : hash SHA256 du texte — évite les doublons

### Couche 3 — PatchMemory (`memory/patch_memory.py`)
- **Rôle** : patterns de patchs réussis — guide le PatchBuilder
- **Opérations** : `record(patch, success)`, `get_context(file, category)`
- **Persistance** : `workspace/patches/` (JSON par fichier)

### Couche 4 — FailureMemory (`memory/failure_memory.py`)
- **Rôle** : patchs rejetés — évite de répéter les mêmes erreurs
- **Opérations** : `record_failure(patch)`, `is_known_failure(patch)`
- **Persistance** : `workspace/failures.json`

### Mémoires spécialisées
| Module | Rôle |
|---|---|
| `AgentMemory` | Patterns réussis par agent — `get_context(agent_name)` |
| `KnowledgeMemory` | Connaissances validées par KnowledgeValidator — `get_context_for_prompt()` |
| `VaultMemory` (agent) | Interface Telegram/bot vers MemoryStore |

---

## 9. AUTO-AMÉLIORATION

### Pipeline 8 étapes (`self_improve/pipeline.py`)

```
Étape 1 — AUDIT      : Auditor scanne le code → AuditFinding[]
Étape 2 — PLAN       : sélection + priorisation des findings
Étape 3 — BUILD      : PatchBuilder génère PatchSpec (LLM deepseek-coder)
Étape 4 — REVIEW     : RegressionReviewer filtre les patchs risqués
Étape 5 — VALIDATION : Cards Telegram envoyées à l'utilisateur
    ↓ [PAUSE — attend l'approbation Telegram]
Étape 6 — APPLY      : application + backup obligatoire
Étape 7 — TEST       : python -m pytest (ou npm test)
Étape 8 — JOURNAL    : PatchJournal.record()
```

**Contraintes absolues :**
- Aucune écriture avant étape 6 (après validation humaine)
- Backup avant chaque application
- `DRY_RUN=true` → s'arrête avant étape 6
- Rollback disponible à tout moment

### Auditor (`self_improve/auditor.py`)
Analyse statique du code Python. Détecte :
- TODO/FIXME/HACK sans tracking
- Fonctions trop longues (> 50 lignes)
- Gestion d'erreurs `bare except`
- Magic numbers et strings hardcodées
- Imports circulaires potentiels

### PatchBuilder (`self_improve/patch_builder.py`)
Génère des `PatchSpec` via LLM (deepseek-coder). Un patch = diff textuel ciblé.

### EscalationRouter (`self_improve/escalation_router.py`)
Décide si un patch peut être appliqué localement ou doit être escaladé (openai/anthropic).

---

## 10. COUCHE D'EXÉCUTION

### ExecutionEngine v2 (`executor/execution_engine.py`)

Moteur de tâches avec queue prioritaire. **Thread-safe, singleton.**

```python
from executor.execution_engine import get_engine
engine = get_engine(settings)
task_id = engine.submit(task)
result  = engine.status(task_id)
```

**Architecture interne :**
- `heapq` (priority, timestamp, task) — tasks priorisées
- Thread daemon `_worker_loop()` — poll toutes les 2s
- Sémaphore `_MAX_CONCURRENT = 4` workers simultanés
- Retry avec backoff exponentiel (`RetryPolicy`)

**Cycle de vie des tâches :**
```
PENDING → RUNNING → SUCCEEDED
                 → FAILED      (retentable)
                 → TIMED_OUT   (retentable si < max_retries)
PENDING → CANCELLED (avant démarrage)
```

### RetryPolicy (`executor/retry_policy.py`)
```python
DEFAULT_POLICY = RetryPolicy(
    max_retries=3,
    base_delay_s=2.0,
    max_delay_s=60.0,
    jitter=True,    # évite les thundering herds
)
```

Erreurs retentables : `TimeoutError`, `ConnectionError`, `asyncio.TimeoutError`
Non retentables : `ValueError`, `TypeError`, `KeyError` (erreurs logiques)

### RiskEngine (`executor/risk_engine.py` + `risk/engine.py`)

Classifie les actions en `LOW` / `MEDIUM` / `HIGH` selon :
- Type d'action (read vs write vs run_command)
- Fichier cible (système vs workspace vs inconnu)
- Pattern de contenu (rm -rf, chmod 777, secrets...)

**Règles de validation selon le risque :**
| Risque | Comportement en AUTO | Comportement en MANUAL |
|---|---|---|
| LOW | Exécution automatique | Exécution automatique |
| MEDIUM | Auto si auto_count < MAX | Validation Telegram requise |
| HIGH | Validation Telegram requise | Validation Telegram requise |

### SupervisedExecutor (`executor/supervised_executor.py`)
Wrapper autour de l'ExecutionEngine qui ajoute :
- Validation des actions par RiskEngine avant exécution
- Notification Telegram pour les actions MEDIUM/HIGH
- Rollback automatique en cas d'échec

---

## 11. NIGHT WORKER

### NightWorkerEngine (`night_worker/worker.py`)

Travail autonome en **max 5 cycles** sur une mission longue.

**Cycle :** Analysis → Production → Review → Decision (continue ?)

**Prompt NightWorker JSON :**
```json
{
  "analysis": "Évaluation de la situation",
  "production": "Le livrable complet de ce cycle",
  "review": "Critique de ma propre production",
  "next_steps": "Ce qui reste à faire",
  "should_continue": true,
  "progress_percent": 40,
  "files_to_create": [{"path": "...", "content": "..."}]
}
```

**NightScheduler (`night_worker/scheduler.py`) :**
- Planification de missions récurrentes
- Déclenchement via cron ou API
- Nettoyage automatique des anciennes missions

---

## 12. BUSINESS LAYER

5 domaines métier, chacun avec son agent et son schéma.

| Domaine | Clé | Description |
|---|---|---|
| **Venture** | `venture` | Analyse d'opportunités business, étude de marché |
| **Offer** | `offer` | Design d'offres commerciales, pricing |
| **SaaS** | `saas` | Blueprint MVP SaaS, architecture produit |
| **Trade Ops** | `trade_ops` | Agents IA pour artisans/TPE (chauffagiste, plombier...) |
| **Workflow** | `workflow` | Automatisation de processus business |
| **Meta Builder** | `meta_builder` | Duplication/clone d'agents business |

**Routing :** `TaskRouter` détecte le mode `BUSINESS` → `BusinessLayer.run(intent, session)`

---

## 13. INTERFACES EXTERNES

### Bot Telegram (`jarvis_bot/bot.py`)

**Interface principale en production.**

| Commande | Description |
|---|---|
| `/auto <mission>` | Lance une mission en mode AUTO |
| `/night <mission>` | Lance une mission en mode NIGHT (multi-cycles) |
| `/improve` | Déclenche le pipeline d'auto-amélioration |
| `/status` | État du système (agents actifs, mémoire, LLM) |
| `/workspace` | Liste les fichiers du workspace |
| `/logs` | Derniers logs structurés |
| `/cancel` | Annule la tâche en cours |
| `/help` | Aide |
| Texte libre | Route via TaskRouter (auto-détection du mode) |

**Système de validation inline :**
- Actions MEDIUM/HIGH → bouton `[✅ Approuver] [❌ Rejeter]` dans Telegram
- TTL de 15 minutes — expiration automatique
- Patches d'amélioration persistés via `PendingPatchStore` (survit aux redémarrages)

### Control API HTTP (`api/control_api.py`)

**Port 7070** — stdlib pure, zéro dépendance externe.

| Endpoint | Méthode | Description |
|---|---|---|
| `/api/mission` | POST | Soumettre une mission |
| `/api/actions` | GET | Lister toutes les actions |
| `/api/action/{id}/approve` | POST | Approuver une action |
| `/api/action/{id}/reject` | POST | Rejeter une action |
| `/api/system/mode` | GET | Mode actuel |
| `/api/system/mode` | POST | Changer le mode |
| `/api/goals` | GET/POST | Objectifs en cours |
| `/api/night/schedule` | POST | Planifier une mission night |

### FastAPI (`api/main.py`) — EN DÉVELOPPEMENT

Port 8000. Routes plus riches avec authentication, WebSockets, versioning.
**Non utilisé en production** — `control_api.py` est le serveur actif.

### N8n Bridge (`tools/n8n/bridge.py`)

API REST complète vers n8n (auto-hébergé) :
- CRUD workflows (create, read, update, delete)
- Activation/désactivation
- Exécution via webhook
- Templates pré-construits (HTTP Request, Telegram Notification)

---

## 14. OBSERVABILITÉ & MONITORING

### MetricsCollector (`monitoring/metrics.py`)

Métriques légères persistées en JSON (`workspace/metrics.json`).

```python
m = MetricsCollector(settings)
m.inc("patch_approved")
m.record_latency("forge-builder", 1520)  # ms
m.record_llm_call("research", latency_s=2.1, error=False)
report = m.get_report()
```

**Métriques collectées :**
- `runs_per_day` — sessions par jour
- `patch_success_rate` — ratio patchs approuvés / générés
- `agent_latency_ms` — histogramme par agent
- `llm_call_count` — appels LLM par rôle
- `llm_error_count` — erreurs LLM par rôle
- `escalation_count` — escalades cloud

### LangfuseTracer (`observability/langfuse_tracer.py`) [NOUVEAU]

Traçage LLM optionnel vers Langfuse (self-hosted).

```bash
# Activer dans .env :
LANGFUSE_ENABLED=true
LANGFUSE_HOST=http://langfuse:3000
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...

# Démarrer avec :
docker compose --profile observability up
```

**Ce qui est tracé par appel LLM :**
- Prompt complet (messages)
- Completion (réponse)
- Modèle utilisé
- Tokens input/output
- Latence
- Session ID + agent name + rôle

**Garantie de non-blocage :** si Langfuse est down, `safe_invoke` continue normalement.

### Structlog

113 fichiers utilisent structlog. Chaque opération critique loguée avec contexte JSON :
```python
log.info("llm_call_ok", role=role, provider=provider, latency_ms=ms)
log.warning("agent_blocked_oom", agent=agent_name, ram_avail_mb=snap.ram_avail_mb)
log.error("shadow_advisor_structure_violations", count=len(violations))
```

### ResourceGuard Monitoring

Thread daemon qui monitore RAM + CPU toutes les 10s (LOCAL) / 15s (VPS).
Log automatique des transitions de statut NORMAL → SAFE → BLOCKED.

---

## 15. TESTS

**251 tests, 0 échec, 0 warning.**

| Fichier | Ce qu'il teste |
|---|---|
| `test_contracts.py` | Types partagés (AgentResult, HealthReport, contrats Pydantic) |
| `test_control_layer.py` | Control API HTTP, mission system, action queue |
| `test_execution_engine.py` | ExecutionEngine v2 — retry, timeout, priorités, cancellation |
| `test_executor.py` | SupervisedExecutor, risk classification, action types |
| `test_learning_engine.py` | LearningLoop, KnowledgeValidator, observation pipeline |
| `test_local_only.py` | LLMFactory en mode LOCAL_ONLY — pas de fallback cloud |
| `test_memory.py` | MemoryStore, VectorMemory, MemoryBus intégration |
| `test_orchestrator.py` | JarvisOrchestrator — routing, modes, session lifecycle |
| `test_parallel_agents.py` | ParallelExecutor — asyncio.gather, timeouts, échecs isolés |
| `test_resource_guard.py` | ResourceGuard — slots, SAFE mode, BLOCKED, profils LOCAL/VPS |
| `test_retry_engine.py` | RetryPolicy — backoff, jitter, erreurs retentables/non-retentables |
| `test_scheduler.py` | NightScheduler — planification, cycles, cleanup |
| `test_vault_finalization.py` | VaultMemory, CoherenceChecker, pipeline validation |
| `test_vector_memory.py` | VectorMemory — ajout, recherche, déduplication, TF-IDF fallback |
| `test_workflow.py` | WorkflowEngine, RiskEngine, WorkflowAgent, SupervisedExecutor |

**Lancer les tests :**
```bash
python -m pytest tests/ -q                 # rapide
python -m pytest tests/ -v --tb=short      # verbeux
python -m pytest tests/test_memory.py -v   # module spécifique
```

---

## 16. DOCKER & INFRASTRUCTURE

### Stack complète (`docker-compose.yml`)

| Service | Image | Port | Rôle |
|---|---|---|---|
| `postgres` | postgres:16-alpine | — | Base de données principale |
| `redis` | redis:7-alpine | — | Cache, sessions |
| `qdrant` | qdrant/qdrant | 6333 | Mémoire vectorielle |
| `ollama` | ollama/ollama | 11434 | LLMs locaux (limite 8GB RAM) |
| `n8n` | n8nio/n8n | 5678 | Automatisation workflows |
| `open_webui` | ghcr.io/open-webui | 3001 | Interface modèles locaux |
| `jarvis` | (build local) | 8000 | JarvisMax core (limite 4GB RAM) |
| `langfuse` | langfuse/langfuse | 3002 | Traçage LLM (profil optionnel) |

**Démarrage :**
```bash
# Stack principale
docker compose up -d

# Avec observabilité Langfuse
docker compose --profile observability up -d

# Logs Jarvis
docker logs jarvis_core -f
```

**Limites mémoire configurées :**
- Ollama : `OLLAMA_MEMORY_LIMIT=8g` (évite monopolisation RAM)
- Jarvis Core : `JARVIS_MEMORY_LIMIT=4g`

**Mode développement (sans Docker) :**
```bash
# Lancer directement (hors Docker)
python jarvis.py                 # CLI
python start_api.py              # API HTTP port 7070
python -m jarvis_bot.bot         # Bot Telegram
```

---

## 17. VARIABLES D'ENVIRONNEMENT

Fichier `.env` (copier depuis `.env.example`).

### Essentielles
```env
TELEGRAM_BOT_TOKEN=...          # Bot Telegram @BotFather
TELEGRAM_ALLOWED_USER_ID=...    # Votre ID Telegram numérique
POSTGRES_PASSWORD=...           # Mot de passe DB
REDIS_PASSWORD=...              # Mot de passe Redis
JARVIS_SECRET_KEY=...           # Secret JWT/session
```

### LLM
```env
OPENAI_API_KEY=sk-...           # Pour les rôles cloud
ANTHROPIC_API_KEY=sk-ant-...    # Optionnel
MODEL_STRATEGY=openai           # openai|anthropic|google|ollama
ESCALATION_ENABLED=false        # Activer le fallback cloud
OLLAMA_MODEL_MAIN=llama3.1:8b
OLLAMA_MODEL_CODE=deepseek-coder-v2:16b
```

### Mode d'exécution
```env
JARVIS_MODE=local               # local (2 agents max) | vps (5 agents max)
JARVIS_SAFE_MODE=false          # true = 1 agent, toujours
DRY_RUN=false                   # true = simule sans écrire
MAX_AUTO_ACTIONS=25             # Limite actions automatiques
OLLAMA_MEMORY_LIMIT=8g          # RAM max pour Ollama
```

### Observabilité (optionnel)
```env
LANGFUSE_ENABLED=false
LANGFUSE_HOST=http://langfuse:3000
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
```

---

## 18. FLUX D'EXÉCUTION COMPLET

Exemple : `/auto Analyse les performances de notre API et propose des optimisations`

```
1. Bot Telegram reçoit la commande
   └── authorized() → vérifie TELEGRAM_ALLOWED_USER_ID

2. TaskRouter.route("Analyse les performances...")
   └── Détecte RESEARCH (verbe "analyse" + pas de code attendu)
   └── Sélectionne agents: [vault-memory, scout-research, shadow-advisor, lens-reviewer]
   └── needs_actions = false

3. JarvisOrchestrator._run_auto(session)
   ├── ResourceGuard.check() → NORMAL (RAM OK)
   │
   ├── Agent 1: VaultMemory.run(session)
   │   └── MemoryStore.search("performances API") → souvenirs pertinents
   │   └── LLM → résumé contexte mémorisé
   │
   ├── ParallelExecutor.run([scout-research, shadow-advisor])
   │   ├── ResourceGuard.acquire_slot("scout-research")
   │   ├── ResourceGuard.acquire_slot("shadow-advisor")
   │   │
   │   ├── ScoutResearch.run(session)  ← asyncio.gather
   │   │   ├── user_message() = mission + vault-memory output + vec_ctx
   │   │   ├── LLMFactory.safe_invoke(messages, role="research")
   │   │   │   └── LangfuseTracer.generation() [si activé]
   │   │   └── Sortie: Synthèse, Faits clés, Tendances, Risques
   │   │
   │   └── ShadowAdvisor.run(session)  ← asyncio.gather
   │       ├── user_message() = sujet + contexte agents + knowledge
   │       ├── LLMFactory.safe_invoke(messages, role="advisor", timeout=30s)
   │       ├── parse_advisory(raw) → AdvisoryReport
   │       ├── AdvisoryScorer.score(report) → recalibre
   │       └── session.metadata["shadow_decision"] = "GO"
   │
   ├── ResourceGuard.release_slot("scout-research")
   ├── ResourceGuard.release_slot("shadow-advisor")
   │
   ├── Agent final: LensReviewer.run(session)
   │   └── _ctx(session) = outputs scout + shadow
   │   └── LLM → Score 8/10, APPROUVÉ
   │
   ├── ShadowGate.check(session) → allowed=True (score 7.2, decision=GO)
   │
   ├── needs_actions = false → PulseOps NON appelé
   │
   └── LearningLoop.observe(session) → extrait connaissances → KnowledgeValidator

4. Rapport final assemblé
   └── scout-research + shadow-advisor + lens-reviewer

5. Bot Telegram envoie le rapport (découpe si > 4096 chars)

6. Métriques enregistrées (MetricsCollector)
```

---

## 19. ÉTAT ACTUEL

### Ce qui est en production et fonctionnel ✅

| Composant | État |
|---|---|
| Bot Telegram | ✅ Fonctionnel — 8 commandes |
| Control API (port 7070) | ✅ Fonctionnel |
| 9 agents AgentCrew | ✅ Fonctionnels avec SelfCriticMixin |
| 3 agents v2 (Debug, Recovery, Monitoring) | ✅ Fonctionnels |
| ParallelExecutor | ✅ Fonctionnel + ResourceGuard |
| LLM Factory (circuit breaker, fallback) | ✅ Fonctionnel |
| ResourceGuard (anti-crash OOM) | ✅ Nouveau — testé |
| Mémoire 4 couches | ✅ Fonctionnelle |
| Self-Improve pipeline | ✅ Fonctionnel (DRY_RUN recommandé en dev) |
| NightWorker | ✅ Fonctionnel |
| Business Layer (5 domaines) | ✅ Fonctionnel |
| n8n Bridge | ✅ Fonctionnel |
| WebScout (Playwright) | ✅ Fonctionnel |
| Tests (251) | ✅ 100% passants |
| Langfuse Tracer | ✅ Nouveau — inactif par défaut |

### Ce qui est en développement / incomplet ⚠️

| Composant | État | Prochaine étape |
|---|---|---|
| FastAPI `api/main.py` | ⚠️ WIP — non utilisé en prod | Migrer de `control_api.py` |
| LangGraph | ⚠️ Installé, 0 usage | Intégrer pour human-in-loop (StateGraph) |
| DevinAgent (autonomous) | ⚠️ Partiel — sandbox limité | Sandbox Docker complet |
| Langfuse (observabilité) | ⚠️ Wiring OK, service Docker à configurer | `--profile observability` |
| OpenHands integration | ⚠️ Adapter présent, non testé en prod | Tester avec container OpenHands |

### Prochaines étapes recommandées

1. **LangGraph StateGraph** — human-in-loop formel dans l'orchestrateur
   - États : PLANNING → AWAITING_APPROVAL → EXECUTING → DONE
   - `interrupt()` avant exécution d'actions HIGH risk

2. **Migrer vers FastAPI** — remplacer `control_api.py` par `api/main.py`
   - Auth JWT, WebSockets, versioning, Swagger auto

3. **Langfuse** — activer en production
   - `docker compose --profile observability up -d`
   - Configurer les clés dans `.env`

4. **Structured Tools** (LangChain `@tool` / `BaseTool`)
   - Typer les interfaces inter-agents pour meilleure validation

---

*Documentation générée le 2026-03-19 par audit complet du codebase.*
*Commit : e4b01cf — 251 tests passants.*
