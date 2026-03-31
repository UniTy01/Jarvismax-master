# JARVIS MAX — Audit Frameworks & Plan d'Intégration
*Architecte : Claude Opus 4 — 2026-03-19*

---

## PHASE 1 — AUDIT COMPLET DU SYSTÈME

### 1.1 État des lieux

| Dimension | Valeur |
|---|---|
| Fichiers Python (hors .venv) | 187 |
| Tests | 237 (0 failures, 0 warnings) |
| Agents enregistrés | 17 |
| Fichiers core/ | 35 |
| Fichiers structlog | 113 (couverture dense) |
| Lignes LLMFactory | 586 |

### 1.2 Ce qui est BIEN fait — NE PAS TOUCHER

**a) LLM Factory** (`core/llm_factory.py`)
- Circuit breaker Ollama (CLOSED/OPEN/HALF) — fail-fast, évite les cascades timeout
- Routing par rôle : LOCAL_ONLY_ROLES jamais cloud, fallback cascade ollama→cloud
- `safe_invoke` unifié avec timeout, retry, MetricsCollector
- Validation clé API (None/vide/CHANGE_ME/< 20 chars)
- **VERDICT : Architecture exemplaire. Conserver tel quel.**

**b) Mémoire 4 couches** (`memory/`)
- MemoryStore (PostgreSQL/Redis/in-memory, clé-valeur + tags + recherche texte)
- VectorMemory (embeddings locaux TF-IDF + sentence_transformers)
- PatchMemory (patterns de patchs réussis)
- FailureMemory (patchs rejetés — évite répétition d'erreurs)
- MemoryBus : interface unifiée, lazy init, search parallèle, dedup
- **VERDICT : Architecture supérieure à la plupart des frameworks. Conserver.**

**c) Exécution parallèle** (`agents/parallel_executor.py`)
- asyncio.gather avec timeout individuel par agent (90s) et global (300s)
- Isolation des échecs (un agent fail n'arrête pas les autres)
- AgentResult typé avec success/error/duration_ms
- **VERDICT : Déjà implémenté et robuste. Conserver.**

**d) Résilience** (`agents/recovery_agent.py`, `agents/debug_agent.py`)
- 5 stratégies : ROLLBACK, SKIP, PARTIAL_RETRY, ESCALATE, ABORT
- Path traversal protection sur les rollbacks
- Circuit breaker Ollama
- **VERDICT : Production-ready. Conserver.**

**e) Logging structuré** (structlog, 113 fichiers)
- Couverture dense : chaque opération critique loguée avec contexte
- session_id systématique dans les logs agents
- **VERDICT : Exemplaire. Conserver.**

**f) Système d'apprentissage** (`learning/`)
- LearningLoop : observe → extrait → valide → stocke
- KnowledgeValidator : KEEP/DISCARD/NEEDS_TEST
- VaultMemory : persistance des connaissances avec feedback
- **VERDICT : Unique et précieux. Conserver.**

**g) Shadow Advisor** (`agents/shadow_advisor/`)
- AdvisoryReport + AdvisoryScorer + ShadowGate
- Bloque les actions à risque avant exécution
- **VERDICT : Conserver et renforcer.**

**h) n8n Bridge** (`tools/n8n/bridge.py`)
- API REST complète : CRUD workflows, activation, run
- 150+ intégrations SaaS via n8n (auto-hébergé)
- **VERDICT : Conserver — remplace Composio sans dépendance externe.**

### 1.3 Goulots d'étranglement identifiés

#### 🔴 GAP #1 — Observabilité LLM (CRITIQUE)
- **Problème** : MetricsCollector enregistre counts/latence mais ZERO traçage de prompts
- Impossible de déboguer un prompt qui produit de mauvaises sorties
- Impossible de comparer deux versions de prompt (A/B test au niveau prompt)
- Pas de visualisation des chaînes d'appels LLM
- **Impact** : Debug aveugle, optimisation des prompts impossible
- **Solution** : Langfuse (self-hosted)

#### 🟡 GAP #2 — Workflow avec état + Human-in-loop
- **Problème** : L'orchestrateur dispatch les agents séquentiellement sans graph d'état formel
- ShadowGate bloque statiquement selon des règles, mais pas de "pause et demande à l'utilisateur"
- Impossible d'interrompre un workflow en cours pour validation humaine
- **Impact** : Autonomie sans supervision possible → risque sur actions critiques
- **Solution** : LangGraph StateGraph (DÉJÀ INSTALLÉ, 0 usage)

#### 🟡 GAP #3 — Structured Tools
- **Problème** : Les agents utilisent des appels LLM directs plutôt que des schemas d'outils typés
- Pas de BaseTool/StructuredTool → validation d'input/output des outils non garantie
- **Impact** : Fragilité des interfaces inter-agents
- **Note** : Partiellement compensé par le typage Pydantic des contracts

#### 🟢 GAP #4 — LangGraph installé mais 0 usage
- LangGraph v1.1.3 est dans requirements et .venv mais **aucun fichier ne l'importe**
- Dépendance morte qui gonfle le container Docker (~80MB)
- **Solution** : Soit l'utiliser (GAP #2), soit le désinstaller

### 1.4 Ce qui ne doit PAS être ajouté

| Composant | Raison |
|---|---|
| FastAPI (main.py) | Déjà installé mais control_api.py (stdlib HTTP) utilisé en prod — cohabitation OK |
| LangGraph (si non utilisé) | Désinstaller OU utiliser pour GAP #2 |
| CrewAI | JarvisMax a AgentCrew + BaseAgent — régression assurée |
| AutoGen | Lourd (>1GB), redondant avec ParallelExecutor |

---

## PHASE 2 — ANALYSE OUTIL PAR OUTIL

### 🔴 REJETER — CrewAI
- **Ce qu'il apporte** : Agent roles, crew orchestration, task delegation
- **Ce que JarvisMax a déjà** : BaseAgent, AgentCrew, 17 agents avec rôles, ParallelExecutor
- **Verdict** : **REJETER** — JarvisMax est plus flexible et mieux intégré
- **Risque si intégré** : Régression, conflit d'architecture, overhead

### 🔴 REJETER — AutoGen (Microsoft)
- **Ce qu'il apporte** : Multi-agent conversation, code execution sandboxé
- **Ce que JarvisMax a déjà** : OrchestrateurAgent, ParallelExecutor, RecoveryAgent
- **Verdict** : **REJETER** — 1GB+, Microsoft-centric, totalement redondant
- **Risque** : Casse l'architecture locale-first

### 🔴 REJETER — OpenAI Agents SDK
- **Ce qu'il apporte** : Handoffs, guardrails, streaming tool calls
- **Problème** : OpenAI-specific — incompatible avec l'architecture local-first (Ollama/DeepSeek)
- **Verdict** : **REJETER** — Conflit fondamental avec la philosophie de JarvisMax
- **Risque** : Lock-in OpenAI, inutilisable avec Ollama

### 🔴 REJETER — MetaGPT
- **Ce qu'il apporte** : Software team simulation (PM, Dev, QA agents)
- **Ce que JarvisMax a déjà** : SelfImprove auditor + PatchBuilder + agents spécialisés
- **Verdict** : **REJETER** — 500MB+, très opinionated, redondant
- **Risque** : Surcharge architecturale

### 🔴 REJETER — Composio
- **Ce qu'il apporte** : 150+ intégrations SaaS (GitHub, Jira, Gmail...)
- **Ce que JarvisMax a déjà** : n8n Bridge (self-hosted, 400+ intégrations)
- **Verdict** : **REJETER** — n8n fait mieux, en self-hosted, sans dépendance cloud
- **Risque** : Dépendance cloud Composio, double emploi

### 🔴 REJETER — Helicone
- **Ce qu'il apporte** : Proxy LLM avec logging
- **Problème** : Proxy external, incompatible avec Ollama local
- **Verdict** : **REJETER** — Langfuse est supérieur et self-hostable
- **Risque** : Latence ajoutée, dépendance cloud

### 🔴 REJETER — Semantic Kernel (Microsoft)
- **Ce qu'il apporte** : Plugin system, memory connectors, planner
- **Ce que JarvisMax a déjà** : MemoryBus, AgentCrew, tout l'écosystème
- **Verdict** : **REJETER** — Microsoft ecosystem, redondant, architectural conflict

### 🟡 CONSERVER — LangChain (déjà installé)
- **Usage actuel** : LLM invocation backbone, MessageHistory, LangChain messages
- **Valeur** : Abstraction LLM-agnostic, support multi-providers
- **Verdict** : **CONSERVER** — Bien utilisé, ne pas remplacer
- **Action** : Aucune

### ✅ INTÉGRER — Langfuse (self-hosted)
- **Ce qu'il apporte** :
  - Traçage complet de chaque appel LLM (prompt, completion, tokens, latence)
  - Visualisation des chaînes (trace → spans → generations)
  - Comparaison A/B de prompts
  - Dashboard web auto-hébergeable (Docker)
  - SDK Python minimal : `langfuse.trace()`, `langfuse.generation()`
- **Intégration** : Wrapper dans `LLMFactory.safe_invoke` — 20 lignes
- **Infrastructure** : 1 container Docker (langfuse + postgres déjà présent)
- **Verdict** : **INTÉGRER** — Comble le GAP #1 critique, ROI maximal
- **Risque** : Quasi nul — instrumentation optionnelle, fallback si absent

### ✅ INTÉGRER — LangGraph (déjà installé, 0 usage)
- **Ce qu'il apporte** :
  - StateGraph : workflow multi-étapes avec transitions conditionnelles
  - Human-in-loop : `interrupt()` pour pause et validation humaine
  - State management : état persistant entre étapes
  - Streaming natif des étapes
- **Intégration** : Wrapper du dispatch principal dans l'orchestrateur
- **Infrastructure** : Déjà installé (v1.1.3)
- **Verdict** : **INTÉGRER** — Comble GAP #2, déjà présent, ROI immédiat
- **Risque** : Moyen — refactoring orchestrateur. Mitigation : wrapper progressif

---

## PHASE 3 — PLAN D'INTÉGRATION

### Ordre d'implémentation

```
BLOC 1 (SEMAINE 1) : Langfuse observabilité
├── Ajouter service langfuse dans docker-compose.yml
├── pip install langfuse
├── Créer observability/langfuse_tracer.py
├── Wrapper safe_invoke dans LLMFactory → inject trace context
└── Tests : vérifier que les traces arrivent dans Langfuse UI

BLOC 2 (SEMAINE 2) : LangGraph human-in-loop
├── Créer core/workflow_graph.py — StateGraph de l'orchestrateur
├── États : PLANNING → AWAITING_APPROVAL ⟶ EXECUTING → DONE/FAILED
├── interrupt() avant EXECUTING si risque détecté par ShadowGate
├── API endpoint : POST /api/v2/missions/{id}/approve
└── Tests : vérifier que les missions se mettent en pause correctement
```

### Règles d'intégration

1. **Zero breaking change** — les agents existants fonctionnent sans modification
2. **Fallback silencieux** — si Langfuse down, `safe_invoke` continue sans traçage
3. **Feature flags** — `settings.langfuse_enabled = True/False`
4. **Tests avant/après** — 237 tests doivent passer avant ET après chaque bloc

---

## DÉCISION FINALE

| Outil | Décision | Raison |
|---|---|---|
| LangChain | ✅ CONSERVER | Backbone bien intégré |
| LangGraph | ✅ INTÉGRER | Déjà installé, human-in-loop |
| Langfuse | ✅ INTÉGRER | Observabilité LLM critique |
| CrewAI | ❌ REJETER | Redondant avec AgentCrew |
| AutoGen | ❌ REJETER | Lourd, redondant, Microsoft |
| OpenAI SDK | ❌ REJETER | Lock-in OpenAI, incompatible local |
| MetaGPT | ❌ REJETER | Lourd, opinionated, redondant |
| Composio | ❌ REJETER | n8n fait mieux en self-hosted |
| Helicone | ❌ REJETER | Proxy cloud, Langfuse est meilleur |
| Semantic Kernel | ❌ REJETER | Microsoft ecosystem, redondant |

**RÉSULTAT : 2 intégrations ciblées sur 10 outils analysés = ROI maximal, risque minimal.**
